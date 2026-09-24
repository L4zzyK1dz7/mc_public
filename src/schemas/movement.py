"""
Static movement configuration schemas for platforms. Loaded once from user
input (YAML/UI) and safely reused across every Monte Carlo replication.

Per-replication runtime state (spawn flags, current waypoint index, etc.) and
the get_next_position logic live in src/monte_carlo/states/movement_state.py,
kept separate so these config objects never carry mutable simulation state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field


@dataclass
class Waypoint:
    """
    Represents a waypoint with x and y coordinates.
    """

    x: float
    y: float


class IntruderEndCondition(Enum):
    """
    Represents the end conditions for an intruder movement type.
    """

    CROSS_WORLD = "cross_world"
    CROSS_BARRIER = "cross_barrier"


class RandomWalkMovement(BaseModel):
    """
    Represents a random walk movement configuration for a platform.
    """

    type: str = Field(
        "random_walk",
    )


class IntruderSearchMovement(BaseModel):
    """
    Represents an intruder search movement configuration for a platform.
    Attributes:
        type (str): The type of movement, which is "intruder_search" for this configuration.
        start_distance_m (float): The starting distance for the intruder search. Must be non-negative.
        end_condition (IntruderEndCondition): The end condition for the intruder search, which can be either CROSS_BARRIER or CROSS_WORLD.
    """

    type: str = Field(
        "intruder_search",
    )
    start_distance_m: float = Field(
        default=0, description="The starting distance for the intruder search.", ge=0
    )
    end_condition: IntruderEndCondition = Field(
        default=IntruderEndCondition.CROSS_WORLD,
        description="The end condition for the intruder search.",
    )


class BarrierPatrollerMovement(BaseModel):
    """
    Represents a barrier patroller movement configuration for a platform.
    """

    type: str = Field("barrier_patrol")
    start_x_pos: float = Field(
        default=0,
        description="The starting X position for the barrier patroller.",
        ge=0,
    )
    start_y_pos: float = Field(
        default=0,
        description="The starting Y position for the barrier patroller.",
        ge=0,
    )
    length: float = Field(..., description="The length of the barrier to patrol.", ge=0)
    height: float = Field(..., description="The height of the barrier to patrol.", ge=0)


class UserDefinedWaypointsMovement(BaseModel):
    """
    Represents a user-defined waypoints movement configuration for a platform.
    Attributes:
        type (str): The type of movement, which is "user_defined_waypoints" for this configuration.
        waypoints (list[Waypoint]): A list of waypoints representing the user-defined path. Each waypoint is an instance of the Waypoint class.
    """

    type: str = Field("user_defined_waypoints")
    waypoints: list[Waypoint] = Field(
        default_factory=list,
        description="A list of waypoints representing the user-defined path.",
    )
