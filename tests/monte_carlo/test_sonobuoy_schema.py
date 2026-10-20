"""Tests for sonobuoy schemas, boundary validation, and configuration loading."""

from __future__ import annotations

import logging
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.monte_carlo.configuration.load_configuration import load_config_from_yaml
from src.monte_carlo.configuration.sonobuoy_loader import (
    load_sonobuoy_csv,
    resolve_sonobuoys,
)
from src.schemas.movement import RandomWalkMovement
from src.schemas.platform import PlatformConfig
from src.schemas.simulation import ConfigData, SimulationConfig, World
from src.schemas.sonobuoy import SonobuoyConfig, SonobuoyFieldConfig
from src.ui.services.create_yaml import create_sonobuoy_file

pytestmark = pytest.mark.unit


def test_sonobuoy_config_valid():
    """Verify a valid SonobuoyConfig initializes cleanly."""
    buoy = SonobuoyConfig(
        display_name="Buoy Alpha",
        x_m=5000.0,
        y_m=10000.0,
        k=2,
        n=4,
        distance_m=[0.0, 500.0, 1000.0],
        pod=[1.0, 0.7, 0.0],
        evaluation_modes=["single", "multi", "single_cycle"],
    )
    assert buoy.display_name == "Buoy Alpha"
    assert buoy.k == 2
    assert buoy.n == 4
    assert buoy.evaluation_modes == ["single", "multi", "single_cycle"]


def test_sonobuoy_config_invalid_k_greater_than_n():
    """Verify validation fails when k > n."""
    with pytest.raises(ValidationError, match="must be less than or equal to n"):
        SonobuoyConfig(
            display_name="Invalid K",
            x_m=0.0,
            y_m=0.0,
            k=5,
            n=3,
            distance_m=[0.0, 100.0],
            pod=[1.0, 0.5],
        )


def test_sonobuoy_config_invalid_distance_not_strictly_increasing():
    """Verify distance_m must be strictly increasing for np.interp."""
    with pytest.raises(ValidationError, match="strictly increasing"):
        SonobuoyConfig(
            display_name="Non increasing",
            x_m=0.0,
            y_m=0.0,
            k=1,
            n=1,
            distance_m=[100.0, 100.0],
            pod=[1.0, 0.5],
        )


def test_sonobuoy_config_invalid_pod_out_of_bounds():
    """Verify pod must be between 0.0 and 1.0."""
    with pytest.raises(ValidationError, match="Probability of detection must be between 0.0 and 1.0"):
        SonobuoyConfig(
            display_name="Bad PoD",
            x_m=0.0,
            y_m=0.0,
            k=1,
            n=1,
            distance_m=[0.0, 100.0],
            pod=[1.0, 1.2],
        )


def test_config_data_sonobuoy_world_boundary_validation():
    """Verify sonobuoys must be placed within world boundaries."""
    world = World(origin_x=0.0, origin_y=0.0, length=50000.0, height=50000.0)
    sim = SimulationConfig(replications=1, time_limit_sec=100.0, timestep_sec=1.0, seeds_file=True)
    platform = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
    )

    # Valid buoy at boundary corner
    valid_buoy = SonobuoyConfig(
        display_name="Corner Buoy",
        x_m=50000.0,
        y_m=50000.0,
        k=1,
        n=1,
        distance_m=[0.0, 100.0],
        pod=[0.8, 0.0],
    )
    cfg = ConfigData(
        simulation=sim,
        world=world,
        platforms=[platform],
        sonobuoys=[valid_buoy],
    )
    assert len(cfg.sonobuoys) == 1

    # Out of bounds buoy
    invalid_buoy = SonobuoyConfig(
        display_name="OOB Buoy",
        x_m=50001.0,
        y_m=20000.0,
        k=1,
        n=1,
        distance_m=[0.0, 100.0],
        pod=[0.8, 0.0],
    )
    with pytest.raises(ValidationError, match="is outside world bounds"):
        ConfigData(
            simulation=sim,
            world=world,
            platforms=[platform],
            sonobuoys=[invalid_buoy],
        )


def test_config_data_duplicate_sonobuoy_name():
    """Verify duplicate sonobuoy display names are rejected."""
    world = World(origin_x=0.0, origin_y=0.0, length=50000.0, height=50000.0)
    sim = SimulationConfig(replications=1, time_limit_sec=100.0, timestep_sec=1.0, seeds_file=True)
    platform = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
    )

    b1 = SonobuoyConfig(
        display_name="Buoy Alpha",
        x_m=1000.0,
        y_m=1000.0,
        k=1,
        n=1,
        distance_m=[0.0, 100.0],
        pod=[0.8, 0.0],
    )
    b2 = SonobuoyConfig(
        display_name="Buoy Alpha",
        x_m=2000.0,
        y_m=2000.0,
        k=1,
        n=1,
        distance_m=[0.0, 100.0],
        pod=[0.8, 0.0],
    )
    with pytest.raises(ValidationError, match="Duplicate sonobuoy display name"):
        ConfigData(
            simulation=sim,
            world=world,
            platforms=[platform],
            sonobuoys=[b1, b2],
        )


