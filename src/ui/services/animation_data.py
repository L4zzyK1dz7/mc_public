"""Loads a self-contained run folder into the plain data shapes
`platform_animation.build_animation` needs.

A run folder (produced by `run_simulation`) contains its own `input_data/`
snapshot plus `raw_positions.csv`, so this module never touches the live
`input_data/` - reanimating an old run is unaffected by later config changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from src.monte_carlo.configuration.load_configuration import load_config_from_yaml
from src.monte_carlo.states.platform_states import assign_platform_ids
from src.schemas.simulation import ConfigData
from src.ui.plotting.platform_animation import (
    DetectionEvent,
    PlatformAnimationData,
    PlatformPosition,
    SensorDefinition,
    SimulationTiming,
)

REQUIRED_POSITION_COLUMNS = {
    "replication_id",
    "platform_id",
    "pos_x_km",
    "pos_y_km",
    "waypoint_x_km",
    "waypoint_y_km",
    "timestamp_minutes",
    "team",
    "target_platform_id",
    "detection_made",
    "detection_sensor_name",
    "detection_distance_km",
}
_STRING_COLUMNS = {"platform_id", "team", "target_platform_id", "detection_sensor_name"}


def load_timing(config_data: ConfigData) -> SimulationTiming:
    """Extract animation timing from a validated ConfigData."""
    return {
        "time_limit_sec": config_data.simulation.time_limit_sec,
        "world_timestep_sec": config_data.simulation.timestep_sec,
    }


def load_sensors(config_data: ConfigData) -> List[SensorDefinition]:
    """Build sensor field-of-view definitions, keyed by the same runtime platform ids
    (Blue_1, Red_1, ...) that raw_positions.csv uses - not the config display_name.
    """
    platform_ids = assign_platform_ids(config_data.platforms)

    sensors: List[SensorDefinition] = []
    for platform_id, platform in zip(platform_ids, config_data.platforms):
        for sensor in platform.sensors:
            sensors.append(
                {
                    "platform_id": platform_id,
                    "name": sensor.display_name,
                    "fov_start_deg": getattr(sensor, "fov_start_angle", 0.0),
                    "fov_end_deg": getattr(sensor, "fov_end_angle", 360.0),
                    "range_km": (
                        max(sensor.x_values) / 1000.0 if sensor.x_values else 0.0
                    ),
                }
            )
    return sensors


def load_positions(csv_path: Path) -> pd.DataFrame:
    """Load and lightly normalise raw_positions.csv for one run."""
    positions = pd.read_csv(csv_path, skipinitialspace=True)
    positions.columns = positions.columns.str.strip()

    missing_columns = REQUIRED_POSITION_COLUMNS.difference(positions.columns)
    if missing_columns:
        raise ValueError(
            "raw_positions.csv is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    for column in _STRING_COLUMNS:
        positions[column] = positions[column].astype("string").str.strip()
        positions[column] = positions[column].replace({"": pd.NA})

    positions["detection_made"] = (
        positions["detection_made"].astype("string").str.strip().str.lower() == "true"
    )

    numeric_columns = REQUIRED_POSITION_COLUMNS - _STRING_COLUMNS - {"detection_made"}
    positions[list(numeric_columns)] = positions[list(numeric_columns)].apply(
        pd.to_numeric, errors="raise"
    )

    positions["timestamp_sec"] = positions["timestamp_minutes"] * 60.0
    return positions.sort_values(
        ["replication_id", "timestamp_sec", "platform_id"]
    ).reset_index(drop=True)


def load_animation_inputs(
    run_folder: Path,
) -> Tuple[pd.DataFrame, List[SensorDefinition], SimulationTiming]:
    """Load everything needed to animate any replication in a self-contained run folder."""
    config_path = run_folder / "input_data" / "config.yaml"
    positions_path = run_folder / "raw_positions.csv"

    config_data = load_config_from_yaml(config_path)
    return (
        load_positions(positions_path),
        load_sensors(config_data),
        load_timing(config_data),
    )


def build_platforms(
    positions: pd.DataFrame,
    sensors: List[SensorDefinition],
    replication_id: int,
) -> Dict[str, PlatformAnimationData]:
    """Slice positions down to one replication and group them per platform."""
    replication = positions[positions["replication_id"] == replication_id]
    if replication.empty:
        raise ValueError(f"Replication {replication_id} has no position data")

    sensor_by_platform: Dict[str, List[SensorDefinition]] = {}
    for sensor in sensors:
        sensor_by_platform.setdefault(sensor["platform_id"], []).append(sensor)

    platforms: Dict[str, PlatformAnimationData] = {}
    for platform_id, platform_rows in replication.groupby("platform_id"):
        records: List[PlatformPosition] = []
        for row in platform_rows.sort_values("timestamp_sec").itertuples():
            records.append(
                {
                    "platform_id": str(row.platform_id),
                    "team": str(row.team),
                    "timestamp_sec": float(row.timestamp_sec),
                    "pos_x_km": float(row.pos_x_km),
                    "pos_y_km": float(row.pos_y_km),
                    "waypoint_x_km": float(row.waypoint_x_km),
                    "waypoint_y_km": float(row.waypoint_y_km),
                    "detection_made": bool(row.detection_made),
                    "target_platform_id": (
                        str(row.target_platform_id)
                        if pd.notna(row.target_platform_id)
                        else None
                    ),
                    "detection_sensor_name": (
                        str(row.detection_sensor_name)
                        if pd.notna(row.detection_sensor_name)
                        else None
                    ),
                    "detection_distance_km": (
                        float(row.detection_distance_km)
                        if pd.notna(row.detection_distance_km)
                        else None
                    ),
                }
            )
        detections: List[DetectionEvent] = [
            {
                "timestamp_sec": record["timestamp_sec"],
                "detecting_platform_id": str(platform_id),
                "target_platform_id": record["target_platform_id"],
                "sensor_name": record["detection_sensor_name"],
                "distance_m": record["detection_distance_km"] * 1000.0
                if record["detection_distance_km"] is not None
                else None,
            }
            for record in records
            if record["detection_made"] and record["target_platform_id"]
        ]
        platforms[str(platform_id)] = {
            "positions": records,
            "sensors": sensor_by_platform.get(str(platform_id), []),
            "detections": detections,
        }
    return platforms


def load_replication_animation_data(
    run_folder: Path, replication_id: int
) -> Tuple[Dict[str, PlatformAnimationData], SimulationTiming]:
    """Convenience entry point used by both the CLI and the Streamlit page."""
    positions, sensors, timing = load_animation_inputs(run_folder)
    platforms = build_platforms(positions, sensors, replication_id)
    return platforms, timing
