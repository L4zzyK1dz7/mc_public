"""Sonobuoy receiver loader module.

Loads sonobuoy definitions and their PoD tables from CSV files under
input_data/sonobuoys/<display_name>.csv into validated SonobuoyConfig objects.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.schemas.sonobuoy import SonobuoyConfig


def load_sonobuoy_csv(csv_path: Path) -> dict[str, Any]:
    """Parse a sonobuoy CSV file (metadata comments header + distance_m,pod table).

    Args:
        csv_path: Path to the sonobuoy CSV file.

    Returns:
        Dictionary payload containing parsed table and metadata.
    """
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
        raise ValueError(f"Sonobuoy file {csv_path} has no PoD table rows.")

    distance_m: list[float] = []
    pod: list[float] = []
    rows = csv.reader(lines[table_start:])
    next(rows, None)  # Skip the header row (e.g. "distance_m,pod")
    for row in rows:
        if not row:
            continue
        distance_m.append(float(row[0]))
        pod.append(float(row[1]))

    payload: dict[str, Any] = {"distance_m": distance_m, "pod": pod}
    for key, value in metadata.items():
        if key in ("k", "n"):
            payload[key] = int(value)
        elif key in ("x_m", "y_m"):
            payload[key] = float(value)
        elif key == "evaluation_modes":
            payload[key] = [m.strip() for m in value.split(",") if m.strip()]
        else:
            payload[key] = value

    return payload


def resolve_sonobuoys(
    sonobuoys_raw: list[dict[str, Any]],
    input_data_path: Path,
) -> list[SonobuoyConfig]:
    """Resolve raw sonobuoy dicts by populating PoD tables from their CSV files.

    If a sonobuoy dict already contains distance_m and pod, it is validated directly.
    Otherwise, the table is loaded from input_data/sonobuoys/<display_name>.csv.

    Args:
        sonobuoys_raw: List of sonobuoy dictionaries from config.yaml.
        input_data_path: Directory containing config.yaml (parent of sonobuoys/).

    Returns:
        List of validated SonobuoyConfig instances.
    """
    resolved: list[SonobuoyConfig] = []
    for buoy_entry in sonobuoys_raw:
        if isinstance(buoy_entry, SonobuoyConfig):
            resolved.append(buoy_entry)
            continue

        buoy_dict = dict(buoy_entry)
        has_table = (
            "distance_m" in buoy_dict
            and "pod" in buoy_dict
            and bool(buoy_dict["distance_m"])
        )

        if not has_table:
            name = buoy_dict.get("display_name")
            if not name:
                raise ValueError("Sonobuoy configuration missing display_name.")
            csv_path = input_data_path / "sonobuoys" / f"{name}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Sonobuoy CSV file not found: {csv_path}")

            csv_data = load_sonobuoy_csv(csv_path)
            for k, v in csv_data.items():
                buoy_dict.setdefault(k, v)
            buoy_dict["distance_m"] = csv_data["distance_m"]
            buoy_dict["pod"] = csv_data["pod"]

        resolved.append(SonobuoyConfig(**buoy_dict))

    return resolved
