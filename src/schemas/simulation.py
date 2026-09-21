from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.platform import PlatformConfig


class World(BaseModel):
    """
    Represents the configuration for the simulation world.
    """

    origin_x: float = Field(
        default=0, description="The x-coordinate of the origin of the world."
    )
    origin_y: float = Field(
        default=0, description="The y-coordinate of the origin of the world."
    )
    length: float = Field(..., description="The length of the world.")
    height: float = Field(..., description="The height of the world.")


class SimulationConfig(BaseModel):
    """
    Represents the configuration for a simulation.

    Attributes:
        replications (int): The number of replications for the simulation.
        time_limit_sec (float): The time limit for the simulation in seconds.
        world_timestep_sec (float): The time step for the simulation world in seconds.
        seeds_file (bool): Indicates whether a seeds file is used for the simulation.
        detection_end_condition (str): The end condition for detection in the simulation. Default is "initial_detection".
    """

    replications: int = Field(
        ..., description="The number of replications for the simulation."
    )
    time_limit_sec: float = Field(
        ..., description="The time limit for the simulation in seconds."
    )
    timestep_sec: float = Field(
        ..., description="The time step for the simulation world in seconds."
    )
    seeds_file: bool = Field(
        ..., description="Indicates whether a seeds file is used for the simulation."
    )
    detection_end_condition: Literal["initial_detection", "team_detection"] = Field(
        default="initial_detection",
        description="The end condition for detection in the simulation.",
    )


class ConfigData(BaseModel):
    """
    Represents the configuration data for the simulation to convert into a Yaml file.
    """

    simulation: SimulationConfig
    world: World
    platforms: list[PlatformConfig] = Field(
        default_factory=list, description="List of PlatformConfig instances."
    )

    @classmethod
    def from_dict(cls, data: dict) -> ConfigData:
        """
        Create a ConfigData instance from a dictionary.

        Args:
            data: Dictionary containing the configuration data.

        Returns:
            ConfigData instance.
        """
        return cls(
            simulation=SimulationConfig(**data.get("simulation", {})),
            world=World(**data.get("world", {})),
            platforms=[PlatformConfig(**p) for p in data.get("platforms", [])],
        )
