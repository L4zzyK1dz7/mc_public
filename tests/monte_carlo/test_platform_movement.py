from __future__ import annotations

import numpy as np
import pytest

from src.monte_carlo.states.platform_states import (
    PlatformState,
    WpProperties,
    initialise_platform_states,
)
from src.schemas.movement import RandomWalkMovement, Waypoint
from src.schemas.platform import PlatformConfig
from src.schemas.simulation import ConfigData, SimulationConfig, World


def test_platform_advance_step_moves_position():
    blueprint = PlatformConfig(
        platform_config_folder="Blue_1",
        display_name="Blue_1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        sensors=[],
    )
    initial_pos = Waypoint(x=0.0, y=0.0)
    target_pos = Waypoint(x=100.0, y=0.0)
    wp_props = WpProperties(
        pos=target_pos,
        arrival_time=10.0,
        distance=100.0,
        heading=np.array([1.0, 0.0]),
        total_duration=10.0,
        step_distance=10.0,
    )
    platform = PlatformState.from_blueprint(
        platform_id="Blue_1",
        blueprint=blueprint,
        initial_pos=initial_pos,
        wp_properties=wp_props,
    )

    rng = np.random.default_rng(42)
    sim_config = SimulationConfig(
        replications=1,
        time_limit_sec=100.0,
        timestep_sec=1.0,
        seeds_file=False,
        detection_end_condition="initial_detection",
    )
    world_config = World(length=1000.0, height=1000.0)
    config_data = ConfigData(
        simulation=sim_config,
        world=world_config,
        platforms=[blueprint],
    )

    # Step 1: sim_time = 1.0 (before arrival at 10.0)
    generated = platform.advance_step(sim_time_sec=1.0, config_data=config_data, random_gen=rng)
    assert not generated
    assert platform.pos.x == pytest.approx(10.0)
    assert platform.pos.y == pytest.approx(0.0)

    # Step 2: sim_time = 2.0
    generated = platform.advance_step(sim_time_sec=2.0, config_data=config_data, random_gen=rng)
    assert not generated
    assert platform.pos.x == pytest.approx(20.0)
    assert platform.pos.y == pytest.approx(0.0)


def test_initialise_platform_states():
    blueprint = PlatformConfig(
        platform_config_folder="Blue_1",
        display_name="Blue_1",
        team="Blue",
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        sensors=[],
    )
    sim_config = SimulationConfig(
        replications=1,
        time_limit_sec=100.0,
        timestep_sec=1.0,
        seeds_file=False,
        detection_end_condition="initial_detection",
    )
    world_config = World(length=1000.0, height=1000.0)
    config_data = ConfigData(
        simulation=sim_config,
        world=world_config,
        platforms=[blueprint],
    )

    rng = np.random.default_rng(123)
    states = initialise_platform_states(config_data, rng)

    assert len(states) == 1
    p = states[0]
    assert p.id == "Blue_1"
    assert p.speed_mps == 10.0
    assert p.wp_properties.step_distance == pytest.approx(10.0)
    assert p.wp_properties.arrival_time > 0.0
