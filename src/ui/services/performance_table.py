"""
Shared PoD performance table parsing and validation services for sensors and sonobuoys.
"""

from __future__ import annotations

from typing import Optional
import pandas as pd


def x_axis_label(sensor_type: str) -> str:
    """Return the label for the independent variable column depending on sensor type."""
    if (sensor_type or "").lower() == "generic":
        return "distance_m"
    return "x_values"


def parse_sensor_csv(
    sensor_table: pd.DataFrame,
    sensor_type: str = "generic",
) -> tuple[pd.DataFrame, Optional[str]]:
    """Normalise a sensor CSV into x_values and pod columns."""
    target_x_col = x_axis_label(sensor_type)

    for col_name in [target_x_col, "distance_m", "range_m", "x_values"]:
        if {col_name, "pod"}.issubset(sensor_table.columns):
            parsed = sensor_table[[col_name, "pod"]].copy()
            parsed.columns = ["x_values", "pod"]
            msg = (
                f"CSV column '{col_name}' was mapped to {target_x_col}."
                if col_name != target_x_col and col_name != "x_values"
                else None
            )
            return parsed, msg

    if len(sensor_table.columns) >= 2:
        parsed_table = sensor_table.iloc[:, :2].copy()
        parsed_table.columns = ["x_values", "pod"]
        return parsed_table, f"CSV columns were auto-mapped to {target_x_col} and pod."

    return (
        pd.DataFrame(),
        f"CSV must include {target_x_col} (or range_m/x_values) and pod columns, or at least two numeric columns.",
    )


def extract_valid_sensor_points(
    table: pd.DataFrame,
) -> tuple[list[float], list[float], Optional[str]]:
    """Normalise a table to x_values and pod lists and validate POD bounds."""
    if table.empty or not {"x_values", "pod"}.issubset(table.columns):
        return [], [], "No valid sensor rows found."

    normalised = table[["x_values", "pod"]].copy()
    normalised["x_values"] = pd.to_numeric(normalised["x_values"], errors="coerce")
    normalised["pod"] = pd.to_numeric(normalised["pod"], errors="coerce")
    normalised = normalised.dropna(subset=["x_values", "pod"])

    if normalised.empty:
        return [], [], "Provide at least one row with numeric values and pod values."

    out_of_bounds = normalised[(normalised["pod"] < 0.0) | (normalised["pod"] > 1.0)]
    if not out_of_bounds.empty:
        return [], [], "All pod values must be between 0 and 1."

    x_values = [float(value) for value in normalised["x_values"].tolist()]
    pod_values = [float(value) for value in normalised["pod"].tolist()]
    return x_values, pod_values, None


# Backward-compatible private aliases
_x_axis_label = x_axis_label
_parse_sensor_csv = parse_sensor_csv
_extract_valid_sensor_points = extract_valid_sensor_points
