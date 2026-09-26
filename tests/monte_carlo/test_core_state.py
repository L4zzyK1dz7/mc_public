"""
Suite 2: Core State Management (STA-01 to STA-09)
Verification of runtime state instantiation, kinematics tracking, and sensor states.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.monte_carlo.detection_pipeline.sensor_state import SensorRuntimeState
from src.monte_carlo.states.platform_states import (
    PlatformState,
    WpProperties,
    initialise_platform_states,
)
from src.schemas.movement import (
    RandomWalkMovement,
    UserDefinedWaypointsMovement,
    Waypoint,
)
from src.schemas.platform import PlatformConfig, Team
from src.schemas.sensor import GenericSensorConfig
from src.schemas.simulation import ConfigData, SimulationConfig, World


# ==============================================================================
# STA-01: Runtime state factory instantiation of PlatformState
# ==============================================================================
def test_sta_01_platform_state_instantiation():
    """Verify runtime factory instantiates PlatformState from blueprint and World."""
    blueprint = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue Fighter",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    sim_config = SimulationConfig(
        replications=1,
        time_limit_sec=100.0,
        timestep_sec=1.0,
        seeds_file=False,
    )
    world = World(origin_x=0.0, origin_y=0.0, length=1000.0, height=1000.0)
    config_data = ConfigData(
        simulation=sim_config,
        world=world,
        platforms=[blueprint],
    )

    rng = np.random.default_rng(12345)
    states = initialise_platform_states(config_data, rng)

    assert len(states) == 1
    platform = states[0]
    assert platform.id == "Blue_1"
    assert platform.speed_mps == 10.0
    assert platform.team == Team.BLUE
    assert platform.neutralized is False
    assert 0.0 <= platform.pos.x <= 1000.0
    assert 0.0 <= platform.pos.y <= 1000.0
    assert platform.wp_properties.step_distance == pytest.approx(10.0)
    assert platform.blueprint is blueprint


# ==============================================================================
# STA-02: Kinematic state progression delegation during advance_step()
# ==============================================================================
def test_sta_02_kinematic_progression():
    """Verify kinematic state progression delegates correctly under delta_t = 1.0s."""
    blueprint = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        sensors=[],
    )
    wp_props = WpProperties(
        pos=Waypoint(x=100.0, y=0.0),
        arrival_time=10.0,
        distance=100.0,
        heading=np.array([1.0, 0.0]),
        total_duration=10.0,
        step_distance=10.0,
    )
    platform = PlatformState.from_blueprint(
        platform_id="Blue_1",
        blueprint=blueprint,
        initial_pos=Waypoint(x=0.0, y=0.0),
        wp_properties=wp_props,
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1, time_limit_sec=100.0, timestep_sec=1.0, seeds_file=False
        ),
        world=World(length=1000.0, height=1000.0),
        platforms=[blueprint],
    )
    rng = np.random.default_rng(42)

    # Before advance
    assert platform.pos.x == 0.0
    assert platform.pos.y == 0.0

    # Advance 1 step
    platform.advance_step(sim_time_sec=1.0, config_data=config_data, random_gen=rng)
    assert platform.pos.x == pytest.approx(10.0)
    assert platform.pos.y == pytest.approx(0.0)
    # Ensure immutable blueprint has not changed
    assert blueprint.speed_mps == 10.0


# ==============================================================================
# STA-03: State lockdown upon platform neutralisation
# ==============================================================================
def test_sta_03_state_lockdown_on_neutralisation():
    """Verify entity halts all translation when neutralized=True with behaviour='stop'."""
    blueprint = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        neutralised_platform_behaviour="stop",
        sensors=[],
    )
    wp_props = WpProperties(
        pos=Waypoint(x=100.0, y=0.0),
        arrival_time=10.0,
        distance=100.0,
        heading=np.array([1.0, 0.0]),
        total_duration=10.0,
        step_distance=10.0,
    )
    platform = PlatformState.from_blueprint(
        platform_id="Blue_1",
        blueprint=blueprint,
        initial_pos=Waypoint(x=0.0, y=0.0),
        wp_properties=wp_props,
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1, time_limit_sec=100.0, timestep_sec=1.0, seeds_file=False
        ),
        world=World(length=1000.0, height=1000.0),
        platforms=[blueprint],
    )
    rng = np.random.default_rng(42)

    # Step 1: active movement
    platform.advance_step(sim_time_sec=1.0, config_data=config_data, random_gen=rng)
    assert platform.pos.x == pytest.approx(10.0)

    # Now neutralise the platform
    platform.neutralized = True
    assert platform.neutralised is True

    # Step 2: should be halted
    gen = platform.advance_step(sim_time_sec=2.0, config_data=config_data, random_gen=rng)
    assert gen is False
    assert platform.pos.x == pytest.approx(10.0)  # Positional lockdown maintained


# ==============================================================================
# STA-04: Linear distance-to-go calculations and step increment tracking
# ==============================================================================
def test_sta_04_distance_to_go_tracking():
    """Traversing (0,0) to (100,0) at 10m/s decrements distance from 100m to 90m."""
    blueprint = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        sensors=[],
    )
    wp_props = WpProperties(
        pos=Waypoint(x=100.0, y=0.0),
        arrival_time=10.0,
        distance=100.0,
        heading=np.array([1.0, 0.0]),
        total_duration=10.0,
        step_distance=10.0,
    )
    platform = PlatformState.from_blueprint(
        platform_id="Blue_1",
        blueprint=blueprint,
        initial_pos=Waypoint(x=0.0, y=0.0),
        wp_properties=wp_props,
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1, time_limit_sec=100.0, timestep_sec=1.0, seeds_file=False
        ),
        world=World(length=1000.0, height=1000.0),
        platforms=[blueprint],
    )
    rng = np.random.default_rng(42)

    assert platform.wp_properties.distance == 100.0
    platform.advance_step(sim_time_sec=1.0, config_data=config_data, random_gen=rng)
    assert platform.pos.x == pytest.approx(10.0)
    assert platform.wp_properties.distance == pytest.approx(90.0)


# ==============================================================================
# STA-05: Waypoint arrival threshold detection and flight leg transition
# ==============================================================================
def test_sta_05_waypoint_arrival_and_leg_transition():
    """Verify arrival at waypoint triggers transition to next waypoint leg."""
    waypoints = [
        Waypoint(x=0.0, y=0.0),
        Waypoint(x=10.0, y=0.0),
        Waypoint(x=10.0, y=20.0),
    ]
    blueprint = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(waypoints=waypoints),
        sensors=[],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1, time_limit_sec=100.0, timestep_sec=1.0, seeds_file=False
        ),
        world=World(length=1000.0, height=1000.0),
        platforms=[blueprint],
    )
    rng = np.random.default_rng(42)

    # Initialise leg towards (10, 0), arrives at t=1.0
    wp_props = WpProperties(
        pos=Waypoint(x=10.0, y=0.0),
        arrival_time=1.0,
        distance=10.0,
        heading=np.array([1.0, 0.0]),
        total_duration=1.0,
        step_distance=10.0,
    )
    platform = PlatformState.from_blueprint(
        platform_id="Blue_1",
        blueprint=blueprint,
        initial_pos=Waypoint(x=0.0, y=0.0),
        wp_properties=wp_props,
    )
    # Since index 0 (spawn) and index 1 (first leg) were used, current_index is 2
    platform.movement_state.current_index = 2

    # At t=1.0, arrival_time <= sim_time_sec triggers new waypoint request
    generated = platform.advance_step(sim_time_sec=1.0, config_data=config_data, random_gen=rng)
    assert generated is True
    # Next leg should point toward (10.0, 20.0)
    assert platform.wp_properties.pos.x == 10.0
    assert platform.wp_properties.pos.y == 20.0


# ==============================================================================
# STA-06: Step distance overshoot handling
# ==============================================================================
def test_sta_06_step_overshoot_handling():
    """Verify integration step handles arrival when step reaches target waypoint."""
    waypoints = [
        Waypoint(x=0.0, y=0.0),
        Waypoint(x=5.0, y=0.0),
        Waypoint(x=5.0, y=10.0),
    ]
    blueprint = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team="Blue",
        speed_mps=10.0,
        movement_type=UserDefinedWaypointsMovement(waypoints=waypoints),
        sensors=[],
    )
    config_data = ConfigData(
        simulation=SimulationConfig(
            replications=1, time_limit_sec=100.0, timestep_sec=1.0, seeds_file=False
        ),
        world=World(length=1000.0, height=1000.0),
        platforms=[blueprint],
    )
    rng = np.random.default_rng(42)

    wp_props = WpProperties(
        pos=Waypoint(x=5.0, y=0.0),
        arrival_time=0.5,
        distance=5.0,
        heading=np.array([1.0, 0.0]),
        total_duration=0.5,
        step_distance=10.0,
    )
    platform = PlatformState.from_blueprint(
        platform_id="Blue_1",
        blueprint=blueprint,
        initial_pos=Waypoint(x=0.0, y=0.0),
        wp_properties=wp_props,
    )
    platform.movement_state.current_index = 2

    generated = platform.advance_step(sim_time_sec=1.0, config_data=config_data, random_gen=rng)
    assert generated is True
    assert platform.wp_properties.pos.y == 10.0


# ==============================================================================
# STA-07: Sliding window capacity and FIFO eviction in SensorRuntimeState
# ==============================================================================
def test_sta_07_sensor_sliding_window_fifo():
    """Verify sliding window capacity N=5 enforces deque maxlen and purges oldest."""
    sensor_state = SensorRuntimeState()
    window = sensor_state.get_window("Target_1", maxlen=5)

    # Supply 8 booleans
    observations = [True, False, True, True, False, True, True, True]
    for obs in observations:
        window.append(obs)

    assert len(window) == 5
    # The 5 most recent should be [True, False, True, True, True]
    assert list(window) == [True, False, True, True, True]


# ==============================================================================
# STA-08: History isolation across concurrent target observations
# ==============================================================================
def test_sta_08_sensor_history_isolation():
    """Verify multiple targets get isolated detection queues on the same sensor."""
    sensor_state = SensorRuntimeState()
    win_a = sensor_state.get_window("Target_A", maxlen=3)
    win_b = sensor_state.get_window("Target_B", maxlen=3)

    win_a.append(True)
    win_a.append(True)
    win_b.append(False)

    assert list(win_a) == [True, True]
    assert list(win_b) == [False]


# ==============================================================================
# STA-09: Clean state reset between replication cycles
# ==============================================================================
def test_sta_09_sensor_state_clean_reset():
    """Verify reset() purges all target queues and resets eval timer."""
    sensor_state = SensorRuntimeState(next_eval_time_sec=15.0)
    sensor_state.get_window("Target_A", maxlen=3).append(True)

    sensor_state.reset()
    assert sensor_state.next_eval_time_sec == 0.0
    assert len(sensor_state.hit_windows) == 0
