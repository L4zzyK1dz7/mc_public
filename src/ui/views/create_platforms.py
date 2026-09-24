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

KM_TO_M = 1000.0


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

    if has_name and _is_duplicate_platform_name(draft.get("display_name", "")):
        return False

    if draft.get("movement_type") == "User Defined Waypoints":
        has_waypoints = bool(movement_config.get("waypoints"))
        return has_name and has_team and has_movement and has_waypoints

    return has_name and has_team and has_movement


def _is_duplicate_platform_name(display_name: str) -> bool:
    """
    Check whether a platform with the given display name already exists in the draft list.
    """
    existing_names = {
        platform.display_name.strip().lower()
        for platform in st.session_state.get("platform_draft_list", [])
    }
    return str(display_name).strip().lower() in existing_names


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
            start_distance_km = st.number_input(
                "Start Distance (km)",
                min_value=0.0,
                value=0.0,
                step=0.1,
                key="start_distance",
            )
            movement_config["start_distance_m"] = start_distance_km * KM_TO_M
            end_condition = st.selectbox(
                "End Condition",
                options=[condition.value for condition in IntruderEndCondition],
                key="end_condition",
            )
            movement_config["end_condition"] = end_condition

        elif movement_type == "Barrier Patroller":
            start_x_pos_km = st.number_input(
                "Start X Position (km)",
                value=0.0,
                step=0.1,
                key="start_x_pos",
            )
            movement_config["start_x_pos"] = start_x_pos_km * KM_TO_M
            start_y_pos_km = st.number_input(
                "Start Y Position (km)",
                value=0.0,
                step=0.1,
                key="movement_start_y_pos",
            )
            movement_config["start_y_pos"] = start_y_pos_km * KM_TO_M
            length_km = st.number_input(
                "Patrol Length (km)",
                min_value=0.0,
                value=0.1,
                step=0.01,
                key="movement_length",
            )
            movement_config["length"] = length_km * KM_TO_M
            height_km = st.number_input(
                "Patrol Height (km)",
                min_value=0.0,
                value=0.1,
                step=0.01,
                key="movement_height",
            )
            movement_config["height"] = height_km * KM_TO_M

        elif movement_type == "User Defined Waypoints":
            import_tab, manual_tab = st.tabs(["Import CSV", "Manual Input"])

            with import_tab:
                st.markdown("Upload a CSV with `x` and `y` columns (in km).")
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
                            {
                                "x": float(row["x"]) * KM_TO_M,
                                "y": float(row["y"]) * KM_TO_M,
                            }
                            for _, row in waypoint_table[["x", "y"]].iterrows()
                        ]
                    else:
                        st.error("Waypoint CSV must contain `x` and `y` columns.")

            with manual_tab:
                st.caption("Enter x and y coordinates in km.")
                default_waypoint_table = pd.DataFrame([{"x": 0.0, "y": 0.0}])
                waypoint_table = st.data_editor(
                    default_waypoint_table,
                    num_rows="dynamic",
                    width="stretch",
                    key="movement_waypoints_table",
                )
                if "waypoints" not in movement_config:
                    movement_config["waypoints"] = [
                        {
                            "x": float(row["x"]) * KM_TO_M,
                            "y": float(row["y"]) * KM_TO_M,
                        }
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
    if platform_name and _is_duplicate_platform_name(platform_name):
        st.error(
            f"A platform named '{platform_name}' already exists. Choose a different name."
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

    # neutralised behaviour
    platform_neutralised_behaviour = st.selectbox(
        "Neutralised Platform Behaviour",
        options=[
            "Stop",
            "Continue",
        ],
        key="platform_neutralised_behaviour",
        help="Required for Team Detection. Determines how the platform behaves when neutralised.",
    )

    platform_movement_config = render_platform_movement_inputs(platform_movement_type)

    st.session_state.platform_draft = {
        "display_name": platform_name,
        "speed": platform_speed,
        "team": platform_team,
        "movement_type": platform_movement_type,
        "movement_config": platform_movement_config,
        "neutralised_behaviour": platform_neutralised_behaviour,
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

        if _is_duplicate_platform_name(platform_draft.get("display_name", "")):
            st.warning(
                f"A platform named '{platform_draft.get('display_name')}' already exists. Choose a different name."
            )
            return

        sensor_draft_list = st.session_state.get("sensor_draft_list", [])
        if sensor_draft_list:
            platform_draft["sensors"] = sensor_draft_list

        logger.info("Creating platform with draft: %s", platform_draft)

        try:
            # # Resolve Sensor Config
            # sensor_types: list[str] = platform_draft.get("sensors") or []
            # sensor_config = [SensorFactory.create_sensor(sensor_type) for sensor_type in sensor_types]

            platform = PlatformConfig(
                platform_config_folder=platform_draft["display_name"],
                display_name=platform_draft["display_name"],
                speed_mps=platform_draft["speed"],
                team=platform_draft["team"],
                movement_type=platform_draft["movement_config"],
                neutralised_platform_behaviour=platform_draft[
                    "neutralised_behaviour"
                ],  # TODO: Make this configurable in the UI if needed
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
                st.session_state["sensor_edit_index"] = 0

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
