"""
Sensor section rendering and validation for platform creation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional, Tuple

import pandas as pd
import streamlit as st

from src.schemas.sensor import SensorFactory
from src.ui.user_notifier import success

if TYPE_CHECKING:
    from src.schemas.sensor import SensorConfig

logger = logging.getLogger(__name__)


def _parse_sensor_csv(sensor_table: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Normalise a sensor CSV into x_values and pod columns.
    """
    if {"x_values", "pod"}.issubset(sensor_table.columns):
        return sensor_table[["x_values", "pod"]], None

    if len(sensor_table.columns) >= 2:
        parsed_table = sensor_table.iloc[:, :2].copy()
        parsed_table.columns = ["x_values", "pod"]
        return parsed_table, "CSV columns were auto-mapped to x_values and pod."

    return (
        pd.DataFrame(),
        "CSV must include x_values and pod columns, or at least two numeric columns.",
    )


def _extract_valid_sensor_points(
    table: pd.DataFrame,
) -> Tuple[list, list, Optional[str]]:
    """
    Normalise a table to x_values and pod lists and validate POD bounds.
    validation step for x_values and pod lists, ensuring all pod values are between 0 and 1.
    """
    if table.empty or not {"x_values", "pod"}.issubset(table.columns):
        return [], [], "No valid sensor rows found."

    normalised = table[["x_values", "pod"]].copy()
    normalised["x_values"] = pd.to_numeric(normalised["x_values"], errors="coerce")
    normalised["pod"] = pd.to_numeric(normalised["pod"], errors="coerce")
    normalised = normalised.dropna(subset=["x_values", "pod"])

    if normalised.empty:
        return [], [], "Provide at least one row with numeric x_values and pod values."

    out_of_bounds = normalised[(normalised["pod"] < 0.0) | (normalised["pod"] > 1.0)]
    if not out_of_bounds.empty:
        return [], [], "All pod values must be between 0 and 1."

    x_values = [float(value) for value in normalised["x_values"].tolist()]
    pod_values = [float(value) for value in normalised["pod"].tolist()]
    return x_values, pod_values, None


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
                "type": draft.get("sensor_type", "").capitalize(),
                "x_values": draft.get("x_values", []),
                "pod": draft.get("pod", []),
                "status": "Ready",
            }
        )
    return pd.DataFrame(rows)


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

    # Create Sensor Config
    sensor_config: tuple[Optional[SensorConfig], list[str]] = (
        SensorFactory.create_sensor(**sensor_data_payload)
    )

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
    with st.form(key=f"sensor_manual_form_{index}", clear_on_submit=False):
        st.caption("Provide x_values and pod rows. POD must be between 0 and 1.")

        # Extract sensor performance data
        default_table = {
            "x_values": sensor_data_payload.get("x_values", []),
            "pod": sensor_data_payload.get("pod", []),
        }

        sensor_table = st.data_editor(
            pd.DataFrame(default_table),
            num_rows="dynamic",
            width="stretch",
            column_config={
                "x_values": st.column_config.NumberColumn(
                    "x_values",
                    help="Independent variable (e.g. range or time).",
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
        # validate table before saving
        x_values, pod_values, validation_error = _extract_valid_sensor_points(
            sensor_table
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
    with st.form(key=f"sensor_import_form_{index}", clear_on_submit=False):
        parsed_table = pd.DataFrame()
        uploaded_file = st.file_uploader(
            "Choose a sensor CSV file",
            type="csv",
            key=f"sensor_csv_upload_{index}",
        )
        if uploaded_file is not None:
            raw_table = pd.read_csv(uploaded_file)
            parsed_table, parse_message = _parse_sensor_csv(raw_table)
            if parse_message:
                if parsed_table.empty:
                    st.error(parse_message)
                else:
                    st.warning(parse_message)
            if not parsed_table.empty:
                st.dataframe(parsed_table, width="stretch")

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
        )

        # K of N
        k = st.number_input("K", key=k_key, value=3, min_value=1)
        n = st.number_input("N", key=n_key, value=5, min_value=1)

        default_table = {
            "x_values": [0, 100, 200, 500, 1000],
            "pod": [1.0, 0.8, 0.6, 0.4, 0.2],
        }

        sensor_data_payload: dict = {
            "display_name": display_name,
            "sensor_type": sensor_type,
            "interval_time_sec": interval_time_sec,
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
