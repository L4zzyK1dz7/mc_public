from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from src.monte_carlo.configuration.load_configuration import load_config_from_yaml
from src.ui.plotting.detection_analytics import (
    build_detection_histogram,
    build_fleet_convergence_chart,
    build_interaction_heatmap,
    build_pairwise_convergence_chart,
)
from src.ui.plotting.platform_animation import build_animation
from src.ui.services.animation_data import (
    build_display_name_map,
    build_platforms,
    compute_replication_end_sec,
    load_animation_inputs,
    load_barriers,
    load_operating_area,
    load_sonobuoys,
    load_sonobuoy_detections,
)
from src.ui.services.results_data import (
    apply_display_names,
    list_run_folders,
    load_raw_positions,
    load_summary_stats_tables,
)


def render_analytics_tab(
    tables: dict[str, pd.DataFrame],
    name_map: Optional[dict[str, str]] = None,
) -> None:
    """Render Tier 1, 2, and 3 Monte Carlo detection analytics."""
    raw_outcomes = next(
        (df for title, df in tables.items() if "Replication-Level" in title), None
    )
    table_1 = next(
        (df for title, df in tables.items() if "Average Detections Across All Agents" in title),
        None,
    )
    end_conditions_table = next(
        (df for title, df in tables.items() if "End Condition Rates" in title), None
    )

    if raw_outcomes is None or raw_outcomes.empty:
        st.info("No replication-level detection outcomes found in summary_stats.csv.")
        return

    if name_map:
        raw_outcomes = apply_display_names(raw_outcomes, name_map)
        if table_1 is not None and not table_1.empty:
            table_1 = apply_display_names(table_1, name_map)

    total_reps = int(raw_outcomes["replication_id"].nunique())
    confirmed_detections = int(
        raw_outcomes.groupby("replication_id")["detection_outcome"].any().sum()
    )
    fleet_p_det = (
        confirmed_detections / total_reps if total_reps > 0 else 0.0
    )

    def _rate_for(cond: str) -> tuple[int, float]:
        if (
            end_conditions_table is not None
            and not end_conditions_table.empty
            and "end_condition" in end_conditions_table.columns
        ):
            matching = end_conditions_table[end_conditions_table["end_condition"] == cond]
            if not matching.empty:
                return int(matching["count"].iloc[0]), float(matching["rate"].iloc[0])
        # Fallback to computing from raw_outcomes if end_conditions_table is not present
        if "end_condition" in raw_outcomes.columns:
            rep_end = raw_outcomes[["replication_id", "end_condition"]].dropna().drop_duplicates(subset=["replication_id"])
            matching = rep_end[rep_end["end_condition"] == cond]
            count = len(matching)
            rate = count / total_reps if total_reps > 0 else 0.0
            return count, rate
        return 0, 0.0

    time_count, time_rate = _rate_for("time_limit")
    escape_count, escape_rate = _rate_for("target_escaped")
    det_count, det_rate = _rate_for("detection")
    blue_det_count, blue_det_rate = _rate_for("blue_team_detection")
    red_det_count, red_det_rate = _rate_for("red_team_detection")
    sb_single_cycle_count, sb_single_cycle_rate = _rate_for("sonobuoy_single_cycle_detection")
    sb_multi_count, sb_multi_rate = _rate_for("sonobuoy_multi_detection")
    sb_single_count, sb_single_rate = _rate_for("sonobuoy_single_detection")

    # Top KPI Metrics Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Replications", f"{total_reps:,}")
    kpi2.metric("Fleet Detection Prob (P_det)", f"{fleet_p_det:.1%}")
    kpi3.metric("Time Limit Reached", f"{time_rate:.1%}", help=f"{time_count} replications")
    kpi4.metric("Target Escaped", f"{escape_rate:.1%}", help=f"{escape_count} replications")

    st.caption("Detection Outcomes Breakdown:")
    det_col1, det_col2, det_col3, det_col4 = st.columns(4)
    det_col1.metric("Initial Detection", f"{det_rate:.1%}", help=f"{det_count} replications")
    det_col2.metric("Blue Team Detection", f"{blue_det_rate:.1%}", help=f"{blue_det_count} replications")
    det_col3.metric("Red Team Detection", f"{red_det_rate:.1%}", help=f"{red_det_count} replications")

    detected_times = pd.to_numeric(
        raw_outcomes[raw_outcomes["detection_outcome"]][
            "detection_timestamp_minutes"
        ],
        errors="coerce",
    ).dropna()
    mean_time = f"{detected_times.mean():.1f} min" if not detected_times.empty else "N/A"
    det_col4.metric("Mean Time to Detect", mean_time)

    total_sb = sb_single_cycle_count + sb_multi_count + sb_single_count
    if total_sb > 0:
        st.caption("Sonobuoy Multistatic Outcomes Breakdown:")
        sb_col1, sb_col2, sb_col3 = st.columns(3)
        sb_col1.metric(
            "Single Cycle Detection",
            f"{sb_single_cycle_rate:.1%}",
            help=f"{sb_single_cycle_count} replications",
        )
        sb_col2.metric(
            "Multi-Buoy Detection",
            f"{sb_multi_rate:.1%}",
            help=f"{sb_multi_count} replications",
        )
        sb_col3.metric(
            "Single Buoy Detection",
            f"{sb_single_rate:.1%}",
            help=f"{sb_single_count} replications",
        )

    st.markdown("---")


    # =========================================================================
    # Tier 1: Fleet Overview & Monte Carlo Convergence
    # =========================================================================
    st.subheader("Tier 1: Fleet-Level Monte Carlo Convergence")
    st.caption(
        "Demonstrates statistical stability and convergence across sample size N. "
        "Curves represent cumulative empirical detection probability as replications accumulate."
    )
    fleet_fig = build_fleet_convergence_chart(raw_outcomes)
    st.plotly_chart(fleet_fig, use_container_width=True)

    # =========================================================================
    # Tier 2: Interaction Matrix (Many-to-Many Heatmap)
    # =========================================================================
    if table_1 is not None and not table_1.empty:
        st.markdown("---")
        st.subheader("Tier 2: Interaction Matrix (Observer vs Target)")
        st.caption(
            "Maps collective detection coverage across all agent pairs to identify "
            "tactical blind spots and overlapping sensor coverage."
        )
        heatmap_fig = build_interaction_heatmap(table_1)
        if heatmap_fig is not None:
            st.plotly_chart(heatmap_fig, use_container_width=True)

    # =========================================================================
    # Tier 3: Pairwise Drill-Down & Histograms
    # =========================================================================
    st.markdown("---")
    st.subheader("Tier 3: Pairwise Engagement Drill-Down")
    st.caption(
        "Select specific observer and target platforms to inspect pair-specific "
        "convergence bounds and engagement physics (time and distance distributions)."
    )

    observers = ["All Observers (Fleet)"] + sorted(
        str(val) for val in raw_outcomes["detecting_platform_id"].dropna().unique()
    )
    targets = ["All Targets (Combined)"] + sorted(
        str(val) for val in raw_outcomes["target_platform_id"].dropna().unique()
    )

    col1, col2 = st.columns(2)
    selected_obs = col1.selectbox("Observer Platform (Blue)", observers)
    selected_target = col2.selectbox("Target Platform (Red)", targets)

    # Filter data for selected pair
    filtered_df = raw_outcomes.copy()
    if selected_obs != "All Observers (Fleet)":
        filtered_df = filtered_df[filtered_df["detecting_platform_id"] == selected_obs]
    if selected_target != "All Targets (Combined)":
        filtered_df = filtered_df[filtered_df["target_platform_id"] == selected_target]

    # Pairwise convergence chart with 95% CI ribbon
    pair_fig = build_pairwise_convergence_chart(
        filtered_df, selected_obs, selected_target, total_replications=total_reps
    )
    st.plotly_chart(pair_fig, use_container_width=True)

    # Histograms for engagement metrics
    hist_col1, hist_col2 = st.columns(2)
    with hist_col1:
        time_hist = build_detection_histogram(
            filtered_df,
            metric_col="detection_timestamp_minutes",
            title=f"Time-to-Detection ({selected_obs} vs {selected_target})",
            xlabel="Detection Time (minutes)",
            color="#2ca02c",
        )
        if time_hist is not None:
            st.plotly_chart(time_hist, use_container_width=True)
        else:
            st.info("No confirmed detections to display time histogram.")

    with hist_col2:
        dist_hist = build_detection_histogram(
            filtered_df,
            metric_col="detection_distance_km",
            title=f"Distance-at-Detection ({selected_obs} vs {selected_target})",
            xlabel="Detection Distance (km)",
            color="#17becf",
        )
        if dist_hist is not None:
            st.plotly_chart(dist_hist, use_container_width=True)
        else:
            st.info("No confirmed detections to display distance histogram.")


