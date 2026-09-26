"""
Suite 1: Schema & Configuration Validation (SCH-01 to SCH-14)
Verification of input schemas and YAML configuration parsing.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from pydantic import ValidationError

from src.schemas.platform import PlatformConfig, Team
from src.schemas.movement import (
    RandomWalkMovement,
    IntruderSearchMovement,
    BarrierPatrollerMovement,
    UserDefinedWaypointsMovement,
    Waypoint,
    IntruderEndCondition,
)
from src.schemas.sensor import GenericSensorConfig, SpecificSensorConfig, SensorConfig
from src.schemas.simulation import ConfigData, SimulationConfig, World
from src.monte_carlo.configuration.load_configuration import (
    load_config_from_yaml,
    load_seeds,
)


# ==============================================================================
# SCH-01: Platform team affiliation validation
# ==============================================================================
def test_sch_01_platform_team_affiliation_valid():
    """Verify platform accepts authorized team designations ('Blue', 'Red', Team enums)."""
    p_blue = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
    )
    assert p_blue.team in ("Blue", Team.BLUE)

    p_red = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Red 1",
        team=Team.RED,
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
    )
    assert p_red.team in ("Red", Team.RED)


def test_sch_01_platform_team_affiliation_invalid():
    """Verify platform rejects unauthorized team strings ('Green', empty, numbers)."""
    with pytest.raises(ValidationError):
        PlatformConfig(
            platform_config_folder="green_1",
            display_name="Green 1",
            team="Green",
            speed_mps=10.0,
            movement_type=RandomWalkMovement(),
        )

    with pytest.raises(ValidationError):
        PlatformConfig(
            platform_config_folder="empty_1",
            display_name="Empty 1",
            team="",
            speed_mps=10.0,
            movement_type=RandomWalkMovement(),
        )

    with pytest.raises(ValidationError):
        PlatformConfig(
            platform_config_folder="num_1",
            display_name="Num 1",
            team=42,  # type: ignore[arg-type]
            speed_mps=10.0,
            movement_type=RandomWalkMovement(),
        )


# ==============================================================================
# SCH-02: Platform speed kinematics boundary validation
# ==============================================================================
def test_sch_02_platform_speed_kinematics():
    """Verify platform accepts non-negative speed and rejects negative velocity."""
    p_positive = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=15.5,
        movement_type=RandomWalkMovement(),
    )
    assert p_positive.speed_mps == 15.5

    p_stationary = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=0.0,
        movement_type=RandomWalkMovement(),
    )
    assert p_stationary.speed_mps == 0.0

    with pytest.raises(ValidationError):
        PlatformConfig(
            platform_config_folder="blue_1",
            display_name="Blue 1",
            team="Blue",
            speed_mps=-5.0,
            movement_type=RandomWalkMovement(),
        )


# ==============================================================================
# SCH-03: Neutralisation behaviour parameter parsing
# ==============================================================================
def test_sch_03_neutralisation_behaviour():
    """Verify supported directives ('stop', 'continue') and rejection of invalid ones."""
    p_stop = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        neutralised_platform_behaviour="stop",
    )
    assert p_stop.neutralised_platform_behaviour == "stop"

    p_cont = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        neutralised_platform_behaviour="continue",
    )
    assert p_cont.neutralised_platform_behaviour == "continue"

    with pytest.raises(ValidationError):
        PlatformConfig(
            platform_config_folder="blue_1",
            display_name="Blue 1",
            team="Blue",
            speed_mps=10.0,
            movement_type=RandomWalkMovement(),
            neutralised_platform_behaviour="destroy",  # type: ignore[arg-type]
        )


# ==============================================================================
# SCH-04: Default schema instantiation for random walk
# ==============================================================================
def test_sch_04_random_walk_default():
    """Verify default schema instantiation for random walk movement configuration."""
    rw = RandomWalkMovement()
    assert rw.type == "random_walk"


# ==============================================================================
# SCH-05: Intruder search profile boundary validation
# ==============================================================================
def test_sch_05_intruder_search_boundaries():
    """Verify intruder search profiles with non-negative offset vs negative distance."""
    search_valid = IntruderSearchMovement(
        start_distance_m=50.0,
        end_condition=IntruderEndCondition.CROSS_BARRIER,
    )
    assert search_valid.start_distance_m == 50.0
    assert search_valid.end_condition == IntruderEndCondition.CROSS_BARRIER
    assert search_valid.type == "intruder_search"

    search_zero = IntruderSearchMovement(start_distance_m=0.0)
    assert search_zero.start_distance_m == 0.0

    with pytest.raises(ValidationError):
        IntruderSearchMovement(start_distance_m=-10.0)


# ==============================================================================
# SCH-06: Barrier patroller geometric parameter validation
# ==============================================================================
def test_sch_06_barrier_patroller_dimensions():
    """Verify barrier patroller bounding dimensions non-negativity."""
    bp_valid = BarrierPatrollerMovement(
        start_x_pos=100.0,
        start_y_pos=200.0,
        length=500.0,
        height=50.0,
    )
    assert bp_valid.length == 500.0
    assert bp_valid.height == 50.0

    with pytest.raises(ValidationError):
        BarrierPatrollerMovement(
            start_x_pos=0.0,
            start_y_pos=0.0,
            length=-10.0,
            height=50.0,
        )

    with pytest.raises(ValidationError):
        BarrierPatrollerMovement(
            start_x_pos=0.0,
            start_y_pos=0.0,
            length=50.0,
            height=-5.0,
        )


# ==============================================================================
# SCH-07: User-defined waypoint coordinate list deserialisation
# ==============================================================================
def test_sch_07_user_defined_waypoints_deserialisation():
    """Verify user-defined waypoint paths deserialise valid coordinates and reject invalid ones."""
    wp_move = UserDefinedWaypointsMovement(
        waypoints=[
            Waypoint(x=0.0, y=0.0),
            Waypoint(x=100.0, y=50.0),
            Waypoint(x=200.0, y=100.0),
        ]
    )
    assert len(wp_move.waypoints) == 3
    assert wp_move.waypoints[1].x == 100.0
    assert wp_move.waypoints[1].y == 50.0

    # Also test deserialisation from dict list
    wp_from_dict = UserDefinedWaypointsMovement(
        waypoints=[{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}]  # type: ignore[arg-type]
    )
    assert len(wp_from_dict.waypoints) == 2
    assert wp_from_dict.waypoints[0].x == 10.0

    with pytest.raises(ValidationError):
        UserDefinedWaypointsMovement(
            waypoints=[{"x": "non_numeric", "y": 20.0}]  # type: ignore[arg-type]
        )


# ==============================================================================
# SCH-08: Angular FOV parameter bounds for generic sensors
# ==============================================================================
def test_sch_08_sensor_fov_bounds():
    """Verify angular field-of-view bounds [0.0, 360.0] degrees."""
    sensor_valid = GenericSensorConfig(
        display_name="Test Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 100.0],
        pod=[1.0, 0.5],
        k=1,
        n=1,
        fov_start_deg=0.0,
        fov_end_deg=180.0,
    )
    assert sensor_valid.fov_start_deg == 0.0
    assert sensor_valid.fov_end_deg == 180.0

    with pytest.raises(ValidationError):
        GenericSensorConfig(
            display_name="Bad FOV",
            interval_time_sec=1.0,
            x_values=[0.0, 100.0],
            pod=[1.0, 0.5],
            k=1,
            n=1,
            fov_start_deg=-10.0,
            fov_end_deg=180.0,
        )

    with pytest.raises(ValidationError):
        GenericSensorConfig(
            display_name="Bad FOV",
            interval_time_sec=1.0,
            x_values=[0.0, 100.0],
            pod=[1.0, 0.5],
            k=1,
            n=1,
            fov_start_deg=0.0,
            fov_end_deg=370.0,
        )


# ==============================================================================
# SCH-09: Statistical K-of-N sliding window parameter constraints
# ==============================================================================
def test_sch_09_sensor_k_of_n_constraints():
    """Verify K <= N, K > 0, N > 0 constraints."""
    sensor = GenericSensorConfig(
        display_name="Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 100.0],
        pod=[1.0, 0.5],
        k=3,
        n=5,
    )
    assert sensor.k == 3
    assert sensor.n == 5

    # K > N must fail
    with pytest.raises(ValidationError):
        GenericSensorConfig(
            display_name="Radar",
            interval_time_sec=1.0,
            x_values=[0.0, 100.0],
            pod=[1.0, 0.5],
            k=6,
            n=5,
        )

    # K = 0 must fail (gt=0)
    with pytest.raises(ValidationError):
        GenericSensorConfig(
            display_name="Radar",
            interval_time_sec=1.0,
            x_values=[0.0, 100.0],
            pod=[1.0, 0.5],
            k=0,
            n=5,
        )

    # N = 0 must fail (gt=0)
    with pytest.raises(ValidationError):
        GenericSensorConfig(
            display_name="Radar",
            interval_time_sec=1.0,
            x_values=[0.0, 100.0],
            pod=[1.0, 0.5],
            k=1,
            n=0,
        )


# ==============================================================================
# SCH-10: Probability-of-detection (PoD) curve consistency
# ==============================================================================
def test_sch_10_sensor_pod_curve_consistency():
    """Verify dimension parity and normalized probabilities within [0.0, 1.0]."""
    # Unequal dimensions
    with pytest.raises(ValidationError):
        GenericSensorConfig(
            display_name="Radar",
            interval_time_sec=1.0,
            x_values=[0.0, 50.0, 100.0],
            pod=[1.0, 0.5],
            k=1,
            n=1,
        )

    # Probability > 1.0
    with pytest.raises(ValidationError):
        GenericSensorConfig(
            display_name="Radar",
            interval_time_sec=1.0,
            x_values=[0.0, 100.0],
            pod=[1.2, 0.5],
            k=1,
            n=1,
        )

    # Probability < 0.0
    with pytest.raises(ValidationError):
        GenericSensorConfig(
            display_name="Radar",
            interval_time_sec=1.0,
            x_values=[0.0, 100.0],
            pod=[-0.1, 0.5],
            k=1,
            n=1,
        )


# ==============================================================================
# SCH-11: World envelope dimensional validation
# ==============================================================================
def test_sch_11_world_envelope_dimensions():
    """Verify positive world boundaries (L > 0, H > 0) versus negative or zero."""
    w = World(origin_x=0.0, origin_y=0.0, length=1000.0, height=2000.0)
    assert w.length == 1000.0
    assert w.height == 2000.0

    with pytest.raises(ValidationError):
        World(length=0.0, height=1000.0)

    with pytest.raises(ValidationError):
        World(length=-500.0, height=1000.0)

    with pytest.raises(ValidationError):
        World(length=1000.0, height=-100.0)


# ==============================================================================
# SCH-12: Simulation execution parameters validation
# ==============================================================================
def test_sch_12_simulation_execution_parameters():
    """Verify replications > 0, time_limit_sec > 0, timestep_sec > 0."""
    sim = SimulationConfig(
        replications=10,
        time_limit_sec=3600.0,
        timestep_sec=1.0,
        seeds_file=False,
    )
    assert sim.replications == 10
    assert sim.time_limit_sec == 3600.0
    assert sim.timestep_sec == 1.0

    with pytest.raises(ValidationError):
        SimulationConfig(
            replications=0,
            time_limit_sec=3600.0,
            timestep_sec=1.0,
            seeds_file=False,
        )

    with pytest.raises(ValidationError):
        SimulationConfig(
            replications=5,
            time_limit_sec=-100.0,
            timestep_sec=1.0,
            seeds_file=False,
        )

    with pytest.raises(ValidationError):
        SimulationConfig(
            replications=5,
            time_limit_sec=100.0,
            timestep_sec=0.0,
            seeds_file=False,
        )


# ==============================================================================
# SCH-13: Top-level scenario deserialisation
# ==============================================================================
def test_sch_13_config_data_deserialisation():
    """Verify top-level scenario deserialisation from full dictionary graph."""
    data = {
        "simulation": {
            "replications": 5,
            "time_limit_sec": 600.0,
            "timestep_sec": 2.0,
            "seeds_file": False,
            "detection_end_condition": "initial_detection",
        },
        "world": {
            "origin_x": 0.0,
            "origin_y": 0.0,
            "length": 5000.0,
            "height": 5000.0,
        },
        "platforms": [
            {
                "platform_config_folder": "blue_1",
                "display_name": "Blue Fighter",
                "team": "Blue",
                "speed_mps": 25.0,
                "movement_type": {"type": "random_walk"},
                "neutralised_platform_behaviour": "stop",
                "sensors": [],
            },
            {
                "platform_config_folder": "red_1",
                "display_name": "Red Drone",
                "team": "Red",
                "speed_mps": 12.0,
                "movement_type": {
                    "type": "intruder_search",
                    "start_distance_m": 100.0,
                    "end_condition": "cross_world",
                },
                "neutralised_platform_behaviour": "continue",
                "sensors": [],
            },
        ],
    }

    config = ConfigData.from_dict(data)
    assert config.simulation.replications == 5
    assert config.world.length == 5000.0
    assert len(config.platforms) == 2
    assert config.platforms[0].display_name == "Blue Fighter"
    assert config.platforms[1].movement_type.type == "intruder_search"


# ==============================================================================
# SCH-14: Resilience and diagnostic reporting on missing configuration files
# ==============================================================================
def test_sch_14_missing_configuration_files(tmp_path: Path):
    """Verify FileNotFoundError is raised when YAML or seeds file is non-existent."""
    non_existent_yaml = tmp_path / "does_not_exist.yaml"
    with pytest.raises(FileNotFoundError):
        load_config_from_yaml(non_existent_yaml)

    non_existent_seeds = tmp_path / "seeds.txt"
    with pytest.raises(FileNotFoundError):
        load_seeds(non_existent_seeds, replications=5)
