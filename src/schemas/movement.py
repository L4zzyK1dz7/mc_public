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

    CROSS_BARRIER = "cross_barrier"
    CROSS_WORLD = "cross_world"


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
        start_distance (float): The starting distance for the intruder search. Must be non-negative.
        end_condition (IntruderEndCondition): The end condition for the intruder search, which can be either CROSS_BARRIER or CROSS_WORLD.
    """

    type: str = Field(
        "intruder_search",
    )
    start_distance: float = Field(
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
