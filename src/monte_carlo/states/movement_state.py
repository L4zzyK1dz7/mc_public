"""
Per-replication runtime state for each movement type, kept separate from the
static movement config in src/schemas/movement.py so config objects loaded
once from YAML can be safely reused, unmutated, across every replication.

Also defines the MovementStrategy ABC and concrete strategy classes (Strategy
pattern), plus a MOVEMENT_REGISTRY dictionary that replaces if/elif dispatch
chains with a registry lookup (Open/Closed Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal, Optional, Type, Union

from pydantic import BaseModel, Field

from src.schemas.movement import (
    BarrierPatrollerMovement,
    IntruderSearchMovement,
    RandomWalkMovement,
    UserDefinedWaypointsMovement,
    Waypoint,
)

if TYPE_CHECKING:
    import numpy as np

    from src.schemas.platform import MovementType
    from src.schemas.simulation import ConfigData


# ==========================
# PER-REPLICATION STATE MODELS
# ==========================


class RandomWalkState(BaseModel):
    """
    Random walk requires no per-replication state, kept for a uniform state interface.
    """


class IntruderSearchState(BaseModel):
    """
    Per-replication runtime state for IntruderSearchMovement.
    """

    initial_position: bool = Field(
        default=True,
        description="Indicates whether the intruder starts at the initial position.",
    )
    initial_position_coordinates: Optional[Waypoint] = Field(
        default=None,
        description="The initial position coordinates for the intruder if it starts at the initial position.",
    )


SideReached = Literal["left", "right", None]


class BarrierPatrollerState(BaseModel):
    """
    Per-replication runtime state for BarrierPatrollerMovement.
    """

    initial_position_generated: bool = Field(
        default=False,
        description="Indicates whether the initial position for the barrier patroller has been generated.",
    )
    side_to_go: SideReached = Field(
        default=None,
        description="Indicates which side of the barrier has been reached.",
    )


class UserDefinedWaypointsState(BaseModel):
    """
    Per-replication runtime state for UserDefinedWaypointsMovement.
    """

    current_index: int = Field(
        0,
        description="To track the current waypoint, this field stores the index of the current waypoint in the user-defined waypoints list.",
    )


MovementState = Union[
    RandomWalkState,
    IntruderSearchState,
    BarrierPatrollerState,
    UserDefinedWaypointsState,
]


# ==========================
# MOVEMENT STRATEGY (ABC + CONCRETE CLASSES)
# ==========================


class MovementStrategy(ABC):
    """
    Abstract base class for movement strategies (Strategy pattern).

    Each concrete subclass encapsulates the waypoint-generation algorithm for
    a single movement config type plus its matching per-replication state.
    Adding a new movement type only requires a new subclass + a registry entry;
    nothing else in the codebase needs to change (Open/Closed Principle).
    """

    @abstractmethod
    def get_next_waypoint(
        self,
        config: MovementType,
        state: MovementState,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        """
        Return the next waypoint for this movement algorithm.

        Args:
            config: The static movement configuration (loaded from YAML, never mutated).
            state: Per-replication mutable runtime state for this movement type.
            config_data: Global simulation configuration (world bounds, timestep, etc.).
            random_gen: Seeded random generator for stochastic behaviour.

        Returns:
            Waypoint: The next target position for the platform.
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def create_state() -> MovementState:
        """Return a fresh, zeroed per-replication runtime state for this strategy."""
        raise NotImplementedError


