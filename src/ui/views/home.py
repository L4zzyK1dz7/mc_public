"""
Home for streamlit application
"""

import logging

import pandas as pd
import streamlit as st

from src.monte_carlo.monte_carlo import run_simulation
from src.schemas.platform import Team
from src.schemas.simulation import ConfigData, SimulationConfig, WorldConfig
from src.ui.services.create_yaml import create_config_yaml
from src.ui.user_notifier import success

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def render_platform_table_with_delete() -> None:
    """
    Render current platforms as a table and provide per-platform delete actions.
    """
    platforms = st.session_state.get("platform_draft_list", [])

    if not platforms:
        st.info("No platforms to display yet.")
        return

    table_rows = [
        {
            "Name": platform.display_name,
            "Speed (m/s)": platform.speed_mps,
            "Team": platform.team.value
            if isinstance(platform.team, Team)
            else str(platform.team),
        }
        for platform in platforms
    ]
    st.subheader("Current Platforms")
    st.table(pd.DataFrame(table_rows))

    st.markdown("### Delete a platform:")
    for idx, platform in enumerate(platforms):
        team_label = (
            platform.team.value
            if isinstance(platform.team, Team)
            else str(platform.team)
        )
        label_col, action_col = st.columns([5, 1])
        label_col.write(f"{platform.display_name} ({team_label})")
        # Include both name and index to keep Streamlit widget keys stable across reruns.
        delete_key = f"delete_platform_{platform.display_name}_{idx}"
        if action_col.button("Delete", key=delete_key):
            deleted_name = platform.display_name
            # Remove by display_name so the update is deterministic even if indices shift.
            st.session_state.platform_draft_list = [
                p
                for p in st.session_state.platform_draft_list
                if p.display_name != deleted_name
            ]
            logger.info("Deleted platform: %s", deleted_name)
            st.success(f"Deleted platform '{deleted_name}'.")
            # Force immediate rerun so the table and status card reflect the new list.
            st.rerun()


def render_platform_status_card() -> bool:
    """
    Render a status card for the currently created platforms.
    return True if the simulation is ready to run (at least one Red and one Blue platform), else False.
    """

    # These are the current platforms in session state .
    platforms = st.session_state.get("platform_draft_list", [])
    # Get unique team values from the current platforms to determine readiness.
    team_colours = set(
        platform.team.value if isinstance(platform.team, Team) else str(platform.team)
        for platform in platforms
    )
    is_ready: bool = False
    if "Red" and "Blue" in team_colours:
        is_ready = True

    platform_count = len(platforms)

    # These are derived UI flags; compute from current state instead of persisting them.
    has_red_platform = Team.RED.value in team_colours
    has_blue_platform = Team.BLUE.value in team_colours
    is_ready = has_red_platform and has_blue_platform

    logger.debug(
        "Platform count: %s, teams: %s, has_red: %s, has_blue: %s, is_ready: %s",
        platform_count,
        sorted(team_colours),
        has_red_platform,
        has_blue_platform,
        is_ready,
    )

    if platform_count == 0:
        title = "No Current Platforms"
        message = "Create one Red and one Blue platform to make the simulation ready."
        background = "#fdecea"
        border = "#dc3545"
    elif is_ready:
        title = "Simulation Ready"
        message = "At least one Red and one Blue platform have been created."
        background = "#e8f5e9"
        border = "#2e7d32"
    else:
        title = "Partially Ready"
        message = "You have at least one platform, but you still need one Red and one Blue platform."
        background = "#fff8e1"
        border = "#f9a825"

    platform_rows = "".join(
        f"<li><strong>{platform.display_name}</strong> ({platform.team.value if isinstance(platform.team, Team) else platform.team})</li>"
        for platform in platforms
    )
    platform_list = (
        f"<ul>{platform_rows}</ul>"
        if platform_rows
        else "<p>No platforms created yet.</p>"
    )

    st.markdown(
        f"""
        <div style="
            background-color: {background};
            border-left: 8px solid {border};
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin: 1rem 0;
        ">
            <h3 style="margin-top: 0; margin-bottom: 0.5rem;">{title}</h3>
            <p style="margin-bottom: 0.75rem;">{message}</p>
            <p style="margin-bottom: 0.5rem;"><strong>Platforms created:</strong> {platform_count}</p>
            {platform_list}
        </div>
        """,
        unsafe_allow_html=True,
    )

    return is_ready


def create_cfg_data() -> None:
    """
    Create a ConfigData object from the current session state and store it in session state.
    """
    try:
        # Create the ConfigData object from the current session state.
        cfg_data = ConfigData(
            simulation=SimulationConfig(
                replications=st.session_state.number_of_replications,
                time_limit_sec=st.session_state.time_limit_sec,
                world_timestep_sec=st.session_state.world_timestep_sec,
                detection_end_condition=st.session_state.detection_end_condition,
                seeds_file=st.session_state.seeds_file,
            ),
            world=WorldConfig(
                origin_x=st.session_state.origin_x,
                origin_y=st.session_state.origin_y,
                length=st.session_state.length,
                height=st.session_state.height,
            ),  # Add any necessary world configuration here.
            # Dump to dicts so a stale class object (e.g. after a Streamlit hot-reload
            # redefines PlatformConfig) doesn't fail Pydantic's isinstance check.
            platforms=[p.model_dump() for p in st.session_state.platform_draft_list],
        )
        try:
            create_config_yaml(cfg_data)
            success("yaml_file_created", "config.yaml created successfully.")
            st.session_state.yaml_file_created = False
        except Exception as e:
            logger.exception("Error creating config.yaml: %s", e)
            st.error(
                f"An error occurred while creating config.yaml: {e}, cfg_data: {cfg_data}"
            )
    except Exception as e:
        logger.exception("❌ Error creating ConfigData object:\n")
        logger.exception("Exception: %s", e)


def main() -> None:
    """Render the home page."""
    st.title(":passenger_ship: :game_die: Run Monte Carlo")
    st.write(
        "To run the Monte Carlo simulation, first create at least one Red and one Blue platform."
    )

    # Render the platform status card and the platform table with delete buttons.
    ready_to_run_simulation = render_platform_status_card()
    render_platform_table_with_delete()

    create_yaml_button = st.button(
        "Create Config YAML",
        help="Create a config.yaml file from the current platforms.",
        on_click=create_cfg_data,
    )

    # Render the "Run Simulation" button, which is enabled only if the simulation is ready to run.
    run_simulation_clicked = st.button(
        "Run Simulation",
        disabled=not ready_to_run_simulation,
        help="Create at least one Red and one Blue platform before running the simulation."
        if not ready_to_run_simulation
        else None,
    )

    if run_simulation_clicked and ready_to_run_simulation and create_yaml_button:
        try:
            logger.info("Running simulation...")
            run_simulation()
            st.success("Monte Carlo simulation completed successfully!")
        except Exception as e:
            logger.exception("Error running simulation: %s", e)
            st.error(f"An error occurred while running the simulation: {e}")


main()
