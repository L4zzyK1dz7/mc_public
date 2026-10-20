"""
Streamlit view for configuring multistatic sonobuoys and field-level fusion parameters.
"""

from __future__ import annotations

import logging
from typing import cast

import pandas as pd
import streamlit as st

from src.schemas.sonobuoy import SonobuoyConfig, SonobuoyEvaluationMode
from src.ui.services.performance_table import (
    extract_valid_sensor_points,
    parse_sensor_csv,
)
from src.ui.user_notifier import success

logger = logging.getLogger(__name__)


def _has_active_blue_source() -> bool:
    """Check if any saved Blue platform possesses an active acoustic source sensor."""
    platforms = st.session_state.get("platform_draft_list", [])
    for platform in platforms:
        team_str = getattr(platform, "team", "")
        team_val = team_str.value if hasattr(team_str, "value") else str(team_str)
        if team_val.lower() == "blue":
            for sensor in getattr(platform, "sensors", []):
                if getattr(sensor, "active_source", False):
                    return True
    return False


def _build_sonobuoy_summary(buoys: list[SonobuoyConfig]) -> pd.DataFrame:
    """Build summary dataframe of configured sonobuoys."""
    if not buoys:
        return pd.DataFrame()

    rows = []
    for idx, buoy in enumerate(buoys):
        rows.append(
            {
                "Index": idx + 1,
                "Name": buoy.display_name,
                "X (km)": buoy.x_m,
                "Y (km)": buoy.y_m,
                "K": buoy.k,
                "N": buoy.n,
                "Modes": ", ".join(buoy.evaluation_modes),
                "PoD Points": len(buoy.distance_m),
            }
        )
    return pd.DataFrame(rows)


def _is_duplicate_buoy_name(name: str) -> bool:
    """Check whether a sonobuoy with the given display name already exists."""
    existing_names = {
        b.display_name.strip().lower()
        for b in st.session_state.get("sonobuoy_draft_list", [])
    }
    return name.strip().lower() in existing_names


