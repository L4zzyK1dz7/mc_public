"""
Module for defining and managing platform states within the Monte Carlo simulation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import numpy as np

from src.monte_carlo.states.movement_state import (
    MovementState,
    MovementStrategy,
    create_movement_state,
    create_movement_strategy,
)
from src.schemas.movement import Waypoint

if TYPE_CHECKING:
    from src.monte_carlo.detection_pipeline.sensor_state import SensorRuntimeState
    from src.schemas.platform import PlatformConfig
    from src.schemas.simulation import ConfigData


@dataclass
class WpProperties:
    """Kinematics properties of the current waypoint leg."""

    pos: Waypoint  # Current target waypoint position
    arrival_time: float  # Expected arrival time at the waypoint
    distance: float  # Total distance from initial position to waypoint
    heading: np.ndarray  # Normalised direction vector [dx, dy]
    total_duration: float  # Total time required to reach the waypoint
    step_distance: float  # Distance covered in one timestep (speed_mps * timestep_sec)


def calculate_heading(
    current_position: Waypoint,
    next_position: Waypoint,
) -> np.ndarray:
    """Compute the normalised 2D direction vector from current to next position."""
    dx = next_position.x - current_position.x
    dy = next_position.y - current_position.y
    distance = math.hypot(dx, dy)
    if distance > 0:
        return np.array([dx / distance, dy / distance])
    return np.array([0.0, 0.0])


def calculate_wp_properties(
    current_pos: Waypoint,
    wp: Waypoint,
    speed_mps: float,
    timestep_sec: float,
    sim_time: float,
) -> WpProperties:
    """Calculate kinematics properties for moving towards a target waypoint."""
    if speed_mps == 0.0:
        return WpProperties(
            pos=wp,
            arrival_time=sim_time,
            distance=0.0,
            heading=np.array([0.0, 0.0]),
            total_duration=0.0,
            step_distance=0.0,
        )

    dx = wp.x - current_pos.x
    dy = wp.y - current_pos.y
    distance = math.hypot(dx, dy)
    heading = calculate_heading(current_pos, wp)
    total_duration = distance / speed_mps
    step_distance = speed_mps * timestep_sec
    arrival_time = sim_time + total_duration

    return WpProperties(
        pos=wp,
        arrival_time=arrival_time,
        distance=distance,
        heading=heading,
        total_duration=total_duration,
        step_distance=step_distance,
    )


@dataclass
class PlatformState:
    """
    Runtime state of a platform for a single Monte Carlo replication.

    Holds the immutable blueprint (``PlatformConfig``) together with all mutable,
    per-replication state (position, movement runtime, sensor runtime, etc.) so
    that the same blueprint can be safely reused across every replication without
    any cross-replication state leakage.
    """

    # -------------------------------------------------------------------
    # Identity (set once at initialisation, never mutated)
    # -------------------------------------------------------------------
    id: str  # Unique runtime identifier e.g. "Blue_1", "Red_2"

    # Blueprint - the immutable validated config loaded from YAML/UI
    blueprint: PlatformConfig

    # -------------------------------------------------------------------
    # Mutable per-replication runtime state
    # -------------------------------------------------------------------
    pos: Waypoint  # Current position of the platform
    movement_runtime: MovementStrategy  # Encapsulates movement algorithm
    movement_state: MovementState  # Per-replication mutable algorithm state
    wp_properties: WpProperties  # Properties of the current waypoint leg

    # Per-sensor evaluation history keyed by id(sensor) e.g. id(sensor): SensorRuntimeState
    sensor_states: dict[int, SensorRuntimeState] = field(default_factory=dict)
    neutralized: bool = False

    # -------------------------------------------------------------------
    # Non changeable attributes (add setters if change is required)
    # -------------------------------------------------------------------

    @property
    def neutralised(self) -> bool:
        """Alias for neutralized (British English)."""
        return self.neutralized

    @neutralised.setter
    def neutralised(self, value: bool) -> None:
        self.neutralized = value

    @property
    def team(self):
        """Team this platform belongs to (delegates to blueprint)."""
        return self.blueprint.team

    @property
    def display_name(self) -> str:
        """Human-readable name for display (delegates to blueprint)."""
        return self.blueprint.display_name

    @property
    def speed_mps(self) -> float:
        """Platform speed in metres per second (delegates to blueprint)."""
        return self.blueprint.speed_mps

    @property
    def movement_type(self):
        """Static movement configuration (delegates to blueprint)."""
        return self.blueprint.movement_type

    @property
    def sensors(self):
        """Sensor configs fitted to this platform (delegates to blueprint)."""
        return self.blueprint.sensors

    # -------------------------------------------------------------------
    # Simulation stepping
    # -------------------------------------------------------------------

    def advance_step(
        self,
        sim_time_sec: float,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> bool:
        """
        Advance platform position by one timestep.

        If the platform has reached its expected waypoint arrival time, requests a new
        waypoint from its movement strategy and recalculates waypoint kinematics.

        Returns:
            bool: True if a new waypoint was generated on this tick, False otherwise.
        """
        if self.speed_mps == 0.0:
            return False

        if self.neutralized and getattr(self.blueprint, "neutralised_platform_behaviour", "stop") == "stop":
            return False

        waypoint_generated = False
        if self.wp_properties.arrival_time <= sim_time_sec:
            new_wp: Waypoint = self.movement_runtime.get_next_waypoint(
                config=self.movement_type,
                state=self.movement_state,
                config_data=config_data,
                random_gen=random_gen,
            )
            self.wp_properties = calculate_wp_properties(
                current_pos=self.pos,
                wp=new_wp,
                speed_mps=self.speed_mps,
                timestep_sec=config_data.simulation.timestep_sec,
                sim_time=sim_time_sec,
            )
            waypoint_generated = True

        # Advance position along heading
        self.pos = Waypoint(
            x=self.pos.x + (self.wp_properties.heading[0] * self.wp_properties.step_distance),
            y=self.pos.y + (self.wp_properties.heading[1] * self.wp_properties.step_distance),
        )
        self.wp_properties.distance = max(0.0, self.wp_properties.distance - self.wp_properties.step_distance)
        return waypoint_generated

    # -------------------------------------------------------------------
    # Alternative constructor (classmethod factory)
    # -------------------------------------------------------------------

    @classmethod
    def from_blueprint(
        cls,
        platform_id: str,
        blueprint: PlatformConfig,
        initial_pos: Waypoint,
        wp_properties: WpProperties,
        movement_runtime: Optional[MovementStrategy] = None,
        movement_state: Optional[MovementState] = None,
    ) -> PlatformState:
        """
        Convert a ``PlatformConfig`` blueprint into a fully-initialised
        ``PlatformState`` for one replication.
        """
        if movement_runtime is None:
            movement_runtime = create_movement_strategy(blueprint.movement_type)
        if movement_state is None:
            movement_state = create_movement_state(blueprint.movement_type)

        return cls(
            id=platform_id,
            blueprint=blueprint,
            pos=initial_pos,
            movement_runtime=movement_runtime,
            movement_state=movement_state,
            wp_properties=wp_properties,
        )


def assign_platform_ids(platforms: list[PlatformConfig]) -> list[str]:
    """Deterministically assign runtime platform ids (Blue_1, Blue_2, Red_1, ...) in config order."""
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
) -> list[PlatformState]:
    """
    Initialise the states of all platforms for a single replication in the Monte Carlo simulation.

    Args:
        config_data: The configuration data for the simulation.
        random_gen: A random number generator for reproducibility.

    Returns:
        A list representing the initial states of all platforms.
    """
    all_platforms: list[PlatformConfig] = config_data.platforms
    platform_ids = assign_platform_ids(all_platforms)

    all_platform_states: list[PlatformState] = []

    for platform_id, p in zip(platform_ids, all_platforms):
        strategy = create_movement_strategy(p.movement_type)
        movement_state = create_movement_state(p.movement_type)

        # Static platform - generate initial position, no waypoint leg needed
        if p.speed_mps == 0.0:
            initial_pos: Waypoint = strategy.get_next_waypoint(
                p.movement_type, movement_state, config_data, random_gen
            )
            wp_properties = WpProperties(
                pos=initial_pos,
                arrival_time=0.0,
                distance=0.0,
                heading=np.array([0.0, 0.0]),
                total_duration=0.0,
                step_distance=0.0,
            )
            all_platform_states.append(
                PlatformState.from_blueprint(
                    platform_id=platform_id,
                    blueprint=p,
                    initial_pos=initial_pos,
                    wp_properties=wp_properties,
                    movement_runtime=strategy,
                    movement_state=movement_state,
                )
            )
            continue

        # Moving platform - generate initial spawn position and first target waypoint
        initial_pos = strategy.get_next_waypoint(
            p.movement_type, movement_state, config_data, random_gen
        )
        next_wp: Waypoint = strategy.get_next_waypoint(
            p.movement_type, movement_state, config_data, random_gen
        )
        assert initial_pos.x != next_wp.x or initial_pos.y != next_wp.y, (
            f"Current position ({initial_pos.x}, {initial_pos.y}) and next position "
            f"({next_wp.x}, {next_wp.y}) must not be the same."
        )

        wp_properties = calculate_wp_properties(
            current_pos=initial_pos,
            wp=next_wp,
            speed_mps=p.speed_mps,
            timestep_sec=config_data.simulation.timestep_sec,
            sim_time=0.0,
        )

        all_platform_states.append(
            PlatformState.from_blueprint(
                platform_id=platform_id,
                blueprint=p,
                initial_pos=initial_pos,
                wp_properties=wp_properties,
                movement_runtime=strategy,
                movement_state=movement_state,
            )
        )

    return all_platform_states
