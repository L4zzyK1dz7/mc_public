"""Resolve sensor type references in config.yaml into full SensorConfig objects.

`config.yaml` only stores sensor type names (e.g. "generic"); the full sensor
definition (metadata + PoD table) lives in per-sensor CSV files written by the
UI under input_data/platforms/<Team>/<Platform>/sensors/<type>/*.csv. This
module reads those files back so validated SensorConfig instances - not bare
type strings - reach PlatformConfig.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.schemas.sensor import SensorConfig, SensorFactory

_INT_FIELDS = {"k", "n"}
_STR_FIELDS = {"display_name", "type"}


def _parse_sensor_csv(csv_path: Path) -> dict[str, Any]:
    """Parse a sensor CSV (metadata header comments + x_values/pod table) into a payload dict."""
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        lines = f.readlines()

    metadata: dict[str, str] = {}
    table_start = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            key, _, value = stripped.lstrip("#").partition(":")
            metadata[key.strip()] = value.strip()
        elif stripped:
            table_start = index
            break

    if table_start is None:
        raise ValueError(f"Sensor file {csv_path} has no PoD table rows.")

    x_values: list[float] = []
    pod: list[float] = []
    rows = csv.reader(lines[table_start:])
    next(rows, None)  # skip the "x_label,pod" table header row
    for row in rows:
        if not row:
            continue
        x_values.append(float(row[0]))
        pod.append(float(row[1]))

    payload: dict[str, Any] = {"x_values": x_values, "pod": pod}
    for key, value in metadata.items():
        if key in _INT_FIELDS:
            payload[key] = int(value)
        elif key in _STR_FIELDS:
            payload[key] = value
        else:
            payload[key] = float(
                value
            )  # sensor-type-specific numeric fields, e.g. FOV angles

    payload["sensor_type"] = payload.pop("type")
    return payload


def _load_sensor(csv_path: Path) -> SensorConfig:
    """Build a validated SensorConfig from a single sensor CSV file."""
    payload = _parse_sensor_csv(csv_path)
    sensor, errors = SensorFactory.create_sensor(**payload)
    if sensor is None:
        raise ValueError(
            f"Invalid sensor configuration in {csv_path}: {', '.join(errors)}"
        )
    return sensor


def resolve_platform_sensors(
    platform: dict[str, Any], input_data_path: Path
) -> list[SensorConfig]:
    """
    Resolve a platform's sensor type names into full SensorConfig objects.

    Args:
        platform: Raw platform dict from config.yaml, with sensors as a list of type names.
        input_data_path: The directory containing config.yaml (parent of platforms/).

    Returns:
        List of SensorConfig instances, one per sensor CSV file found for each referenced type.
    """
    sensor_types: list[str] = platform.get("sensors") or []
    if not sensor_types:
        return []

    platform_sensors_dir = (
        input_data_path
        / "platforms"
        / str(platform["team"])
        / platform["display_name"]
        / "sensors"
    )

    resolved: list[SensorConfig] = []
    for sensor_type in dict.fromkeys(sensor_types):  # de-duplicate, preserve order
        type_dir = platform_sensors_dir / sensor_type
        csv_files = sorted(type_dir.glob("*.csv"))
        if not csv_files:
            raise ValueError(
                f"No sensor files found for type '{sensor_type}' at {type_dir}"
            )
        resolved.extend(_load_sensor(csv_file) for csv_file in csv_files)

    return resolved
