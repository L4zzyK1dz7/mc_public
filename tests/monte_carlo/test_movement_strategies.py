"""
Suite 3: Movement Strategies (MOV-01 to MOV-06)
Verification of polymorphic waypoint generation algorithms and kinematics.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.monte_carlo.states.movement_state import (
    BarrierPatrollerState,
    BarrierPatrollerStrategy,
    IntruderSearchState,
    IntruderSearchStrategy,
    RandomWalkState,
    RandomWalkStrategy,
    UserDefinedWaypointsState,
    UserDefinedWaypointsStrategy,
    create_movement_state,
    create_movement_strategy,
)
from src.schemas.movement import (
    BarrierPatrollerMovement,
    IntruderEndCondition,
    IntruderSearchMovement,
    RandomWalkMovement,
    UserDefinedWaypointsMovement,
    Waypoint,
)
from src.schemas.simulation import ConfigData, SimulationConfig, World


@pytest.fixture
def base_config_data() -> ConfigData:
    return ConfigData(
        simulation=SimulationConfig(
            replications=1,
            time_limit_sec=1000.0,
            timestep_sec=1.0,
            seeds_file=False,
        ),
        world=World(origin_x=0.0, origin_y=0.0, length=1000.0, height=1000.0),
        platforms=[],
    )


# ==============================================================================
# MOV-01: Geometric boundary containment for random walk
# ==============================================================================
def test_mov_01_random_walk_boundary_containment(base_config_data: ConfigData):
    """Verify random walk stays strictly within world bounds across 1,000 steps."""
    strategy = RandomWalkStrategy()
    state = RandomWalkState()
    config = RandomWalkMovement()
    rng = np.random.default_rng(999)

    for _ in range(1000):
        wp = strategy.get_next_waypoint(config, state, base_config_data, rng)
        assert 0.0 <= wp.x <= 1000.0
        assert 0.0 <= wp.y <= 1000.0


# ==============================================================================
# MOV-02: Pseudorandom path determinism
# ==============================================================================
def test_mov_02_pseudorandom_path_determinism(base_config_data: ConfigData):
    """Verify two runs with identical random seeds produce identical waypoint sequences."""
    strategy = RandomWalkStrategy()
    config = RandomWalkMovement()

    rng1 = np.random.default_rng(42)
    state1 = RandomWalkState()
    seq1 = [strategy.get_next_waypoint(config, state1, base_config_data, rng1) for _ in range(50)]

    rng2 = np.random.default_rng(42)
    state2 = RandomWalkState()
    seq2 = [strategy.get_next_waypoint(config, state2, base_config_data, rng2) for _ in range(50)]

    for wp1, wp2 in zip(seq1, seq2):
        assert wp1.x == wp2.x
        assert wp1.y == wp2.y


# ==============================================================================
# MOV-03: Linear waypoint navigation sequence order
# ==============================================================================
def test_mov_03_user_defined_waypoints_sequence_order(base_config_data: ConfigData):
    """Verify linear waypoint navigation sequence order [(0,0), (100,0), (100,100), (0,100)]."""
    coords = [
        Waypoint(x=0.0, y=0.0),
        Waypoint(x=100.0, y=0.0),
        Waypoint(x=100.0, y=100.0),
        Waypoint(x=0.0, y=100.0),
    ]
    config = UserDefinedWaypointsMovement(waypoints=coords)
    strategy = UserDefinedWaypointsStrategy()
    state = UserDefinedWaypointsState()
    rng = np.random.default_rng(1)

    visited = [
        strategy.get_next_waypoint(config, state, base_config_data, rng)
        for _ in range(len(coords))
    ]

    for expected, actual in zip(coords, visited):
        assert actual.x == expected.x
        assert actual.y == expected.y


# ==============================================================================
# MOV-04: Route termination / cycling behaviour
# ==============================================================================
def test_mov_04_user_defined_waypoints_cycling(base_config_data: ConfigData):
    """Verify user-defined waypoint route seamlessly cycles after reaching terminal node."""
    coords = [
        Waypoint(x=10.0, y=20.0),
        Waypoint(x=30.0, y=40.0),
    ]
    config = UserDefinedWaypointsMovement(waypoints=coords)
    strategy = UserDefinedWaypointsStrategy()
    state = UserDefinedWaypointsState()
    rng = np.random.default_rng(1)

    # 4 calls should visit: [coords[0], coords[1], coords[0], coords[1]]
    wps = [strategy.get_next_waypoint(config, state, base_config_data, rng) for _ in range(4)]
    assert wps[0].x == 10.0 and wps[0].y == 20.0
    assert wps[1].x == 30.0 and wps[1].y == 40.0
    assert wps[2].x == 10.0 and wps[2].y == 20.0
    assert wps[3].x == 30.0 and wps[3].y == 40.0


# ==============================================================================
# MOV-05: Transit kinematics for intruder search pattern
# ==============================================================================
def test_mov_05_intruder_search_kinematics(base_config_data: ConfigData):
    """Verify intruder spawns above world and traverses downwards towards barrier/bottom."""
    config = IntruderSearchMovement(
        start_distance_m=50.0,
        end_condition=IntruderEndCondition.CROSS_WORLD,
    )
    strategy = IntruderSearchStrategy()
    state = IntruderSearchState()
    rng = np.random.default_rng(100)

    # Step 1: Initial spawn above world (height = 1000 + 50 = 1050)
    spawn = strategy.get_next_waypoint(config, state, base_config_data, rng)
    assert 0.0 <= spawn.x <= 1000.0
    assert spawn.y == pytest.approx(1050.0)

    # Step 2: Next waypoint traverses down towards world bottom (origin_y - 10 = -10)
    target = strategy.get_next_waypoint(config, state, base_config_data, rng)
    assert target.x == pytest.approx(spawn.x)  # Linear vertical transit
    assert target.y == pytest.approx(-10.0)    # Directed downwards across world


# ==============================================================================
# MOV-06: Cyclic patrol kinematics for barrier patroller
# ==============================================================================
def test_mov_06_barrier_patroller_kinematics(base_config_data: ConfigData):
    """Verify barrier patroller oscillates between barrier endpoints."""
    config = BarrierPatrollerMovement(
        start_x_pos=100.0,
        start_y_pos=200.0,
        length=500.0,
        height=0.0,
    )
    strategy = BarrierPatrollerStrategy()
    state = BarrierPatrollerState()
    rng = np.random.default_rng(200)

    # 1st call: initial position within [100.0, 600.0] at y=200
    initial = strategy.get_next_waypoint(config, state, base_config_data, rng)
    assert 100.0 <= initial.x <= 600.0
    assert initial.y == pytest.approx(200.0)

    # 2nd call: moves towards one side (100.0 or 600.0)
    first_side = strategy.get_next_waypoint(config, state, base_config_data, rng)
    assert first_side.x in (100.0, 600.0)
    assert first_side.y == pytest.approx(200.0)

    # 3rd call: oscillates to opposite side
    second_side = strategy.get_next_waypoint(config, state, base_config_data, rng)
    assert second_side.x in (100.0, 600.0)
    assert second_side.x != first_side.x
    assert second_side.y == pytest.approx(200.0)

    # 4th call: returns to first side
    third_side = strategy.get_next_waypoint(config, state, base_config_data, rng)
    assert third_side.x == first_side.x
