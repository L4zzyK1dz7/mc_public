"""Streamlit page: browse a run folder and view its animation and output tables."""

from __future__ import annotations

import streamlit as st

from src.ui.plotting.platform_animation import build_animation
from src.ui.services.animation_data import build_platforms, load_animation_inputs
from src.ui.services.results_data import (
    list_run_folders,
    load_raw_positions,
    load_summary_stats_tables,
)


def main() -> None:
    st.title("Results")

    run_folders = list_run_folders()
    if not run_folders:
        st.info("No runs found under 'outcomes/'. Run a simulation first.")
        return

    selected_folder = st.selectbox(
        "Run folder", run_folders, format_func=lambda folder: folder.name
    )

    animation_tab, positions_tab, summary_tab = st.tabs(
        ["Animation", "Raw Positions", "Summary Stats"]
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
