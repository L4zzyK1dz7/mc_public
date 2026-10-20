from __future__ import annotations

import logging
from typing import Literal, Optional


from pydantic import BaseModel, Field, model_validator

from src.schemas.platform import PlatformConfig
from src.schemas.sonobuoy import SonobuoyConfig, SonobuoyFieldConfig

logger = logging.getLogger(__name__)


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
    length: float = Field(..., gt=0, description="The length of the world.")
    height: float = Field(..., gt=0, description="The height of the world.")


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
        ..., gt=0, description="The number of replications for the simulation."
    )
    time_limit_sec: float = Field(
        ..., gt=0, description="The time limit for the simulation in seconds."
    )
    timestep_sec: float = Field(
        ..., gt=0, description="The time step for the simulation world in seconds."
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
    sonobuoys: list[SonobuoyConfig] = Field(
        default_factory=list, description="List of sonobuoy receivers."
    )
    sonobuoy_field: Optional[SonobuoyFieldConfig] = Field(
        default=None, description="Field-level multistatic fusion configuration."
    )

    @model_validator(mode="after")
    def validate_config_data(self) -> ConfigData:
        world_x_min = self.world.origin_x
        world_x_max = self.world.origin_x + self.world.length
        world_y_min = self.world.origin_y
        world_y_max = self.world.origin_y + self.world.height

        names: set[str] = set()
        for buoy in self.sonobuoys:
            if buoy.display_name in names:
                raise ValueError(
                    f"Duplicate sonobuoy display name: '{buoy.display_name}'"
                )
            names.add(buoy.display_name)

            if not (
                world_x_min <= buoy.x_m <= world_x_max
                and world_y_min <= buoy.y_m <= world_y_max
            ):
                raise ValueError(
                    f"Sonobuoy '{buoy.display_name}' at ({buoy.x_m}, {buoy.y_m}) is outside world bounds "
                    f"[{world_x_min}, {world_x_max}] x [{world_y_min}, {world_y_max}]"
                )

        if self.sonobuoy_field is not None and self.sonobuoys:
            participating_buoys = [
                b
                for b in self.sonobuoys
                if any(m in b.evaluation_modes for m in ("multi", "single_cycle"))
            ]
            if self.sonobuoy_field.data_fusion_requirement > len(participating_buoys):
                logger.warning(
                    "data_fusion_requirement (%d) is greater than the number of participating buoys (%d)",
                    self.sonobuoy_field.data_fusion_requirement,
                    len(participating_buoys),
                )
        return self

    @classmethod
    def from_dict(cls, data: dict) -> ConfigData:
        """
        Create a ConfigData instance from a dictionary.

        Args:
            data: Dictionary containing the configuration data.

        Returns:
            ConfigData instance.
        """
        raw_sonobuoys = data.get("sonobuoys", [])
        sonobuoys = [
            b if isinstance(b, SonobuoyConfig) else SonobuoyConfig(**b)
            for b in raw_sonobuoys
        ]
        raw_field = data.get("sonobuoy_field")
        sonobuoy_field = (
            raw_field
            if isinstance(raw_field, SonobuoyFieldConfig)
            else (SonobuoyFieldConfig(**raw_field) if raw_field else None)
        )
        return cls(
            simulation=SimulationConfig(**data.get("simulation", {})),
            world=World(**data.get("world", {})),
            platforms=[
                p if isinstance(p, PlatformConfig) else PlatformConfig(**p)
                for p in data.get("platforms", [])
            ],
            sonobuoys=sonobuoys,
            sonobuoy_field=sonobuoy_field,
        )

