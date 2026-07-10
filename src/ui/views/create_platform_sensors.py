"""
Sensor section rendering and validation for platform creation.
"""

from typing import Optional, Tuple
from src.ui.user_notifier import success, fail

import pandas as pd
import streamlit as st


def _parse_sensor_csv(sensor_table: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Normalize a sensor CSV into x_values and pod columns.
    """
    if {"x_values", "pod"}.issubset(sensor_table.columns):
        return sensor_table[["x_values", "pod"]], None

    if len(sensor_table.columns) >= 2:
        parsed_table = sensor_table.iloc[:, :2].copy()
        parsed_table.columns = ["x_values", "pod"]
        return parsed_table, "CSV columns were auto-mapped to x_values and pod."

    return pd.DataFrame(), "CSV must include x_values and pod columns, or at least two numeric columns."


def _is_single_sensor_complete(sensor_draft: dict) -> bool:
    """
    Validate a single sensor draft.
    """
    if not sensor_draft:
        return False

    display_name = bool(str(sensor_draft.get("display_name", "")).strip())
    sensor_type = bool(sensor_draft.get("sensor_type"))
    x_values = sensor_draft.get("x_values", [])
    pod = sensor_draft.get("pod", [])

    return (
        display_name
        and sensor_type
        and isinstance(x_values, list)
        and isinstance(pod, list)
        and len(x_values) > 0
        and len(x_values) == len(pod)
        and all(0.0 <= float(value) <= 1.0 for value in pod)
    )


def _extract_valid_sensor_points(table: pd.DataFrame) -> Tuple[list, list, Optional[str]]:
    """
    Normalize a table to x_values and pod lists and validate POD bounds.
    """
    if table.empty or not {"x_values", "pod"}.issubset(table.columns):
        return [], [], "No valid sensor rows found."

    normalized = table[["x_values", "pod"]].copy()
    normalized["x_values"] = pd.to_numeric(normalized["x_values"], errors="coerce")
    normalized["pod"] = pd.to_numeric(normalized["pod"], errors="coerce")
    normalized = normalized.dropna(subset=["x_values", "pod"])

    if normalized.empty:
        return [], [], "Provide at least one row with numeric x_values and pod values."

    out_of_bounds = normalized[(normalized["pod"] < 0.0) | (normalized["pod"] > 1.0)]
    if not out_of_bounds.empty:
        return [], [], "All pod values must be between 0 and 1."

    x_values = [float(value) for value in normalized["x_values"].tolist()]
    pod_values = [float(value) for value in normalized["pod"].tolist()]
    return x_values, pod_values, None


def _sync_sensor_draft_list(sensor_count: int) -> list:
    """
    Resize sensor_draft_list to match the requested sensor count.
    """
    sensor_draft_list = st.session_state.get("sensor_draft_list", [])

    if len(sensor_draft_list) < sensor_count:
        sensor_draft_list.extend(
            {
                "display_name": f"Sensor {index + 1}",
                "x_values": [],
                "pod": [],
                "sensor_type": "generic",
                "source": "manual",
            }
            for index in range(len(sensor_draft_list), sensor_count)
        )
    elif len(sensor_draft_list) > sensor_count:
        sensor_draft_list = sensor_draft_list[:sensor_count]

    st.session_state.sensor_draft_list = sensor_draft_list
    return sensor_draft_list


def _build_sensor_summary(sensor_draft_list: list) -> pd.DataFrame:
    """
    Build summary table required by the UI acceptance criteria.
    """
    rows = []
    for index, draft in enumerate(sensor_draft_list):
        rows.append(
            {
                "index": index + 1,
                "name": draft.get("display_name", ""),
                "type": draft.get("sensor_type", "").capitalize(),
                "x_values": str(draft.get("x_values", [])),
                "pod": str(draft.get("pod", [])),
                "source": draft.get("source", "manual").capitalize(),
                "status": "Ready" if _is_single_sensor_complete(draft) else "Incomplete",
            }
        )
    return pd.DataFrame(rows)


def _save_sensor(index: int, display_name: str, sensor_type: str, x_values: list, pod_values: list, source: str) -> None:
    """
    Persist a single sensor draft and trigger immediate refresh.
    """
    st.session_state.sensor_draft_list[index] = {
        "display_name": display_name,
        "x_values": x_values,
        "pod": pod_values,
        "sensor_type": sensor_type,
        "source": source,
    }
    success(f"sensor_{index}_saved", f"Sensor {index + 1} saved.")
    st.rerun()


def _render_manual_editor(
    index: int,
    display_name: str,
    sensor_type: str,
    default_table: pd.DataFrame,
    table_editor_key: str,
) -> None:
    """
    Render manual sensor editor for one row.
    """
    with st.form(key=f"sensor_manual_form_{index}", clear_on_submit=False):
        st.caption("Provide x_values and pod rows. POD must be between 0 and 1.")
        sensor_table = st.data_editor(
            default_table,
            num_rows="dynamic",
            use_container_width=True,
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
        x_values, pod_values, validation_error = _extract_valid_sensor_points(sensor_table)
        if validation_error:
            st.warning(f"Sensor {index + 1}: {validation_error}")
            return

        _save_sensor(index, display_name, sensor_type, x_values, pod_values, "manual")


def _render_import_editor(index: int, display_name: str, sensor_type: str) -> None:
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
                st.dataframe(parsed_table, use_container_width=True)

        save_clicked = st.form_submit_button("Save Sensor")

    if save_clicked:
        if parsed_table.empty:
            st.warning(f"Sensor {index + 1}: upload a valid CSV before saving.")
            return

        x_values, pod_values, validation_error = _extract_valid_sensor_points(parsed_table)
        if validation_error:
            st.warning(f"Sensor {index + 1}: {validation_error}")
            return

        _save_sensor(index, display_name, sensor_type, x_values, pod_values, "import")


def _render_single_sensor_editor(index: int, sensor_draft: dict) -> None:
    """
    Render one sensor editor entry.
    """
    mode_key = f"sensor_mode_widget_{index}"
    name_key = f"sensor_name_widget_{index}"
    type_key = f"sensor_type_widget_{index}"
    table_editor_key = f"sensor_table_widget_{index}"

    with st.expander(f"Sensor {index + 1}", expanded=not _is_single_sensor_complete(sensor_draft)):
        mode = st.radio(
            "Input Mode",
            options=["manual", "import"],
            key=mode_key,
            horizontal=True,
            index=0 if sensor_draft.get("source", "manual") == "manual" else 1,
        )

        display_name = st.text_input(
            "Sensor Name",
            key=name_key,
            value=sensor_draft.get("display_name", f"Sensor {index + 1}"),
        )
        sensor_type = st.selectbox(
            "Sensor Type",
            options=["generic", "specific"],
            key=type_key,
            index=0 if sensor_draft.get("sensor_type", "generic") == "generic" else 1,
        )

        if mode == "manual":
            default_table = (
                pd.DataFrame(
                    {
                        "x_values": sensor_draft.get("x_values", []),
                        "pod": sensor_draft.get("pod", []),
                    }
                )
                if sensor_draft.get("x_values") and sensor_draft.get("pod")
                else pd.DataFrame([{"x_values": 0.0, "pod": 0.0}])
            )
            _render_manual_editor(index, display_name, sensor_type, default_table, table_editor_key)
        else:
            _render_import_editor(index, display_name, sensor_type)


def is_sensor_draft_ready() -> bool:
    """
    Validate whether the sensor draft is complete and aligned for creation.
    """
    sensor_count = int(st.session_state.get("number_of_sensors", 0))
    if sensor_count == 0:
        return True

    sensor_draft_list = st.session_state.get("sensor_draft_list", [])
    if len(sensor_draft_list) != sensor_count:
        return False

    return all(_is_single_sensor_complete(sensor_draft) for sensor_draft in sensor_draft_list)


def render_sensor_creation() -> bool:
    """
    Wizard for creating one or more sensors for the platform.
    Returns True when all required sensors are complete.
    """
    st.markdown("## Sensor Details")

    if st.session_state.get("sensor_save_message"):
        st.success(st.session_state["sensor_save_message"])
        st.session_state["sensor_save_message"] = ""

    number_of_sensors = st.number_input(
        "Number of sensors",
        min_value=0,
        value=int(st.session_state.get("number_of_sensors", 0)),
        step=1,
        key="number_of_sensors",
    )

    sensor_count = int(number_of_sensors)
    sensor_draft_list = _sync_sensor_draft_list(sensor_count)

    if sensor_count == 0:
        st.info("No sensors required. You can continue and create the platform.")
        return True

    st.markdown("### Sensor Overview")
    st.dataframe(_build_sensor_summary(sensor_draft_list), use_container_width=True, hide_index=True)

    st.markdown("### Configure Sensors")
    for index in range(sensor_count):
        _render_single_sensor_editor(index, st.session_state.sensor_draft_list[index])

    return is_sensor_draft_ready()
