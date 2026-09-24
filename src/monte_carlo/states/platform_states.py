"""
Module for defining and managing platform states within the Monte Carlo simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Union

from src.monte_carlo.states.movement_manager import MovementManager, WpProperties
from src.monte_carlo.states.movement_state import create_movement_state

if TYPE_CHECKING:
    import numpy as np

    from src.monte_carlo.detection_pipeline.sensor_state import SensorRuntimeState
    from src.monte_carlo.states.movement_state import MovementState
    from src.schemas.movement import Waypoint
    from src.schemas.platform import MovementType, PlatformConfig, Team
    from src.schemas.sensor import GenericSensorConfig, SpecificSensorConfig
    from src.schemas.simulation import (
        ConfigData,  # Ignore at runtime to prevent circular imports
    )


@dataclass
class PlatformState:
    """
    State of platform during runtime within the Monte Carlo simulation.
    """

    # Build from PlatformConfig blueprint, with runtime-specific fields initialized per replication

    id: str  # Used as a unique identifier for the platform
    display_name: str  # User friendly name for the platform
    team: Union[str, Team]  # Team to which the platform belongs
    speed_mps: float  # Current speed of the platform
    pos: Waypoint  # Current position of the platform
    movement_type: MovementType
    movement_state: MovementState  # Per-replication runtime state for movement_type, fresh each replication
    wp_properties: WpProperties  # Properties of the current waypoint
    sensors: list[
        Union[GenericSensorConfig, SpecificSensorConfig]
    ]  # Sensors fitted to this platform, used by the detection pipeline
    sensor_states: "dict[int, SensorRuntimeState]" = field(
        default_factory=dict
    )  # Per-sensor evaluation history, keyed by id(sensor) e.g. id(sensor): SensorRuntimeState


def assign_platform_ids(platforms: list[PlatformConfig]) -> list[str]:
    """Deterministically assign runtime platform ids (Blue_1, Blue_2, Red_1, ...) in config order.

    Extracted so anything outside the simulation (e.g. the animation loader, which
    needs to match raw_positions.csv's platform_id values) can derive the exact
    same ids without duplicating - and risking drifting from - this logic.
    """
    team_counters: dict[str, int] = {}
    ids: list[str] = []
    for platform in platforms:
        team = str(getattr(platform.team, "value", platform.team))
        team_counters[team] = team_counters.get(team, 0) + 1
        ids.append(f"{team}_{team_counters[team]}")
    return ids


def initialise_platform_states(
    config_data: ConfigData,
    random_gen: np.random.Generator,
    movement_manager: MovementManager,
) -> list[PlatformState]:
    """
    Initialise the states of all platforms for each replication in the Monte Carlo simulation.

    Args:
        config_data: The configuration data for the simulation.
        random_gen: A random number generator for reproducibility.
        movement_manager: The movement manager responsible for determining initial movement types.
        simulation_time: The current simulation time in the simulation.

    Returns:
        A list representing the initial states of all platforms.
    """
    # Determine all the platforms
    all_platforms: list[PlatformConfig] = config_data.platforms
    platform_ids = assign_platform_ids(all_platforms)

    all_platform_states: list[
        PlatformState
    ] = []  # Initialize the list to store all platform states

    for id, p in zip(platform_ids, all_platforms):
        # Fresh runtime state per replication, so spawn flags / waypoint index don't leak across replications
        movement_state: MovementState = create_movement_state(p.movement_type)

        # Generate platform at a random position if speed is zero
        if p.speed_mps == 0.0:
            initial_pos: Waypoint = movement_manager.get_waypoint(
                p.movement_type, config_data, random_gen, movement_state
            )
            wp_properties: WpProperties = WpProperties(
                pos=initial_pos,
                arrival_time=0.0,
                distance=0.0,
                heading=np.array([0.0, 0.0]),
                total_duration=0.0,
                step_distance=0.0,
            )
            platform_state = PlatformState(
                id=id,
                display_name=p.display_name,
                team=p.team,
                pos=initial_pos,
                speed_mps=p.speed_mps,
                movement_type=p.movement_type,
                movement_state=movement_state,
                wp_properties=wp_properties,
                sensors=p.sensors,
            )
            all_platform_states.append(platform_state)
            continue

        initial_pos: Waypoint = movement_manager.get_waypoint(
            p.movement_type, config_data, random_gen, movement_state
        )
        next_wp: Waypoint = movement_manager.get_waypoint(
            p.movement_type, config_data, random_gen, movement_state
        )
        assert initial_pos != next_wp, (
            f"Current position ({initial_pos.x}, {initial_pos.y}) and next position ({next_wp.x}, {next_wp.y}) must not be the same."
        )

        wp_properties: WpProperties = movement_manager.calculate_wp_properties(
            current_pos=initial_pos,
            wp=next_wp,
            speed_mps=p.speed_mps,
            timestep_sec=config_data.simulation.timestep_sec,
            sim_time=0.0,
        )

        platform_state = PlatformState(
            id=id,
            display_name=p.display_name,
            team=p.team,
            pos=initial_pos,
            speed_mps=p.speed_mps,
            movement_type=p.movement_type,
            movement_state=movement_state,
            wp_properties=wp_properties,
            sensors=p.sensors,
        )
        all_platform_states.append(platform_state)

    return all_platform_states