def main() -> None:
    st.title("📊 Results 📊")

    run_folders = list_run_folders()
    if not run_folders:
        st.info("No runs found under 'outcomes/'. Run a simulation first.")
        return

    selected_folder = st.selectbox(
        "Run folder", run_folders, format_func=lambda folder: folder.name
    )

    animation_tab, analytics_tab, positions_tab, summary_tab = st.tabs(
        ["Animation", "Analytics & Convergence", "Raw Positions", "Summary Stats"]
    )

    with animation_tab:
        try:
            positions, sensors, timing, name_map = load_animation_inputs(selected_folder)
        except (OSError, ValueError) as error:
            st.error(f"Could not load animation inputs: {error}")
        else:
            replications = sorted(positions["replication_id"].unique())
            selected_replication = st.selectbox(
                "Replication",
                replications,
                format_func=lambda value: f"Replication {value}",
            )
            platforms = build_platforms(
                positions, sensors, int(selected_replication), name_map=name_map
            )
            timing["end_time_sec"] = compute_replication_end_sec(platforms)

            col1, col2 = st.columns(2)
            col1.text_input(
                "Simulation Time Limit (User Input)",
                value=f"{timing['time_limit_sec'] / 60.0:.2f} min ({timing['time_limit_sec']:.1f} s)",
                disabled=True,
            )
            col2.text_input(
                "Replication Duration",
                value=f"{timing['end_time_sec'] / 60.0:.2f} min ({timing['end_time_sec']:.1f} s)",
                disabled=True,
            )

            config_path = selected_folder / "input_data" / "config.yaml"
            sonobuoys = []
            operating_area = None
            barriers = None
            if config_path.exists():
                try:
                    cfg = load_config_from_yaml(config_path)
                    sonobuoys = load_sonobuoys(cfg)
                    operating_area = load_operating_area(cfg)
                    barriers = load_barriers(cfg)
                except Exception:
                    sonobuoys = []
                    operating_area = None
                    barriers = None
            sb_detections = load_sonobuoy_detections(
                selected_folder, int(selected_replication)
            )

            st.plotly_chart(
                build_animation(
                    platforms,
                    timing,
                    sonobuoys=sonobuoys,
                    sonobuoy_detections=sb_detections,
                    operating_area=operating_area,
                    barriers=barriers,
                ),
                use_container_width=True,
            )

    with analytics_tab:
        try:
            tables = load_summary_stats_tables(selected_folder)
        except OSError as error:
            st.error(f"Could not load summary_stats.csv: {error}")
        else:
            name_map: dict[str, str] = {}
            config_path = selected_folder / "input_data" / "config.yaml"
            if config_path.exists():
                try:
                    config_data = load_config_from_yaml(config_path)
                    name_map = build_display_name_map(config_data)
                except Exception:
                    name_map = {}
            render_analytics_tab(tables, name_map=name_map)

    with positions_tab:
        try:
            raw_positions = load_raw_positions(selected_folder)
        except OSError as error:
            st.error(f"Could not load raw_positions.csv: {error}")
        else:
            mapped_positions = (
                apply_display_names(
                    raw_positions,
                    name_map,
                    columns=("platform_id", "detecting_platform_id", "target_platform_id"),
                )
                if name_map
                else raw_positions
            )
            st.dataframe(mapped_positions, width="stretch")

    with summary_tab:
        try:
            tables = load_summary_stats_tables(selected_folder)
        except OSError as error:
            st.error(f"Could not load summary_stats.csv: {error}")
        else:
            for title, table in tables.items():
                st.subheader(title)
                mapped_table = (
                    apply_display_names(
                        table,
                        name_map,
                        columns=("detecting_platform_id", "target_platform_id", "platform_id"),
                    )
                    if name_map
                    else table
                )
                st.dataframe(mapped_table, width="stretch")


main()
