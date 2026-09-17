"""
Module for defining and managing platform states within the Monte Carlo simulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

from src.monte_carlo.states.movement_manager import MovementManager, WpProperties

if TYPE_CHECKING:
    import numpy as np

    from src.schemas.movement import Waypoint
    from src.schemas.platform import MovementType, PlatformConfig, Team
    from src.schemas.simulation import (
        ConfigData,  # Ignore at runtime to prevent circular imports
    )


@dataclass
class PlatformState:
    """
    State of platform during runtime within the Monte Carlo simulation.
    """

    id: str  # Used as a unique identifier for the platform
    display_name: str  # User friendly name for the platform
    team: Union[str, Team]  # Team to which the platform belongs
    speed_mps: float  # Current speed of the platform
    pos: Waypoint  # Current position of the platform
    movement_type: MovementType
    wp_properties: WpProperties  # Properties of the current waypoint


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

    all_platform_states: list[
        PlatformState
    ] = []  # Initialize the list to store all platform states
    blue_counter = 0
    red_counter = 0
    id: str = ""  # Initialize an empty string for the platform ID

    for p in all_platforms:
        if p.team == "Blue":
            blue_counter += 1
            id = f"Blue_{blue_counter}"

        elif p.team == "Red":
            red_counter += 1
            id = f"Red_{red_counter}"

        initial_pos: Waypoint = movement_manager.get_waypoint(
            p.movement_type, config_data, random_gen
        )
        next_wp: Waypoint = movement_manager.get_waypoint(
            p.movement_type, config_data, random_gen
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
            wp_properties=wp_properties,
        )
        all_platform_states.append(platform_state)

    return all_platform_states
