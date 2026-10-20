"""
Sensor section rendering and validation for platform creation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd
import streamlit as st

from src.schemas.sensor import SensorFactory
from src.ui.services.performance_table import (
    _extract_valid_sensor_points,
    _parse_sensor_csv,
    _x_axis_label,
)
from src.ui.user_notifier import success

if TYPE_CHECKING:
    from src.schemas.sensor import SensorConfig

logger = logging.getLogger(__name__)


def _build_sensor_summary(sensor_draft_list: list[SensorConfig]) -> pd.DataFrame:
    """
    Build summary table required by the UI acceptance criteria.

    args:
        sensor_draft_list (list[SensorConfig]): List of sensor drafts to build the summary table from, collection of Pydantic objects.
    """
    if not sensor_draft_list:
        return pd.DataFrame()

    rows = []
    sensor_draft_list: list[dict[str, Any]] = [
        sensor.model_dump() for sensor in sensor_draft_list
    ]
    for index, draft in enumerate(sensor_draft_list):
        rows.append(
            {
                "index": index + 1,
                "name": draft.get("display_name", ""),
                "interval_time_sec": draft.get("interval_time_sec", 1.0),
                "type": draft.get("type", "").capitalize(),
                "active_source": draft.get("active_source", False),
                "collocated": draft.get("source_receiver_collocated", False),
                "fov_start_deg": draft.get("fov_start_deg", None),
                "fov_end_deg": draft.get("fov_end_deg", None),
                "x_values": draft.get("x_values", []),
                "pod": draft.get("pod", []),
                "status": "Ready",
            }
        )
    return pd.DataFrame(rows)


def _is_duplicate_sensor_name(display_name: str) -> bool:
    """
    Check whether a sensor with the given display name already exists in the draft list.
    """
    existing_names = {
        sensor.display_name.strip().lower()
        for sensor in st.session_state.get("sensor_draft_list", [])
    }
    return display_name.strip().lower() in existing_names


def _save_sensor(
    index: int,
    sensor_data_payload: dict,
) -> None:
    """
    Persist a single sensor draft and trigger immediate refresh.
    """

    # Check if sensor display name is not empty and not in stored inside sensor_draft_list
    display_name = sensor_data_payload.get("display_name", "")
    if not display_name:
        st.warning(f"Sensor {index + 1}: Display name cannot be empty.")
        return

    if _is_duplicate_sensor_name(display_name):
        st.warning(
            f"Sensor {index + 1}: A sensor named '{display_name}' already exists. Choose a different name."
        )
        return

    # Create Sensor Config
    sensor_config: tuple[Optional[SensorConfig], list[str]] = (
        SensorFactory.create_sensor(**sensor_data_payload)
    )
    logger.info("Sensor config created: %s", sensor_config)

    if sensor_config[0] is None:
        error_messages = sensor_config[1]
        st.warning(
            f"Sensor {index + 1}: Failed to create sensor configuration. Errors: {', '.join(error_messages)}"
        )
        return

    st.session_state.sensor_draft_list.append(sensor_config[0])

    success(f"sensor_{index}_saved", f"Sensor {index + 1} saved.")
    st.session_state.sensor_edit_index += 1
    logger.info(st.session_state.sensor_draft_list)
    st.rerun()


def _render_manual_editor(
    index: int,
    sensor_data_payload: dict,
    table_editor_key: str,
) -> None:
    sensor_type = str(sensor_data_payload.get("sensor_type", "generic"))
    x_label = _x_axis_label(sensor_type)
    caption_text = (
        "Provide distance_m and pod rows. POD must be between 0 and 1."
        if x_label == "distance_m"
        else "Provide x_values and pod rows. POD must be between 0 and 1."
    )
    with st.form(key=f"sensor_manual_form_{index}", clear_on_submit=False):
        st.caption(caption_text)

        # Extract sensor performance data
        default_table = {
            x_label: sensor_data_payload.get("x_values", []),
            "pod": sensor_data_payload.get("pod", []),
        }

        help_text = (
            "Distance in metres from the sensor."
            if x_label == "distance_m"
            else "Independent variable (e.g. range or time)."
        )

        sensor_table = st.data_editor(
            pd.DataFrame(default_table),
            num_rows="dynamic",
            width="stretch",
            column_config={
                x_label: st.column_config.NumberColumn(
                    x_label,
                    help=help_text,
                    required=True,
                ),
                "pod": st.column_config.NumberColumn(
                    "pod",
                    help="Probability of detection in [0, 1].",
                    min_value=0.0,
                    max_value=1.0,
                    required=True,
                ),
            },
            key=table_editor_key,
        )

        save_clicked = st.form_submit_button("Save Sensor")

    if save_clicked:
        # validate table before saving (ensure x_values column is present)
        table_to_validate = sensor_table.copy()
        if x_label in table_to_validate.columns and "x_values" not in table_to_validate.columns:
            table_to_validate = table_to_validate.rename(columns={x_label: "x_values"})

        x_values, pod_values, validation_error = _extract_valid_sensor_points(
            table_to_validate
        )

        # Update payload
        sensor_data_payload["x_values"] = x_values
        sensor_data_payload["pod"] = pod_values

        if validation_error:
            st.warning(f"Sensor {index + 1}: {validation_error}")
            return

        _save_sensor(
            index,
            sensor_data_payload,
        )


def _render_import_editor(index: int, sensor_data_payload: dict) -> None:
    """
    Render CSV import editor for one row.
    """
    sensor_type = str(sensor_data_payload.get("sensor_type", "generic"))
    x_label = _x_axis_label(sensor_type)

    with st.form(key=f"sensor_import_form_{index}", clear_on_submit=False):
        parsed_table = pd.DataFrame()
        uploaded_file = st.file_uploader(
            "Choose a sensor CSV file",
            type="csv",
            key=f"sensor_csv_upload_{index}",
        )
        if uploaded_file is not None:
            raw_table = pd.read_csv(uploaded_file)
            parsed_table, parse_message = _parse_sensor_csv(raw_table, sensor_type=sensor_type)
            if parse_message:
                if parsed_table.empty:
                    st.error(parse_message)
                else:
                    st.warning(parse_message)
            if not parsed_table.empty:
                preview_table = parsed_table.rename(columns={"x_values": x_label})
                st.dataframe(preview_table, width="stretch")

        save_clicked = st.form_submit_button("Save Sensor")

    if save_clicked:
        if parsed_table.empty:
            st.warning(f"Sensor {index + 1}: upload a valid CSV before saving.")
            return

        x_values, pod_values, validation_error = _extract_valid_sensor_points(
            parsed_table
        )

        # Update payload
        sensor_data_payload["x_values"] = x_values
        sensor_data_payload["pod"] = pod_values

        if validation_error:
            st.warning(f"Sensor {index + 1}: {validation_error}")
            return

        _save_sensor(index, sensor_data_payload)


def _render_single_sensor_editor(index: int) -> None:
    """
    Render one sensor editor entry.

    Args:
        index (int): The index of the sensor in the list.
        sensor_draft (dict): The draft data for the sensor in the session state draft list.
    """
    mode_key = f"sensor_mode_widget_{index}"
    name_key = f"sensor_name_widget_{index}"
    type_key = f"sensor_type_widget_{index}"
    k_key = f"sensor_k_widget_{index}"
    n_key = f"sensor_n_widget_{index}"
    table_editor_key = f"sensor_table_widget_{index}"

    with st.expander(f"Sensor {index + 1}"):
        mode = st.radio(
            "Input Mode",
            options=["manual", "import"],
            key=mode_key,
            horizontal=True,
        )

        display_name = st.text_input(
            "Sensor Name",
            key=name_key,
            value=f"Sensor {index + 1}",
        )
        sensor_type = st.selectbox(
            "Sensor Type",
            options=["generic", "specific"],
            key=type_key,
        )
        interval_time_sec = st.number_input(
            "Interval Time (sec)",
            key=f"sensor_interval_time_widget_{index}",
            value=1.0,
            min_value=0.0,
            help="Time interval between sensor evaluations in seconds.",
        )

        # K of N
        k = st.number_input(
            "K",
            key=k_key,
            value=3,
            min_value=1,
            help="Determines the number of True detections",
        )
        n = st.number_input(
            "N",
            key=n_key,
            value=5,
            min_value=1,
            help="Determines the size of the sliding window for K-of-N evaluation",
        )

        if sensor_type == "generic":
            fov_start_deg = st.number_input(
                "FOV Start (deg)",
                key=f"sensor_fov_start_widget_{index}",
                value=0.0,
                min_value=0.0,
                help="Field of View (degrees), 0 degrees points East and moves counterclockwise around the platform and moves with it as the platform moves.",
            )
            fov_end_deg = st.number_input(
                "FOV End (deg)",
                key=f"sensor_fov_end_widget_{index}",
                value=90.0,
                min_value=0.0,
                max_value=360.0,
                help="Field of View (degrees), 0 degrees points East and moves counterclockwise around the platform and moves with it as the platform moves.",
            )
        else:
            fov_start_deg = None
            fov_end_deg = None

        platform_team = st.session_state.get("platform_team", "")
        if platform_team == "Blue":
            active_source = st.checkbox(
                "Active Source",
                key=f"sensor_active_source_widget_{index}",
                value=False,
                help="Emits omnidirectional active acoustic pings.",
            )
            collocated = st.checkbox(
                "Source/Receiver Collocated",
                key=f"sensor_collocated_widget_{index}",
                value=False,
                disabled=not active_source,
                help="Whether this platform also functions as a monostatic receiver for its own pings.",
            )
            if not active_source:
                collocated = False
        else:
            active_source = False
            collocated = False

        default_table = {
            "x_values": [0, 100, 200, 500, 1000],
            "pod": [1.0, 0.8, 0.6, 0.4, 0.2],
        }

        sensor_data_payload: dict = {
            "display_name": display_name,
            "sensor_type": sensor_type,
            "interval_time_sec": interval_time_sec,
            "active_source": active_source,
            "source_receiver_collocated": collocated,
            "fov_start_deg": fov_start_deg,
            "fov_end_deg": fov_end_deg,
            "x_values": default_table["x_values"],
            "pod": default_table["pod"],
            "k": k,
            "n": n,
        }

        if mode == "manual":
            _render_manual_editor(index, sensor_data_payload, table_editor_key)
        else:
            _render_import_editor(index, sensor_data_payload)


def render_sensor_creation() -> bool:
    """
    Wizard for creating one or more sensors for the platform.
    Returns True when all required sensors are complete.
    """
    st.markdown("## Sensor Details")

    if st.session_state.get("sensor_save_message"):
        st.success(st.session_state["sensor_save_message"])
        st.session_state["sensor_save_message"] = ""

    equip_sensor = st.radio(
        "Equip Sensor?",
        options=["Yes", "No"],
        key="input_mode",
        horizontal=True,
        index=1,
    )

    if equip_sensor == "No":
        st.info(
            "Platform will not be able to detect with no sensors. However, can continue and create the platform."
        )
        return True

    st.markdown("### Sensor Overview")
    st.dataframe(
        _build_sensor_summary(st.session_state.sensor_draft_list),
        width="stretch",
        hide_index=True,
    )

    st.markdown("### Configure Sensors")
    if equip_sensor == "Yes":
        _render_single_sensor_editor(st.session_state.sensor_edit_index)

    return True
