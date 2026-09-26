import pandas as pd
import streamlit as st

from src.ui.plotting.detection_analytics import (
    build_detection_histogram,
    build_fleet_convergence_chart,
    build_interaction_heatmap,
    build_pairwise_convergence_chart,
)
from src.ui.plotting.platform_animation import build_animation
from src.ui.services.animation_data import build_platforms, load_animation_inputs
from src.ui.services.results_data import (
    list_run_folders,
    load_raw_positions,
    load_summary_stats_tables,
)


def render_analytics_tab(tables: dict[str, pd.DataFrame]) -> None:
    """Render Tier 1, 2, and 3 Monte Carlo detection analytics."""
    raw_outcomes = next(
        (df for title, df in tables.items() if "Replication-Level" in title), None
    )
    table_1 = next(
        (df for title, df in tables.items() if "Average Detections Across All Agents" in title),
        None,
    )

    if raw_outcomes is None or raw_outcomes.empty:
        st.info("No replication-level detection outcomes found in summary_stats.csv.")
        return

    total_reps = int(raw_outcomes["replication_id"].nunique())
    confirmed_detections = int(
        raw_outcomes.groupby("replication_id")["detection_outcome"].any().sum()
    )
    fleet_p_det = (
        confirmed_detections / total_reps if total_reps > 0 else 0.0
    )

    # Top KPI Metrics Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Replications", f"{total_reps:,}")
    kpi2.metric("Fleet Detection Prob (P_det)", f"{fleet_p_det:.1%}")
    kpi3.metric("Successful Detections", f"{confirmed_detections:,}")
    detected_times = pd.to_numeric(
        raw_outcomes[raw_outcomes["detection_outcome"] == True][
            "detection_timestamp_minutes"
        ],
        errors="coerce",
    ).dropna()
    mean_time = f"{detected_times.mean():.1f} min" if not detected_times.empty else "N/A"
    kpi4.metric("Mean Time to Detect", mean_time)

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
    st.title("Results")

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
            positions, sensors, timing = load_animation_inputs(selected_folder)
        except (OSError, ValueError) as error:
            st.error(f"Could not load animation inputs: {error}")
        else:
            replications = sorted(positions["replication_id"].unique())
            selected_replication = st.selectbox(
                "Replication",
                replications,
                format_func=lambda value: f"Replication {value}",
            )
            platforms = build_platforms(positions, sensors, int(selected_replication))
            st.plotly_chart(build_animation(platforms, timing))

    with analytics_tab:
        try:
            tables = load_summary_stats_tables(selected_folder)
        except OSError as error:
            st.error(f"Could not load summary_stats.csv: {error}")
        else:
            render_analytics_tab(tables)

    with positions_tab:
        try:
            raw_positions = load_raw_positions(selected_folder)
        except OSError as error:
            st.error(f"Could not load raw_positions.csv: {error}")
        else:
            st.dataframe(raw_positions, width="stretch")

    with summary_tab:
        try:
            tables = load_summary_stats_tables(selected_folder)
        except OSError as error:
            st.error(f"Could not load summary_stats.csv: {error}")
        else:
            for title, table in tables.items():
                st.subheader(title)
                st.dataframe(table, width="stretch")


main()
