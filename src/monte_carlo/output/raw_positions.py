from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.schemas.output import PlatformPositionEvent

# Column order for the raw positions data (internal / SI units)
RAW_COLUMN_ORDER: dict[str, pd.Series] = {
    "replication_id": pd.Series(dtype="int64"),
    "platform_id": pd.Series(dtype="string"),
    "team": pd.Series(dtype="string"),
    "timestamp": pd.Series(dtype="float64"),
    "pos_x": pd.Series(dtype="float64"),
    "pos_y": pd.Series(dtype="float64"),
    "heading": pd.Series(dtype="float64"),
    "speed": pd.Series(dtype="float64"),
    "waypoint_x": pd.Series(dtype="float64"),
    "waypoint_y": pd.Series(dtype="float64"),
    "status": pd.Series(dtype="string"),
    "detecting_platform_id": pd.Series(dtype="string"),
    "target_platform_id": pd.Series(dtype="int64"),
    "detection_made": pd.Series(dtype="bool"),
    "detection_sensor_name": pd.Series(dtype="string"),
    "detection_distance_m": pd.Series(dtype="float64"),
}
# Column types and order for the CSV file written to disk
CSV_COLUMN_ORDER: dict[str, pd.Series] = {
    "replication_id": pd.Series(dtype="int64"),
    "platform_id": pd.Series(dtype="string"),
    "pos_x_km": pd.Series(dtype="float64"),
    "pos_y_km": pd.Series(dtype="float64"),
    "waypoint_x_km": pd.Series(dtype="float64"),
    "waypoint_y_km": pd.Series(dtype="float64"),
    "timestamp_minutes": pd.Series(dtype="float64"),
    "team": pd.Series(dtype="string"),
    "detecting_platform_id": pd.Series(dtype="string"),
    "heading": pd.Series(dtype="float64"),
    "speed_kmh": pd.Series(dtype="float64"),
    "status": pd.Series(dtype="string"),
    "target_platform_id": pd.Series(dtype="int64"),
    "detection_made": pd.Series(dtype="bool"),
    "detection_sensor_name": pd.Series(dtype="string"),
    "detection_distance_m": pd.Series(dtype="float64"),
}


def build_positions_df(
    platform_position_events: list[PlatformPositionEvent],
) -> pd.DataFrame:
    """
    Convert a list of raw timestep dicts into a unit-converted positions DataFrame.

    This helper is shared by the streaming path (called after each replication)
    and the in-memory path (called inside write_raw_positions_csv).  Extracting
    the logic here avoids duplicating the unit-conversion and column-ordering code.

    Conversions applied:
    - pos_x / pos_y / waypoint_x / waypoint_y : metres → kilometres (rounded to 2 dp)
    - speed : m/s → km/h
    - timestamp : seconds → minutes

    Args:
        platform_position_events: List of per-agent-per-timestep state dicts produced by simulation.

    Returns:
        DataFrame with the columns defined in CSV_COLUMN_ORDER, ready to
        append to or write as raw_positions.csv.
    """
    df = pd.DataFrame(platform_position_events)
    if df.empty:
        return pd.DataFrame(CSV_COLUMN_ORDER)

    # Unit conversions
    df["pos_x_km"] = (df["pos_x"] / 1000.0).round(2)
    df["pos_y_km"] = (df["pos_y"] / 1000.0).round(2)
    df["waypoint_x_km"] = (df["waypoint_x"] / 1000.0).round(2)
    df["waypoint_y_km"] = (df["waypoint_y"] / 1000.0).round(2)
    df["speed_kmh"] = df["speed"] * 3.6
    df["timestamp_minutes"] = df["timestamp"] / 60.0

    return df[list(CSV_COLUMN_ORDER)]