class RandomWalkStrategy(MovementStrategy):
    """Movement strategy for RandomWalkMovement."""

    def get_next_waypoint(
        self,
        config: RandomWalkMovement,
        state: RandomWalkState,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        return _random_walk_next_position(config, state, config_data, random_gen)

    @staticmethod
    def create_state() -> RandomWalkState:
        return RandomWalkState()


class IntruderSearchStrategy(MovementStrategy):
    """Movement strategy for IntruderSearchMovement."""

    def get_next_waypoint(
        self,
        config: IntruderSearchMovement,
        state: IntruderSearchState,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        return _intruder_search_next_position(config, state, config_data, random_gen)

    @staticmethod
    def create_state() -> IntruderSearchState:
        return IntruderSearchState()


class BarrierPatrollerStrategy(MovementStrategy):
    """Movement strategy for BarrierPatrollerMovement."""

    def get_next_waypoint(
        self,
        config: BarrierPatrollerMovement,
        state: BarrierPatrollerState,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        return _barrier_patroller_next_position(config, state, config_data, random_gen)

    @staticmethod
    def create_state() -> BarrierPatrollerState:
        return BarrierPatrollerState()


class UserDefinedWaypointsStrategy(MovementStrategy):
    """Movement strategy for UserDefinedWaypointsMovement."""

    def get_next_waypoint(
        self,
        config: UserDefinedWaypointsMovement,
        state: UserDefinedWaypointsState,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        return _user_defined_waypoints_next_position(
            config, state, config_data, random_gen
        )

    @staticmethod
    def create_state() -> UserDefinedWaypointsState:
        return UserDefinedWaypointsState()


# ==========================
# MOVEMENT REGISTRY
# ==========================

# Registry pattern: maps movement config `type` string -> strategy class.
# Adding a new movement type only requires registering it here.
MOVEMENT_REGISTRY: dict[str, Type[MovementStrategy]] = {
    "random_walk": RandomWalkStrategy,
    "intruder_search": IntruderSearchStrategy,
    "barrier_patrol": BarrierPatrollerStrategy,
    "user_defined_waypoints": UserDefinedWaypointsStrategy,
}


def create_movement_strategy(movement_type: MovementType) -> MovementStrategy:
    """
    Instantiate the MovementStrategy for the given config via the registry.

    This replaces the if/elif isinstance chain with a O(1) dict lookup.
    Raises KeyError if the movement type string is not registered.
    """
    strategy_class = MOVEMENT_REGISTRY[movement_type.type]
    return strategy_class()


def create_movement_state(movement_type: MovementType) -> MovementState:
    """
    Build a fresh runtime state instance matching the given movement config, so
    per-replication state (e.g. current waypoint index, spawn flags) never
    leaks between replications that reuse the same movement config object.

    Delegates to the registered strategy's create_state factory so the
    mapping is defined in one place (MOVEMENT_REGISTRY).
    """
    strategy_class = MOVEMENT_REGISTRY[movement_type.type]
    return strategy_class.create_state()


# ==========================
# PRIVATE POSITION CALCULATORS
# (Called by the concrete strategy classes above)
# ==========================


def _random_walk_next_position(
    movement_type: RandomWalkMovement,
    state: RandomWalkState,
    config_data: ConfigData,
    random_gen: np.random.Generator,
) -> Waypoint:
    """
    Get the next position for the random walk movement based on the current position.

    Args:
        movement_type (RandomWalkMovement): The static movement config, unused here.
        state (RandomWalkState): Unused, kept for a uniform signature across movement types.
        config_data (ConfigData): The configuration data for the simulation based on user
            input. This provides information about the environment in which the platform
            is operating.

    Returns:
        Waypoint: The next position for the platform.
    """

    world = config_data.world

    # Generate a random waypoint position bounded by the world dimensions randomly
    next_pos = Waypoint(
        x=random_gen.uniform(world.origin_x, world.origin_x + world.length),
        y=random_gen.uniform(world.origin_y, world.origin_y + world.height),
    )

    return next_pos


def _intruder_search_next_position(
    movement_type: IntruderSearchMovement,
    state: IntruderSearchState,
    config_data: ConfigData,
    random_gen: np.random.Generator,
) -> Waypoint:
    """
    Intruder starts on or just outside the world (determined by start_distance_m).
    The initial position x is random along the length of the world. The y position is
    determined by the height of the world plus start_distance_m from the top of the world.
    The waypoint represents the intruders next position positioned just outside the world.
    The intruder moves vertically downwards from its starting position to the waypoint.
    If the intruder is not detected then the end condition stops at either crossing the
    world or crossing barrier.

    args:
        movement_type (IntruderSearchMovement): The static movement config.
        state (IntruderSearchState): Per-replication runtime state for this movement.
        config_data (ConfigData): The configuration data for the simulation.
        random_gen (np.random.Generator): A random number generator for stochastic behavior.

    Returns:
        Waypoint: The next position for the intruder.
    """

    world = config_data.world

    # Spawn
    if state.initial_position:
        start_x = random_gen.uniform(world.origin_x, world.origin_x + world.length)
        start_y = world.origin_y + world.height + movement_type.start_distance_m

        next_waypoint = Waypoint(x=start_x, y=start_y)
        state.initial_position = False
        state.initial_position_coordinates = next_waypoint
        return next_waypoint

    # Bottom of the world
    if state.initial_position_coordinates is not None:
        next_waypoint = Waypoint(
            x=state.initial_position_coordinates.x,
            y=world.origin_y - 10,
        )

        return next_waypoint

    assert state.initial_position_coordinates is not None, (
        "Initial position coordinates must be set before getting the next position."
    )


def _barrier_patroller_next_position(
    movement_type: BarrierPatrollerMovement,
    state: BarrierPatrollerState,
    config_data: ConfigData,
    random_gen: np.random.Generator,
) -> Waypoint:
    """
    The barrier is positioned based on its starting X and Y positions, length, and height
    inside the world.

    The initial position is randomly placed within the barrier starting X and Y positions
    and constrained by the barrier's length and height.
    The next position will be determined by a 50/50 chance of either left or right of the
    barrier. If the barrier reaches one of the sides, the next position will be on the
    opposite side.

    args:
        movement_type (BarrierPatrollerMovement): The static movement config.
        state (BarrierPatrollerState): Per-replication runtime state for this movement.
    """

    # Generate initial position
    if not state.initial_position_generated:
        state.initial_position_generated = True
        # Generate the initial position within the barrier's starting X and Y positions
        # and constrained by the barrier's length and height
        initial_x = random_gen.uniform(
            movement_type.start_x_pos, movement_type.start_x_pos + movement_type.length
        )
        initial_y = movement_type.start_y_pos

        # Randomly determine whether the platform should move to the left or to the right side
        state.side_to_go = "left" if random_gen.random() < 0.5 else "right"

        return Waypoint(x=initial_x, y=initial_y)

    # Position the waypoint left or the right side
    left = Waypoint(
        x=movement_type.start_x_pos,
        y=movement_type.start_y_pos,
    )
    right = Waypoint(
        x=movement_type.start_x_pos + movement_type.length,
        y=movement_type.start_y_pos,
    )

    # Go the opposite side if the barrier has reached one of the sides
    if state.side_to_go is not None:
        if state.side_to_go == "left":
            state.side_to_go = "right"
        elif state.side_to_go == "right":
            state.side_to_go = "left"

    if state.side_to_go == "left":
        return left
    else:
        return right


def _user_defined_waypoints_next_position(
    movement_type: UserDefinedWaypointsMovement,
    state: UserDefinedWaypointsState,
    config_data: ConfigData,
    random_gen: np.random.Generator,
) -> Waypoint:
    """
    Waypoints is a list of Waypoint, the platform's initial position will be the first
    Waypoint in the list and will move along the subsequent waypoints.
    The cycle repeats after reaching the last waypoint, and the platform will start on
    the first waypoint again to form a pattern.

    args:
        movement_type (UserDefinedWaypointsMovement): The static movement config.
        state (UserDefinedWaypointsState): Per-replication runtime state for this movement.
    """

    # If this is the first call, return the initial waypoint without updating the index.
    waypoint = movement_type.waypoints[state.current_index]

    # Update the waypoint index to the next waypoint in the list, cycling back to the
    # first waypoint if necessary.
    state.current_index = (state.current_index + 1) % len(movement_type.waypoints)

    return waypoint


def get_next_position(
    movement_type: MovementType,
    state: MovementState,
    config_data: ConfigData,
    random_gen: np.random.Generator,
) -> Waypoint:
    """Convenience functional dispatch using MovementStrategy."""
    strategy = create_movement_strategy(movement_type)
    return strategy.get_next_waypoint(movement_type, state, config_data, random_gen)
