from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.schemas.simulation import ConfigData


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

    def execute(self) -> None:
        """
        Execute the random walk movement.
        """
        print("Random Walking....")

    def get_next_position(
        self,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        """
        Get the next position for the random walk movement based on the current position.

        Args:
            current_pos (Waypoint): The current position of the platform.
            config_data (ConfigData): The configuration data for the simulation based on user input. This provides information about the environment in which the platform is operating.

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

    def execute(self) -> None:
        """
        Execute the intruder search movement.
        """
        print("Intruder Searching....")

    def get_next_position(
        self,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        raise NotImplementedError(
            "get_next_position method is not implemented for IntruderSearchMovement."
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

    def execute(self) -> None:
        """
        Execute the barrier patroller movement.
        """
        print("Patrolling Barrier....")

        # Check if waypoint should be updated

    def get_next_position(
        self,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        raise NotImplementedError(
            "get_next_position method is not implemented for BarrierPatrollerMovement."
        )


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

    def execute(self) -> None:
        """
        Execute the user-defined waypoints movement.
        """
        print("Following User-Defined Waypoints....")

    def get_next_position(
        self,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        raise NotImplementedError(
            "get_next_position method is not implemented for UserDefinedWaypointsMovement."
        )