def test_config_data_fusion_requirement_warning(caplog):
    """Verify a warning is logged when data_fusion_requirement exceeds participating buoys."""
    world = World(origin_x=0.0, origin_y=0.0, length=50000.0, height=50000.0)
    sim = SimulationConfig(replications=1, time_limit_sec=100.0, timestep_sec=1.0, seeds_file=True)
    platform = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
    )
    buoy = SonobuoyConfig(
        display_name="Buoy 1",
        x_m=1000.0,
        y_m=1000.0,
        k=1,
        n=1,
        distance_m=[0.0, 100.0],
        pod=[0.8, 0.0],
        evaluation_modes=["multi"],
    )

    with caplog.at_level(logging.WARNING):
        ConfigData(
            simulation=sim,
            world=world,
            platforms=[platform],
            sonobuoys=[buoy],
            sonobuoy_field=SonobuoyFieldConfig(data_fusion_requirement=5),
        )
    assert "data_fusion_requirement (5) is greater than the number of participating buoys (1)" in caplog.text


def test_sonobuoy_csv_round_trip(tmp_path: Path):
    """Verify sonobuoy CSV write and load round-trip."""
    buoy = SonobuoyConfig(
        display_name="Echo_1",
        x_m=12000.0,
        y_m=34000.0,
        k=2,
        n=3,
        distance_m=[0.0, 250.0, 750.0],
        pod=[1.0, 0.75, 0.1],
        evaluation_modes=["single", "multi"],
    )

    sonobuoys_dir = tmp_path / "sonobuoys"
    success = create_sonobuoy_file(buoy, sonobuoys_dir)
    assert success is True

    csv_path = sonobuoys_dir / "Echo_1.csv"
    assert csv_path.exists()

    csv_data = load_sonobuoy_csv(csv_path)
    assert csv_data["display_name"] == "Echo_1"
    assert csv_data["distance_m"] == [0.0, 250.0, 750.0]
    assert csv_data["pod"] == [1.0, 0.75, 0.1]
    assert csv_data["evaluation_modes"] == ["single", "multi"]

    # Test resolve_sonobuoys
    raw_buoys = [{"display_name": "Echo_1", "x_m": 12000.0, "y_m": 34000.0, "k": 2, "n": 3}]
    resolved = resolve_sonobuoys(raw_buoys, tmp_path)
    assert len(resolved) == 1
    assert resolved[0].display_name == "Echo_1"
    assert resolved[0].distance_m == [0.0, 250.0, 750.0]


def test_load_config_from_yaml_with_sonobuoys(tmp_path: Path):
    """Verify loading config.yaml with sonobuoys and sonobuoy_field."""
    # Write a test sonobuoy CSV
    sonobuoys_dir = tmp_path / "sonobuoys"
    sonobuoys_dir.mkdir(parents=True)
    csv_file = sonobuoys_dir / "Buoy_1.csv"
    csv_file.write_text(
        "# display_name: Buoy_1\n"
        "# x_m: 5000.0\n"
        "# y_m: 5000.0\n"
        "# k: 1\n"
        "# n: 2\n"
        "# evaluation_modes: single,multi,single_cycle\n\n"
        "distance_m,pod\n"
        "0.0,1.0\n"
        "500.0,0.5\n",
        encoding="utf-8",
    )

    # Write config.yaml
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        "simulation:\n"
        "  replications: 1\n"
        "  time_limit_sec: 100.0\n"
        "  timestep_sec: 1.0\n"
        "  seeds_file: true\n"
        "world:\n"
        "  origin_x: 0.0\n"
        "  origin_y: 0.0\n"
        "  length: 10000.0\n"
        "  height: 10000.0\n"
        "platforms: []\n"
        "sonobuoys:\n"
        "  - display_name: Buoy_1\n"
        "    x_m: 5000.0\n"
        "    y_m: 5000.0\n"
        "    k: 1\n"
        "    n: 2\n"
        "    evaluation_modes: ['single', 'multi', 'single_cycle']\n"
        "sonobuoy_field:\n"
        "  data_fusion_requirement: 1\n",
        encoding="utf-8",
    )

    config = load_config_from_yaml(yaml_file)
    assert len(config.sonobuoys) == 1
    assert config.sonobuoys[0].display_name == "Buoy_1"
    assert config.sonobuoys[0].distance_m == [0.0, 500.0]
    assert config.sonobuoy_field is not None
    assert config.sonobuoy_field.data_fusion_requirement == 1
