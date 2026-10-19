from __future__ import annotations

import logging
from pathlib import Path
import pandas as pd
import pytest

from src.schemas.platform import PlatformConfig
from src.schemas.movement import RandomWalkMovement
from src.schemas.simulation import ConfigData, SimulationConfig, World
from src.ui.services.animation_data import (
    REQUIRED_POSITION_COLUMNS,
    build_display_name_map,
    build_platforms,
    compute_replication_end_sec,
    load_positions,
)


@pytest.fixture
def sample_positions_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "raw_positions.csv"
    data = {
        "replication_id": [1, 1],
        "platform_id": ["Blue_1", "Blue_1"],
        "pos_x_km": [0.0, 1.0],
        "pos_y_km": [0.0, 1.0],
        "waypoint_x_km": [1.0, 2.0],
        "waypoint_y_km": [1.0, 2.0],
        "timestamp_minutes": [0.0, 1.0],
        "team": ["Blue", "Blue"],
        "target_platform_id": ["", ""],
        "detection_made": ["false", "false"],
        "detection_sensor_name": ["", ""],
        "detection_distance_km": ["", ""],
        "heading": [45.0, 405.0],  # 405 deg should normalise to 45 deg
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    return csv_path


def test_load_positions_happy_path(sample_positions_csv: Path):
    """Happy path: raw_positions.csv loads with normalised heading."""
    df = load_positions(sample_positions_csv)
    assert "heading" in df.columns
    assert df["heading"].iloc[0] == pytest.approx(45.0)
    assert df["heading"].iloc[1] == pytest.approx(45.0)  # 405 % 360 == 45
    assert df["timestamp_sec"].iloc[1] == 60.0


def test_load_positions_bad_path_missing_heading(tmp_path: Path):
    """Bad path: Missing heading raises ValueError."""
    csv_path = tmp_path / "raw_positions.csv"
    data = {
        col: [0]
        for col in REQUIRED_POSITION_COLUMNS
        if col != "heading"
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="missing required columns.*heading"):
        load_positions(csv_path)


def test_load_positions_extreme_path_negative_and_zero_heading(tmp_path: Path):
    """Extreme path: Negative headings are mapped to [0, 360)."""
    csv_path = tmp_path / "raw_positions.csv"
    cols = {col: ["0"] for col in REQUIRED_POSITION_COLUMNS}
    cols["heading"] = ["-90.0"]
    pd.DataFrame(cols).to_csv(csv_path, index=False)

    df = load_positions(csv_path)
    assert df["heading"].iloc[0] == pytest.approx(270.0)


def test_build_platforms_with_heading_and_display_name(sample_positions_csv: Path):
    """Happy path: build_platforms preserves heading and applies display_name."""
    df = load_positions(sample_positions_csv)
    name_map = {"Blue_1": "Custom Destroyer"}
    platforms = build_platforms(df, sensors=[], replication_id=1, name_map=name_map)

    assert "Blue_1" in platforms
    blue = platforms["Blue_1"]
    assert blue["display_name"] == "Custom Destroyer"
    assert len(blue["positions"]) == 2
    assert blue["positions"][0]["heading"] == pytest.approx(45.0)
    assert blue["positions"][1]["heading"] == pytest.approx(45.0)


def test_build_platforms_detection_uses_display_name(tmp_path: Path):
    """Verify that detection events use display_name for detecting and target platforms."""
    csv_path = tmp_path / "raw_positions_det.csv"
    data = {
        "replication_id": [1],
        "platform_id": ["Blue_1"],
        "pos_x_km": [0.0],
        "pos_y_km": [0.0],
        "waypoint_x_km": [1.0],
        "waypoint_y_km": [1.0],
        "timestamp_minutes": [0.5],
        "team": ["Blue"],
        "target_platform_id": ["Red_1"],
        "detection_made": ["true"],
        "detection_sensor_name": ["Radar 1"],
        "detection_distance_km": [5.0],
        "heading": [90.0],
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    df = load_positions(csv_path)
    name_map = {"Blue_1": "Observer Ship", "Red_1": "Target Ship"}
    platforms = build_platforms(df, sensors=[], replication_id=1, name_map=name_map)

    detections = platforms["Blue_1"]["detections"]
    assert len(detections) == 1
    assert detections[0]["detecting_platform_id"] == "Observer Ship"
    assert detections[0]["target_platform_id"] == "Target Ship"
    assert detections[0]["distance_m"] == pytest.approx(5000.0)


def test_compute_replication_end_sec():
    """Happy path & extreme path for computing replication end time."""
    from typing import cast
    from src.ui.plotting.platform_animation import PlatformAnimationData

    platforms = {
        "Blue_1": cast(
            PlatformAnimationData,
            {
                "display_name": "Blue_1",
                "positions": [
                    {"timestamp_sec": 0.0},
                    {"timestamp_sec": 125.5},
                ],
                "sensors": [],
                "detections": [],
            },
        ),
        "Red_1": cast(
            PlatformAnimationData,
            {
                "display_name": "Red_1",
                "positions": [
                    {"timestamp_sec": 0.0},
                    {"timestamp_sec": 90.0},
                ],
                "sensors": [],
                "detections": [],
            },
        ),
    }
    end_sec = compute_replication_end_sec(platforms)
    assert end_sec == pytest.approx(125.5)

    with pytest.raises(ValueError, match="empty platforms"):
        compute_replication_end_sec({})


def test_build_display_name_map_duplicate_and_blank(caplog):
    """Happy & extreme path: mapping display names, logging duplicate warnings."""
    p1 = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Hunter",
        team="Blue",
        speed_mps=10.0,
        neutralised_platform_behaviour="stop",
        movement_type=RandomWalkMovement(type="random_walk"),
    )
    p2 = PlatformConfig(
        platform_config_folder="blue_2",
        display_name="Hunter",  # duplicate display name
        team="Blue",
        speed_mps=10.0,
        neutralised_platform_behaviour="stop",
        movement_type=RandomWalkMovement(type="random_walk"),
    )
    p3 = PlatformConfig(
        platform_config_folder="red_1",
        display_name="   ",  # blank display name
        team="Red",
        speed_mps=10.0,
        neutralised_platform_behaviour="stop",
        movement_type=RandomWalkMovement(type="random_walk"),
    )

    cfg = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=100.0,
            timestep_sec=1.0,
            seeds_file=False,
        ),
        world=World(length=1000.0, height=1000.0),
        platforms=[p1, p2, p3],
    )

    with caplog.at_level(logging.WARNING):
        name_map = build_display_name_map(cfg)

    assert name_map["Blue_1"] == "Hunter"
    assert name_map["Blue_2"] == "Hunter"
    assert name_map["Red_1"] == "Red_1"  # falls back to platform id
    assert any("Duplicate platform display name" in rec.message for rec in caplog.records)
