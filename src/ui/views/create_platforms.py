"""
Creates platform
"""

import logging

import pandas as pd
import streamlit as st

from src.schemas.movement import IntruderEndCondition
from src.schemas.platform import PlatformConfig
from src.ui.user_notifier import success
from src.ui.views.create_platform_sensors import render_sensor_creation

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def is_platform_draft_ready() -> bool:
    """
    Validate whether the platform draft has enough information to be created.
    """
    draft = st.session_state.get("platform_draft", {})
    if not draft:
        return False

    has_name = bool(str(draft.get("display_name", "")).strip())
    has_team = bool(draft.get("team"))
    has_movement = bool(draft.get("movement_type"))
    movement_config = draft.get("movement_config", {})

    if draft.get("movement_type") == "User Defined Waypoints":
        has_waypoints = bool(movement_config.get("waypoints"))
        return has_name and has_team and has_movement and has_waypoints

    return has_name and has_team and has_movement


def render_platform_movement_inputs(movement_type: str) -> dict:
    """
    Render movement-specific inputs and return them as a config dictionary.
    """
    movement_config: dict = {}

    with st.container(border=True):
        st.markdown("### Movement Settings")

        if movement_type == "Random Walk":
            st.caption("Random walk does not require extra parameters.")

        elif movement_type == "Intruder Search":
            movement_config["start_distance"] = st.number_input(
                "Start Distance",
                min_value=0.0,
                value=0.0,
                step=0.1,
                key="start_distance",
            )
            end_condition = st.selectbox(
                "End Condition",
                options=[condition.value for condition in IntruderEndCondition],
                key="end_condition",
            )
            movement_config["end_condition"] = end_condition

        elif movement_type == "Barrier Patroller":
            movement_config["start_x_pos"] = st.number_input(
                "Start X Position",
                value=0.0,
                step=0.1,
                key="start_x_pos",
            )
            movement_config["start_y_pos"] = st.number_input(
                "Start Y Position",
                value=0.0,
                step=0.1,
                key="movement_start_y_pos",
            )
            movement_config["length"] = st.number_input(
                "Patrol Length",
                min_value=0.0,
                value=100.0,
                step=1.0,
                key="movement_length",
            )
            movement_config["height"] = st.number_input(
                "Patrol Height",
                min_value=0.0,
                value=100.0,
                step=1.0,
                key="movement_height",
            )

        elif movement_type == "User Defined Waypoints":
            import_tab, manual_tab = st.tabs(["Import CSV", "Manual Input"])

            with import_tab:
                st.markdown("Upload a CSV with `x` and `y` columns.")
                uploaded_waypoints = st.file_uploader(
                    "Choose a waypoint CSV file",
                    type="csv",
                    key="movement_waypoints_csv",
                )
                if uploaded_waypoints is not None:
                    waypoint_table = pd.read_csv(uploaded_waypoints)
                    if {"x", "y"}.issubset(waypoint_table.columns):
                        st.dataframe(waypoint_table[["x", "y"]], width="stretch")
                        movement_config["waypoints"] = [
                            {"x": float(row["x"]), "y": float(row["y"])}
                            for _, row in waypoint_table[["x", "y"]].iterrows()
                        ]
                    else:
                        st.error("Waypoint CSV must contain `x` and `y` columns.")

            with manual_tab:
                default_waypoint_table = pd.DataFrame([{"x": 0.0, "y": 0.0}])
                waypoint_table = st.data_editor(
                    default_waypoint_table,
                    num_rows="dynamic",
                    width="stretch",
                    key="movement_waypoints_table",
                )
                if "waypoints" not in movement_config:
                    movement_config["waypoints"] = [
                        {"x": float(row["x"]), "y": float(row["y"])}
                        for _, row in waypoint_table.iterrows()
                    ]

    movement_config["pattern"] = movement_type.lower().replace(" ", "_")
    return movement_config


def render_platform_creation() -> bool:
    """
    Renders the platform creation interface in the Streamlit application.
    """
    st.markdown("## Create a new platform for simulation")

    platform_name = st.text_input(
        "Platform Name",
        key="platform_name",
        placeholder="Enter platform name",
        value="Platform 1",
    )
    platform_speed = st.number_input(
        "Platform Speed (m/s)", min_value=0.0, value=0.0, step=0.1, key="platform_speed"
    )
    platform_team = st.selectbox(
        "Platform Team", options=["Blue", "Red"], key="platform_team"
    )
    platform_movement_type = st.selectbox(
        "Platform Movement Type",
        options=[
            "Random Walk",
            "Intruder Search",
            "Barrier Patroller",
            "User Defined Waypoints",
        ],
        key="platform_movement_type",
    )
    platform_movement_config = render_platform_movement_inputs(platform_movement_type)

    st.session_state.platform_draft = {
        "display_name": platform_name,
        "speed": platform_speed,
        "team": platform_team,
        "movement_type": platform_movement_type,
        "movement_config": platform_movement_config,
    }

    return is_platform_draft_ready()


def create_platform() -> None:
    """
    Creates a platform based on the current session state and notifies the user.
    """
    if "platform_draft" in st.session_state:
        platform_draft = dict(st.session_state.platform_draft)
        logger.info(
            "Creating platform with draft: %s \n %s",
            platform_draft,
            st.session_state.platform_draft_list,
        )
        sensor_draft_list = st.session_state.get("sensor_draft_list", [])
        if sensor_draft_list:
            platform_draft["sensors"] = sensor_draft_list

        logger.info("Creating platform with draft: %s", platform_draft)

        try:
            # platform = PlatformDraft.create_from_dict(platform_draft)
            platform = PlatformConfig(
                platform_config_folder=platform_draft["display_name"],
                display_name=platform_draft["display_name"],
                speed_mps=platform_draft["speed"],
                team=platform_draft["team"],
                movement_type=platform_draft["movement_config"],
                neutralised_platform_behaviour="stop",  # TODO: Make this configurable in the UI if needed
                sensors=platform_draft.get("sensors", []),
            )
            st.session_state.platform_draft_list.append(platform)

            success(
                "platform_created",
                f"Platform '{platform_draft['display_name']}' created successfully!",
            )

            if st.session_state.get("platform_created", False):
                logger.debug("Platform created successfully! %s", platform)

                # Reset states
                st.session_state["platform_created"] = False
                st.session_state["platform_draft"] = {}
                st.session_state["sensor_draft_list"] = []
        except Exception as e:
            logger.exception("Error creating platform: %s", e)
            return

    else:
        logger.warning("No platform draft found in session state.")


def main() -> None:
    """
    Main function to run the platform creation view.
    """
    st.title("📊 Create Platforms")
    platform_ready = render_platform_creation()
    sensor_ready = render_sensor_creation()

    st.caption(
        f"Platform details: {'Ready' if platform_ready else 'Incomplete'} | "
        f"Sensor details: {'Ready' if sensor_ready else 'Incomplete'}"
    )

    st.button(
        "Create Platform",
        on_click=create_platform,
        disabled=not (platform_ready and sensor_ready),
        help="Complete both platform and sensor sections to create a platform.",
    )


main()
