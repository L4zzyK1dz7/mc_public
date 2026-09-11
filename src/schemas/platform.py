from __future__ import annotations

from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field

from src.schemas.movement import (
    BarrierPatrollerMovement,
    IntruderSearchMovement,
    RandomWalkMovement,
    UserDefinedWaypointsMovement,
)
from src.schemas.sensor import SensorConfig


# ==========================
# ENUMS
# ==========================
class Team(Enum):
    """
    Represents the different platform teams in the simulation.
    """

    BLUE = "Blue"
    RED = "Red"


neutralised_platform_behaviour_options: Literal["stop", "continue"] = (
    "stop"  # Define the Simulation subsection structure
)


MovementType = Union[
    RandomWalkMovement,
    IntruderSearchMovement,
    BarrierPatrollerMovement,
    UserDefinedWaypointsMovement,
]


class PlatformConfig(BaseModel):
    """
    Represents the configuration for a platform in the simulation.

    Attributes:
        platform_config_folder (str): The folder where the platform configuration is stored. examples: blue_1 or red_1.
        display_name (str): The display name of the platform (not used for validation, purely for user readability).
        team (Union[Team, str]): The team of the platform (Blue or Red).
        speed_mps: float: The speed of the platform in meters per second.
        search_pattern (list[MovementType]): The movement type of the platform, which can be one of several predefined movement configurations.
        neutralised_platform_behaviour (str): The behaviour of the platform when neutralised, either "stop" or "continue".
        sensors (list[SensorConfig]): A list of sensors associated with the platform. Can be empty if not specified.
    """

    platform_config_folder: str
    display_name: str = Field(..., description="The display name of the platform.")
    team: Union[Team, str] = Field(
        ..., description="The team of the platform (Blue or Red)."
    )
    speed_mps: float = Field(
        ..., description="The speed of the platform in meters per second."
    )
    movement_type: MovementType = Field(
        ...,
        description="The movement type of the platform, which can be one of several predefined movement configurations.",
    )
    neutralised_platform_behaviour: str = Field(
        default=neutralised_platform_behaviour_options,
        description="The behaviour of the platform when neutralised, either 'stop' or 'continue'.",
    )
    sensors: list[SensorConfig] = Field(
        default_factory=list,
        description="A list of sensors associated with the platform. Can be empty if not specified.",
    )
