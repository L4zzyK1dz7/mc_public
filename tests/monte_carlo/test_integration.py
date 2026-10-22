"""
Suite 6: Monte Carlo Orchestration & Integration (INT-01 to INT-06)
End-to-end integration tests for replication loops, seed generation, and scenario orchestration.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest
import yaml

from src.monte_carlo.monte_carlo import (
    _execute_single_replication,
    _execute_monte_carlo,
    run_simulation,
)
from src.monte_carlo.output.aggregate_results import aggregate_and_output_results
from src.monte_carlo.output.outcome_detection_manager import OutcomeDetectionManager
from src.monte_carlo.output.outcome_position_manager import OutcomePositionManager
from src.monte_carlo.configuration.load_configuration import load_seeds
from src.schemas.movement import (
    IntruderSearchMovement,
    RandomWalkMovement,
    UserDefinedWaypointsMovement,
    Waypoint,
)
from src.schemas.platform import PlatformConfig, Team
from src.schemas.sensor import GenericSensorConfig, SpecificSensorConfig
from src.schemas.simulation import ConfigData, SimulationConfig, World
from src.schemas.sonobuoy import SonobuoyConfig, SonobuoyFieldConfig


def make_test_config_data(
    replications: int = 1,
    time_limit_sec: float = 60.0,
    timestep_sec: float = 1.0,
    seeds_file: bool = False,
    detection_end_condition: str = "initial_detection",
) -> ConfigData:
    sensor = GenericSensorConfig(
        display_name="Test Sensor",
        interval_time_sec=1.0,
        x_values=[0.0, 1000.0],
        pod=[1.0, 1.0],
        type="generic",
        k=1,
        n=1,
        fov_start_deg=0.0,
        fov_end_deg=360.0,
    )
    blue_platform = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        neutralised_platform_behaviour="stop",
        sensors=[sensor],
    )
    red_platform = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=5.0,
        movement_type=RandomWalkMovement(),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    return ConfigData(
        simulation=SimulationConfig(
            replications=replications,
            time_limit_sec=time_limit_sec,
            timestep_sec=timestep_sec,
            seeds_file=seeds_file,
            detection_end_condition=detection_end_condition,  # type: ignore[arg-type]
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=10000.0, height=10000.0),
        platforms=[blue_platform, red_platform],
    )


# ==============================================================================
# INT-01: End-to-end deterministic repeatability under identical seed
# ==============================================================================
def test_int_01_deterministic_repeatability():
    """Verify replication executed twice under identical seed produces identical results."""
    config_data = make_test_config_data()
    seed = 42

    outcome_manager_1 = OutcomePositionManager(0)
    detection_manager_1 = OutcomeDetectionManager(0)
    res_1 = _execute_single_replication(
        config_data, outcome_manager_1, detection_manager_1, seed=seed
    )

    outcome_manager_2 = OutcomePositionManager(1)
    detection_manager_2 = OutcomeDetectionManager(1)
    res_2 = _execute_single_replication(
        config_data, outcome_manager_2, detection_manager_2, seed=seed
    )

    assert res_1["result"] == res_2["result"]
    assert res_1["end_condition"] == res_2["end_condition"]

    events_1 = [e if isinstance(e, dict) else e.model_dump() for e in res_1["platform_position_events"]]
    events_2 = [e if isinstance(e, dict) else e.model_dump() for e in res_2["platform_position_events"]]
    assert len(events_1) == len(events_2)
    for e1, e2 in zip(events_1, events_2):
        e1.pop("replication_id", None)
        e2.pop("replication_id", None)
        assert e1 == e2

    det_1 = [d if isinstance(d, dict) else d.model_dump() for d in res_1["detection_outcomes"]]
    det_2 = [d if isinstance(d, dict) else d.model_dump() for d in res_2["detection_outcomes"]]
    assert len(det_1) == len(det_2)
    for d1, d2 in zip(det_1, det_2):
        d1.pop("replication_id", None)
        d2.pop("replication_id", None)
        assert d1 == d2


# ==============================================================================
# INT-02: Execution order and phase progression within replication loop
# ==============================================================================
def test_int_02_execution_order_phase_progression():
    """Verify detection evaluates current platform positions after kinematics advance."""
    config_data = make_test_config_data(time_limit_sec=2.0)
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)

    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=123
    )

    # Initial positions are recorded first
    initial_events = [
        e for e in outcome_manager.events if e["event_type"] == "initial_position"
    ]
    assert len(initial_events) == 2

    # If detection occurred, snapshot aligns with detection time
    if res["result"] == "detected":
        det_events = [
            e for e in outcome_manager.events if e["event_type"] == "detection"
        ]
        assert len(det_events) == 2  # Both platforms captured at detection moment


# ==============================================================================
# INT-03: Seed splitting and pseudorandom independence across 20 replications
# ==============================================================================
def test_int_03_seed_splitting_independence():
    """Verify master RNG spawns 20 unique and independent child sub-seeds."""
    master_rng = np.random.default_rng(98765)
    child_rngs = master_rng.spawn(20)
    seeds = [int(rng.bit_generator.seed_seq.generate_state(1)[0]) for rng in child_rngs]

    assert len(seeds) == 20
    assert len(set(seeds)) == 20  # Completely unique sub-seeds
    # Ensure values are within standard 32-bit unsigned range
    for s in seeds:
        assert 0 <= s <= 2**32 - 1


# ==============================================================================
# INT-04: Scenario initialisation from external seeds.txt
# ==============================================================================
def test_int_04_scenario_initialisation_from_seeds_file(tmp_path: Path):
    """Verify loading and sequentially injecting seeds from external seeds.txt."""
    seeds_file = tmp_path / "seeds.txt"
    prescribed_seeds = [101, 202, 303, 404, 505]
    with open(seeds_file, "w", encoding="utf-8") as f:
        for s in prescribed_seeds:
            f.write(f"{s}\n")

    loaded = load_seeds(seeds_file, replications=5)["seeds"]
    assert loaded == prescribed_seeds

    config_data = make_test_config_data(replications=5, seeds_file=True)
    results = _execute_monte_carlo(5, config_data=config_data, seeds=loaded)
    assert len(results) == 5


# ==============================================================================
# INT-05: Data integrity and aggregation stability
# ==============================================================================
def test_int_05_aggregation_stability_50_replications(tmp_path: Path):
    """Verify consolidating 50 replication outputs into summary statistics and positions."""
    config_data = make_test_config_data(replications=50, time_limit_sec=5.0)
    master_rng = np.random.default_rng(42)
    seeds = [int(rng.bit_generator.seed_seq.generate_state(1)[0]) for rng in master_rng.spawn(50)]

    results = _execute_monte_carlo(50, config_data=config_data, seeds=seeds)
    assert len(results) == 50

    output_dir = tmp_path / "aggregated_run"
    aggregate_and_output_results(results, output_dir=output_dir)

    assert (output_dir / "summary_stats.csv").exists()
    assert (output_dir / "raw_positions.csv").exists()
    assert (output_dir / "summary_stats.csv").stat().st_size > 0
    assert (output_dir / "raw_positions.csv").stat().st_size > 0


# ==============================================================================
# INT-06: System-level scenario execution baseline (run_simulation)
# ==============================================================================
def test_int_06_system_level_simulation_baseline(tmp_path: Path):
    """Verify run_simulation executes from config file to completion with exit code 0."""
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()

    config_dict = {
        "simulation": {
            "replications": 2,
            "time_limit_sec": 10.0,
            "timestep_sec": 1.0,
            "seeds_file": False,
            "detection_end_condition": "initial_detection",
        },
        "world": {
            "origin_x": 0.0,
            "origin_y": 0.0,
            "length": 1000.0,
            "height": 1000.0,
        },
        "platforms": [
            {
                "platform_config_folder": "blue_patroller",
                "display_name": "Blue Patroller",
                "team": "Blue",
                "speed_mps": 10.0,
                "movement_type": {"type": "random_walk"},
                "neutralised_platform_behaviour": "stop",
                "sensors": [],
            },
            {
                "platform_config_folder": "red_intruder",
                "display_name": "Red Intruder",
                "team": "Red",
                "speed_mps": 5.0,
                "movement_type": {
                    "type": "intruder_search",
                    "start_distance_m": 0.0,
                    "end_condition": "cross_world",
                },
                "neutralised_platform_behaviour": "continue",
                "sensors": [],
            },
        ],
    }

    config_path = scenario_dir / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    output_dir = tmp_path / "run_outcomes"
    return_code = run_simulation(config_path, output_dir=output_dir)

    assert return_code == 0
    assert (output_dir / "seeds.txt").exists()
    assert (output_dir / "summary_stats.csv").exists()
    assert (output_dir / "raw_positions.csv").exists()


# ==============================================================================
# INT-07: Multistatic sonobuoy scenario end-to-end simulation
# ==============================================================================
def test_int_07_multistatic_sonobuoy_simulation(tmp_path: Path):
    """Verify run_simulation with 1 Blue active pinger, 3 sonobuoys, and 1 Red platform."""
    scenario_dir = tmp_path / "scenario_sonobuoy"
    scenario_dir.mkdir()

    sonar_dir = (
        scenario_dir
        / "platforms"
        / "Blue"
        / "Blue Pinger"
        / "sensors"
        / "sonar"
    )
    sonar_dir.mkdir(parents=True)

    sonar_csv = sonar_dir / "sonar.csv"
    with open(sonar_csv, "w", encoding="utf-8") as f:
        f.write("# display_name: Active Sonar\n")
        f.write("# type: generic\n")
        f.write("# interval_time_sec: 1.0\n")
        f.write("# active_source: True\n")
        f.write("# source_receiver_collocated: False\n")
        f.write("# fov_start_deg: 0.0\n")
        f.write("# fov_end_deg: 360.0\n")
        f.write("# k: 1\n")
        f.write("# n: 1\n")
        f.write("distance_m,pod\n")
        f.write("0.0,1.0\n")
        f.write("1000.0,1.0\n")

    sonobuoys_dir = scenario_dir / "sonobuoys"
    sonobuoys_dir.mkdir()

    for idx, (bx, by) in enumerate([(500.0, 500.0), (510.0, 500.0), (520.0, 500.0)], start=1):
        buoy_csv = sonobuoys_dir / f"Buoy {idx}.csv"
        with open(buoy_csv, "w", encoding="utf-8") as f:
            f.write(f"# display_name: Buoy {idx}\n")
            f.write(f"# x_m: {bx}\n")
            f.write(f"# y_m: {by}\n")
            f.write("# k: 1\n")
            f.write("# n: 1\n")
            f.write("# evaluation_modes: single,multi,single_cycle\n")
            f.write("distance_m,pod\n")
            f.write("0.0,1.0\n")
            f.write("10000.0,1.0\n")

    config_dict = {
        "simulation": {
            "replications": 2,
            "time_limit_sec": 10.0,
            "timestep_sec": 1.0,
            "seeds_file": False,
            "detection_end_condition": "initial_detection",
        },
        "world": {
            "origin_x": 0.0,
            "origin_y": 0.0,
            "length": 1000.0,
            "height": 1000.0,
        },
        "platforms": [
            {
                "platform_config_folder": "blue_pinger",
                "display_name": "Blue Pinger",
                "team": "Blue",
                "speed_mps": 0.0,
                "movement_type": {"type": "random_walk"},
                "neutralised_platform_behaviour": "stop",
                "sensors": ["sonar"],
            },
            {
                "platform_config_folder": "red_target",
                "display_name": "Red Target",
                "team": "Red",
                "speed_mps": 5.0,
                "movement_type": {
                    "type": "intruder_search",
                    "start_distance_m": 0.0,
                    "end_condition": "cross_world",
                },
                "neutralised_platform_behaviour": "continue",
                "sensors": [],
            },
        ],
        "sonobuoys": [
            {
                "display_name": "Buoy 1",
                "x_m": 500.0,
                "y_m": 500.0,
                "k": 1,
                "n": 1,
                "evaluation_modes": ["single", "multi", "single_cycle"],
            },
            {
                "display_name": "Buoy 2",
                "x_m": 510.0,
                "y_m": 500.0,
                "k": 1,
                "n": 1,
                "evaluation_modes": ["single", "multi", "single_cycle"],
            },
            {
                "display_name": "Buoy 3",
                "x_m": 520.0,
                "y_m": 500.0,
                "k": 1,
                "n": 1,
                "evaluation_modes": ["single", "multi", "single_cycle"],
            },
        ],
        "sonobuoy_field": {
            "data_fusion_requirement": 2,
        },
    }

    config_path = scenario_dir / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f)

    output_dir = tmp_path / "sonobuoy_outcomes"
    return_code = run_simulation(config_path, output_dir=output_dir)

    assert return_code == 0
    assert (output_dir / "seeds.txt").exists()
    assert (output_dir / "summary_stats.csv").exists()
    assert (output_dir / "raw_positions.csv").exists()
    assert (output_dir / "sonobuoy_detections.csv").exists()

    # Verify sonobuoy_detections.csv contents
    import pandas as pd
    det_df = pd.read_csv(output_dir / "sonobuoy_detections.csv")
    assert not det_df.empty
    assert set(det_df.columns) == {
        "replication_id",
        "timestamp_minutes",
        "mode",
        "detecting_id",
        "target_platform_id",
    }
    # Highest priority is single_cycle
    assert "single_cycle" in det_df["mode"].values

    # Check summary_stats.csv records single-cycle end condition and sonobuoy_field detector
    summary_text = (output_dir / "summary_stats.csv").read_text(encoding="utf-8")
    assert "sonobuoy_single_cycle_detection" in summary_text
    assert "sonobuoy_field" in summary_text


def test_execute_monte_carlo_progress_callback():
    """Verify progress_callback is called N times with (1..N, N)."""
    cfg_data = make_test_config_data(replications=3, time_limit_sec=5.0)
    calls: list[tuple[int, int]] = []

    def mock_cb(completed: int, total: int) -> None:
        calls.append((completed, total))

    results = _execute_monte_carlo(
        number_of_replications=3,
        config_data=cfg_data,
        seeds=[1, 2, 3],
        progress_callback=mock_cb,
    )

    assert len(results) == 3
    assert calls == [(1, 3), (2, 3), (3, 3)]


def test_execute_monte_carlo_none_progress_callback():
    """Verify progress_callback=None still works cleanly."""
    cfg_data = make_test_config_data(replications=2, time_limit_sec=5.0)
    results = _execute_monte_carlo(
        number_of_replications=2,
        config_data=cfg_data,
        seeds=[1, 2],
        progress_callback=None,
    )
    assert len(results) == 2


def test_run_simulation_forwards_progress_callback(tmp_path: Path):
    """Verify run_simulation forwards progress_callback to replication loop."""
    scenario_dir = tmp_path / "scenario_cb"
    scenario_dir.mkdir(parents=True, exist_ok=True)
    cfg_data = make_test_config_data(replications=2, time_limit_sec=5.0)

    cfg_dict = cfg_data.model_dump(mode="json")
    for platform in cfg_dict["platforms"]:
        platform["sensors"] = []

    config_path = scenario_dir / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg_dict, f)

    output_dir = tmp_path / "cb_outcomes"
    calls: list[tuple[int, int]] = []

    def mock_cb(completed: int, total: int) -> None:
        calls.append((completed, total))

    ret = run_simulation(config_path, output_dir=output_dir, progress_callback=mock_cb)
    assert ret == 0
    assert calls == [(1, 2), (2, 2)]


# ==============================================================================
# INT-07: Deterministic trail crossing detection with specific sensor
# ==============================================================================
def test_int_07_specific_sensor_trail_crossing_integration():
    """Verify deterministic crossing scenario ends with initial_detection."""
    sensor = SpecificSensorConfig(
        display_name="SpecificSensor",
        interval_time_sec=10.0,
        x_values=[0.0, 1.0],  # 0 to 1 hour
        pod=[1.0, 1.0],
        k=1,
        n=1,
    )
    blue_platform = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=50.0, y=0.0), Waypoint(x=50.0, y=100.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[sensor],
    )
    red_platform = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=0.0, y=50.0), Waypoint(x=100.0, y=50.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=20.0,
            timestep_sec=10.0,
            seeds_file=False,
            detection_end_condition="initial_detection",
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=1000.0, height=1000.0),
        platforms=[blue_platform, red_platform],
    )
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)
    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=42
    )

    assert res["end_condition"] == "detection"
    assert res["result"] == "detected"


# ==============================================================================
# INT-08: Expired trail skips detection (same geometry, table ends earlier)
# ==============================================================================
def test_int_08_specific_sensor_expired_trail_no_detection():
    """Verify same geometry does not detect when red trail segment is older than table."""
    # Table ends at 0.001 hours = 3.6 seconds, but crossing happens at t=10s (age = 10s = 0.00277h)
    sensor = SpecificSensorConfig(
        display_name="SpecificSensor",
        interval_time_sec=10.0,
        x_values=[0.0, 0.001],
        pod=[1.0, 1.0],
        k=1,
        n=1,
    )
    blue_platform = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=50.0, y=0.0), Waypoint(x=50.0, y=100.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[sensor],
    )
    red_platform = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=0.0, y=50.0), Waypoint(x=100.0, y=50.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=20.0,
            timestep_sec=10.0,
            seeds_file=False,
            detection_end_condition="initial_detection",
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=1000.0, height=1000.0),
        platforms=[blue_platform, red_platform],
    )
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)
    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=42
    )

    assert res["end_condition"] == "time_limit"
    assert res["result"] == "not_detected"


# ==============================================================================
# INT-09: Team Detection - Stop Behaviour Freezes Detected Platform
# ==============================================================================
def test_int_09_team_detection_stop_freezes_detected_platform():
    """Verify detected platform with behaviour='stop' halts while simulation continues."""
    sensor = GenericSensorConfig(
        display_name="Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 500.0],
        pod=[1.0, 1.0],
        type="generic",
        k=1,
        n=1,
        fov_start_deg=0.0,
        fov_end_deg=360.0,
    )
    blue = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=0.0, y=0.0), Waypoint(x=100.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[sensor],
    )
    red_1 = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=50.0, y=0.0), Waypoint(x=200.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    red_2 = PlatformConfig(
        platform_config_folder="red_2",
        display_name="Red 2",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=5000.0, y=5000.0), Waypoint(x=6000.0, y=5000.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=5.0,
            timestep_sec=1.0,
            seeds_file=False,
            detection_end_condition="team_detection",
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=10000.0, height=10000.0),
        platforms=[blue, red_1, red_2],
    )
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)
    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=42
    )

    assert res["end_condition"] == "time_limit"

    time_limit_events = [
        e for e in res["platform_position_events"]
        if (e.get("event_type") if isinstance(e, dict) else getattr(e, "event_type", None)) == "time_limit"
    ]
    red_1_final = next(
        e for e in time_limit_events
        if (e.get("platform_id") if isinstance(e, dict) else getattr(e, "platform_id", None)) == "Red_1"
    )
    red_2_final = next(
        e for e in time_limit_events
        if (e.get("platform_id") if isinstance(e, dict) else getattr(e, "platform_id", None)) == "Red_2"
    )
    red_1_x = red_1_final.get("pos_x") if isinstance(red_1_final, dict) else red_1_final.pos_x
    red_2_x = red_2_final.get("pos_x") if isinstance(red_2_final, dict) else red_2_final.pos_x
    # Red 1 moved in tick 1 to 60.0 then froze upon neutralisation
    assert red_1_x == pytest.approx(60.0)
    # Red 2 moved all 5 ticks (5000 + 50 = 5050.0)
    assert red_2_x == pytest.approx(5050.0)

    # Exactly one detection outcome for Red 1
    red_1_det = [
        row for row in res["detection_outcomes"]
        if row["target_platform_id"] == "Red_1" and row["detection_outcome"] is True
    ]
    assert len(red_1_det) == 1
    assert red_1_det[0]["detection_timestamp_sec"] == 1.0


# ==============================================================================
# INT-10: Team Detection - Continue Behaviour Keeps Moving, Single Detection
# ==============================================================================
def test_int_10_team_detection_continue_keeps_moving_single_detection():
    """Verify detected platform with behaviour='continue' keeps moving and is not re-detected."""
    sensor = GenericSensorConfig(
        display_name="Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 500.0],
        pod=[1.0, 1.0],
        type="generic",
        k=1,
        n=1,
        fov_start_deg=0.0,
        fov_end_deg=360.0,
    )
    blue = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=0.0, y=0.0), Waypoint(x=100.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[sensor],
    )
    red_1 = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=50.0, y=0.0), Waypoint(x=200.0, y=0.0)]
        ),
        neutralised_platform_behaviour="continue",
        sensors=[],
    )
    red_2 = PlatformConfig(
        platform_config_folder="red_2",
        display_name="Red 2",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=5000.0, y=5000.0), Waypoint(x=6000.0, y=5000.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=5.0,
            timestep_sec=1.0,
            seeds_file=False,
            detection_end_condition="team_detection",
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=10000.0, height=10000.0),
        platforms=[blue, red_1, red_2],
    )
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)
    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=42
    )

    assert res["end_condition"] == "time_limit"

    time_limit_events = [
        e for e in res["platform_position_events"]
        if (e.get("event_type") if isinstance(e, dict) else getattr(e, "event_type", None)) == "time_limit"
    ]
    red_1_final = next(
        e for e in time_limit_events
        if (e.get("platform_id") if isinstance(e, dict) else getattr(e, "platform_id", None)) == "Red_1"
    )
    red_1_x = red_1_final.get("pos_x") if isinstance(red_1_final, dict) else red_1_final.pos_x
    # Red 1 kept moving all 5 ticks (50 + 50 = 100.0)
    assert red_1_x == pytest.approx(100.0)

    # Exactly one detection outcome for Red 1
    red_1_det = [
        row for row in res["detection_outcomes"]
        if row["target_platform_id"] == "Red_1" and row["detection_outcome"] is True
    ]
    assert len(red_1_det) == 1
    assert red_1_det[0]["detection_timestamp_sec"] == 1.0


# ==============================================================================
# INT-11: Initial Detection - Neutralisation Flag Never Set
# ==============================================================================
def test_int_11_initial_detection_never_sets_neutralised():
    """Verify initial_detection ends on first detection without neutralising platforms."""
    sensor = GenericSensorConfig(
        display_name="Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 500.0],
        pod=[1.0, 1.0],
        type="generic",
        k=1,
        n=1,
        fov_start_deg=0.0,
        fov_end_deg=360.0,
    )
    blue = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=0.0, y=0.0), Waypoint(x=100.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[sensor],
    )
    red = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=50.0, y=0.0), Waypoint(x=200.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=10.0,
            timestep_sec=1.0,
            seeds_file=False,
            detection_end_condition="initial_detection",
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=10000.0, height=10000.0),
        platforms=[blue, red],
    )
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)
    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=42
    )

    assert res["end_condition"] == "detection"
    assert res["result"] == "detected"


# ==============================================================================
# INT-12: Full Team Detection Completes When All Targets Detected
# ==============================================================================
def test_int_12_team_detection_completes_when_all_targets_detected():
    """Verify red_team_detection terminates when every platform on Red team is detected."""
    sensor = GenericSensorConfig(
        display_name="Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 500.0],
        pod=[1.0, 1.0],
        type="generic",
        k=1,
        n=1,
        fov_start_deg=0.0,
        fov_end_deg=360.0,
    )
    blue = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=0.0, y=0.0), Waypoint(x=2000.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[sensor],
    )
    red_1 = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=50.0, y=0.0), Waypoint(x=200.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    red_2 = PlatformConfig(
        platform_config_folder="red_2",
        display_name="Red 2",
        team=Team.RED,
        speed_mps=0.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=100.0, y=0.0), Waypoint(x=100.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=10.0,
            timestep_sec=1.0,
            seeds_file=False,
            detection_end_condition="team_detection",
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=10000.0, height=10000.0),
        platforms=[blue, red_1, red_2],
    )
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)
    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=42
    )

    assert res["end_condition"] == "red_team_detection"
    assert res["result"] == "detected"


# ==============================================================================
# INT-13: Neutralised Platform's Own Sensors Still Detect
# ==============================================================================
def test_int_13_neutralised_platform_sensors_still_detect():
    """Verify neutralised platform can still detect opposing targets with its own sensors."""
    blue_sensor = GenericSensorConfig(
        display_name="Blue Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 500.0],
        pod=[1.0, 1.0],
        type="generic",
        k=1,
        n=1,
        fov_start_deg=0.0,
        fov_end_deg=360.0,
    )
    red_sensor = GenericSensorConfig(
        display_name="Red Sonar",
        interval_time_sec=1.0,
        x_values=[0.0, 500.0],
        pod=[1.0, 1.0],
        type="generic",
        k=1,
        n=1,
        fov_start_deg=0.0,
        fov_end_deg=360.0,
    )
    blue_1 = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=50.0, y=0.0), Waypoint(x=200.0, y=0.0)]
        ),
        neutralised_platform_behaviour="continue",
        sensors=[blue_sensor],
    )
    blue_2 = PlatformConfig(
        platform_config_folder="blue_2",
        display_name="Blue 2",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=5000.0, y=5000.0), Waypoint(x=6000.0, y=5000.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    red = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=0.0, y=0.0), Waypoint(x=100.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[red_sensor],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=5.0,
            timestep_sec=1.0,
            seeds_file=False,
            detection_end_condition="team_detection",
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=10000.0, height=10000.0),
        platforms=[blue_1, blue_2, red],
    )
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)
    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=42
    )

    blue_1_detections = [
        row for row in res["detection_outcomes"]
        if row["detecting_platform_id"] == "Blue_1" and row["detection_outcome"] is True
    ]
    assert len(blue_1_detections) >= 1


# ==============================================================================
# INT-14: Sonobuoy Detected Platform Neutralised and Excluded
# ==============================================================================
def test_int_14_sonobuoy_detected_platform_neutralised_and_excluded():
    """Verify red platform detected by sonobuoy is neutralised and excluded from further buoy hits."""
    pinger = GenericSensorConfig(
        display_name="Pinger",
        interval_time_sec=1.0,
        x_values=[0.0, 1000.0],
        pod=[1.0, 1.0],
        type="generic",
        k=1,
        n=1,
        active_source=True,
        can_detect=False,
    )
    blue = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=0.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=0.0, y=0.0), Waypoint(x=0.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[pinger],
    )
    red_1 = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=50.0, y=0.0), Waypoint(x=200.0, y=0.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    red_2 = PlatformConfig(
        platform_config_folder="red_2",
        display_name="Red 2",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=5000.0, y=5000.0), Waypoint(x=6000.0, y=5000.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    buoy = SonobuoyConfig(
        display_name="Buoy 1",
        x_m=50.0,
        y_m=0.0,
        k=1,
        n=1,
        distance_m=[0.0, 1000.0],
        pod=[1.0, 1.0],
        evaluation_modes=["single_cycle"],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=5.0,
            timestep_sec=1.0,
            seeds_file=False,
            detection_end_condition="team_detection",
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=10000.0, height=10000.0),
        platforms=[blue, red_1, red_2],
        sonobuoys=[buoy],
        sonobuoy_field=SonobuoyFieldConfig(data_fusion_requirement=1),
    )
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)
    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=42
    )

    assert res["end_condition"] == "time_limit"

    time_limit_events = [
        e for e in res["platform_position_events"]
        if (e.get("event_type") if isinstance(e, dict) else getattr(e, "event_type", None)) == "time_limit"
    ]
    red_1_final = next(
        e for e in time_limit_events
        if (e.get("platform_id") if isinstance(e, dict) else getattr(e, "platform_id", None)) == "Red_1"
    )
    red_1_x = red_1_final.get("pos_x") if isinstance(red_1_final, dict) else red_1_final.pos_x
    # Red 1 was detected by sonobuoy at tick 1 and stopped at 60.0
    assert red_1_x == pytest.approx(60.0)


# ==============================================================================
# INT-15: Team Detection - Continue Intruder Spatial Boundary Escape
# ==============================================================================
def test_int_15_team_detection_continue_intruder_escape():
    """Verify detected 'continue' intruder crossing world boundary terminates as target_escaped."""
    sensor = GenericSensorConfig(
        display_name="Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 500.0],
        pod=[1.0, 1.0],
        type="generic",
        k=1,
        n=1,
        fov_start_deg=0.0,
        fov_end_deg=360.0,
    )
    blue = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=0.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=500.0, y=90.0), Waypoint(x=500.0, y=90.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[sensor],
    )
    # Red 1 starts near top of world (height=100m, so spawns at y=100.0) and heads south towards y <= 0
    # Blue is at (500, 90) so detects Red 1 right away
    red_1 = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=30.0,
        movement_type=IntruderSearchMovement(start_distance_m=0.0),
        neutralised_platform_behaviour="continue",
        sensors=[],
    )
    # Red 2 is far away so team detection does not complete
    red_2 = PlatformConfig(
        platform_config_folder="red_2",
        display_name="Red 2",
        team=Team.RED,
        speed_mps=0.0,
        movement_type=UserDefinedWaypointsMovement(
            waypoints=[Waypoint(x=5000.0, y=5000.0), Waypoint(x=5000.0, y=5000.0)]
        ),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=20.0,
            timestep_sec=1.0,
            seeds_file=False,
            detection_end_condition="team_detection",
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=1000.0, height=100.0),
        platforms=[blue, red_1, red_2],
    )
    outcome_manager = OutcomePositionManager(0)
    detection_manager = OutcomeDetectionManager(0)
    res = _execute_single_replication(
        config_data, outcome_manager, detection_manager, seed=42
    )

    assert res["end_condition"] == "target_escaped"
    assert res["result"] == "not_detected"