def render_sonobuoy_overview() -> None:
    """Render the overview table and deletion controls for sonobuoys."""
    st.markdown("### Configured Sonobuoys")
    buoys: list[SonobuoyConfig] = st.session_state.get("sonobuoy_draft_list", [])

    if not buoys:
        st.info("No sonobuoys configured yet.")
        return

    summary_df = _build_sonobuoy_summary(buoys)
    st.dataframe(summary_df, width="stretch", hide_index=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        buoy_to_delete = st.selectbox(
            "Select sonobuoy to remove",
            options=[b.display_name for b in buoys],
            key="delete_sonobuoy_select",
        )
    with col2:
        if st.button("Delete Sonobuoy", type="secondary"):
            st.session_state.sonobuoy_draft_list = [
                b for b in buoys if b.display_name != buoy_to_delete
            ]
            st.rerun()


def render_sonobuoy_creation() -> None:
    """Render the form and editors to configure field fusion and individual sonobuoys."""
    st.markdown("## Multistatic Sonobuoy Configuration")

    # Banner notifying if no active Blue source is present
    if not _has_active_blue_source():
        st.info(
            "Note: No Blue platform currently has an active acoustic source sensor. "
            "Sonobuoys require active acoustic pings to detect targets and will not evaluate without one."
        )

    # Field-level configuration
    st.markdown("### Field Settings")
    st.session_state.data_fusion_requirement = st.number_input(
        "Data Fusion Requirement (M)",
        min_value=1,
        value=int(st.session_state.get("data_fusion_requirement", 1)),
        step=1,
        help="Minimum number of positive detection events required across buoys in multi-buoy and single-cycle fusion.",
    )

    render_sonobuoy_overview()

    st.markdown("### Add Sonobuoy")
    index = len(st.session_state.get("sonobuoy_draft_list", []))

    # Boundary limits from World parameters
    origin_x = float(st.session_state.get("origin_x", 0.0))
    origin_y = float(st.session_state.get("origin_y", 0.0))
    length = float(st.session_state.get("length", 100.0))
    height = float(st.session_state.get("height", 100.0))

    display_name = st.text_input(
        "Sonobuoy Name",
        value=f"Buoy {index + 1}",
        key=f"buoy_name_{index}",
    )
    if display_name and _is_duplicate_buoy_name(display_name):
        st.error(f"A sonobuoy named '{display_name}' already exists.")

    col_x, col_y = st.columns(2)
    with col_x:
        x_km = st.number_input(
            "X Position (km)",
            min_value=origin_x,
            max_value=origin_x + length,
            value=min(max(origin_x + length / 2.0, origin_x), origin_x + length),
            step=0.1,
            key=f"buoy_x_{index}",
        )
    with col_y:
        y_km = st.number_input(
            "Y Position (km)",
            min_value=origin_y,
            max_value=origin_y + height,
            value=min(max(origin_y + height / 2.0, origin_y), origin_y + height),
            step=0.1,
            key=f"buoy_y_{index}",
        )

    col_k, col_n = st.columns(2)
    with col_k:
        k = st.number_input(
            "K (detections)",
            min_value=1,
            value=1,
            step=1,
            key=f"buoy_k_{index}",
            help="Number of positive detections required within sliding window.",
        )
    with col_n:
        n = st.number_input(
            "N (window size)",
            min_value=1,
            value=1,
            step=1,
            key=f"buoy_n_{index}",
            help="Sliding window capacity of past ping evaluations.",
        )

    if k > n:
        st.error("K cannot be greater than N.")

    evaluation_modes = st.multiselect(
        "Evaluation Modes",
        options=["single", "multi", "single_cycle"],
        default=["single", "multi", "single_cycle"],
        key=f"buoy_modes_{index}",
        help="Select fusion evaluation modes in which this buoy participates.",
    )
    if not evaluation_modes:
        st.error("At least one evaluation mode must be selected.")

    mode = st.radio(
        "Performance Curve Input Mode",
        options=["manual", "import"],
        key=f"buoy_input_mode_{index}",
        horizontal=True,
    )

    x_values: list[float] = []
    pod_values: list[float] = []

    if mode == "manual":
        st.caption("Provide distance_m and pod rows. PoD must be between 0 and 1.")
        default_data = {
            "distance_m": [0.0, 1000.0, 2000.0, 5000.0, 10000.0],
            "pod": [1.0, 0.9, 0.7, 0.4, 0.0],
        }
        edited_table = st.data_editor(
            pd.DataFrame(default_data),
            num_rows="dynamic",
            width="stretch",
            key=f"buoy_table_{index}",
            column_config={
                "distance_m": st.column_config.NumberColumn(
                    "distance_m",
                    help="Equivalent bistatic distance in metres.",
                    required=True,
                ),
                "pod": st.column_config.NumberColumn(
                    "pod",
                    help="Probability of detection [0.0, 1.0].",
                    min_value=0.0,
                    max_value=1.0,
                    required=True,
                ),
            },
        )
        norm_table = edited_table.copy()
        if "distance_m" in norm_table.columns and "x_values" not in norm_table.columns:
            norm_table = norm_table.rename(columns={"distance_m": "x_values"})
        x_values, pod_values, val_err = extract_valid_sensor_points(norm_table)
    else:
        uploaded_file = st.file_uploader(
            "Choose a sonobuoy PoD CSV file",
            type="csv",
            key=f"buoy_upload_{index}",
        )
        val_err = None
        if uploaded_file is not None:
            raw_table = pd.read_csv(uploaded_file)
            parsed_table, msg = parse_sensor_csv(raw_table, sensor_type="generic")
            if msg:
                st.info(msg)
            if not parsed_table.empty:
                st.dataframe(parsed_table.rename(columns={"x_values": "distance_m"}), width="stretch")
                x_values, pod_values, val_err = extract_valid_sensor_points(parsed_table)

    save_buoy = st.button("Save Sonobuoy", type="primary")
    if save_buoy:
        if not display_name.strip():
            st.error("Display name cannot be empty.")
            return
        if _is_duplicate_buoy_name(display_name):
            st.error(f"A sonobuoy named '{display_name}' already exists.")
            return
        if k > n:
            st.error("K cannot be greater than N.")
            return
        if not evaluation_modes:
            st.error("At least one evaluation mode must be selected.")
            return
        if val_err:
            st.error(val_err)
            return
        if not x_values or not pod_values:
            st.error("Please supply valid distance_m and pod points.")
            return

        try:
            buoy_cfg = SonobuoyConfig(
                display_name=display_name.strip(),
                x_m=x_km,
                y_m=y_km,
                k=k,
                n=n,
                evaluation_modes=cast(list[SonobuoyEvaluationMode], evaluation_modes),
                distance_m=x_values,
                pod=pod_values,
            )
            st.session_state.setdefault("sonobuoy_draft_list", []).append(buoy_cfg)
            success(f"buoy_{index}_saved", f"Sonobuoy '{buoy_cfg.display_name}' saved.")
            st.rerun()
        except Exception as exc:
            st.error(f"Failed to create sonobuoy: {exc}")


def main() -> None:
    """Main route for Create Sonobuoys view."""
    render_sonobuoy_creation()


if __name__ == "__main__":
    main()
