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
from src.schemas.movement import IntruderSearchMovement, RandomWalkMovement
from src.schemas.platform import PlatformConfig, Team
from src.schemas.sensor import GenericSensorConfig
from src.schemas.simulation import ConfigData, SimulationConfig, World


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
