from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.schemas.error_handling import human_readable_errors


class SensorConfig(BaseModel):
    """
    Represents the configuration for a sensor in the simulation.

    Attributes:
        display_name (str): The display name of the sensor (not used for validation, purely for user readability).
        x_values (list[float]): The x-values associated with the sensor.
        pod (list[float]): The pod values associated with the sensor.
        sensor_type (str): The type of the sensor.
        k (int): An integer parameter associated with the sensor.
        n (int): An integer parameter associated with the sensor.
    """

    display_name: str = Field(..., description="The display name of the sensor.")
    interval_time_sec: float = Field(
        ..., description="The interval time of the sensor in seconds."
    )
    x_values: list[float] = Field(
        default_factory=list, description="The x-values associated with the sensor."
    )
    pod: list[float] = Field(
        default_factory=list, description="The pod values associated with the sensor."
    )
    type: str = Field(..., description="The type of the sensor.")
    k: int = Field(gt=0, description="An integer parameter associated with the sensor.")
    n: int = Field(gt=0, description="An integer parameter associated with the sensor.")


class GenericSensorConfig(SensorConfig):
    """
    Represents the configuration for a generic sensor in the simulation.
    Inherits from SensorConfig and adds additional attributes specific to generic sensors.

    Attributes:
        fov_start_angle (float): The starting angle of the field of view for the generic sensor.
        fov_end_angle (float): The ending angle of the field of view for the generic sensor.
    """

    type: str = Field("generic")
    fov_start_angle: float = Field(
        ge=0.0,
        le=360.0,
        default=0.0,
        description="The starting angle of the field of view.",
    )
    fov_end_angle: float = Field(
        ge=0.0,
        le=360.0,
        default=360.0,
        description="The ending angle of the field of view.",
    )


class SpecificSensorConfig(SensorConfig):
    """
    Represents the configuration for a specific sensor in the simulation.
    Inherits from SensorConfig and adds additional attributes specific to specific sensors.
    """

    model_config = ConfigDict(extra="ignore")

    type: str = Field("specific")


class SensorFactory:
    _sensor_map = {
        "generic": GenericSensorConfig,
        "specific": SpecificSensorConfig,
    }

    @classmethod
    def create_sensor(cls, **kwargs) -> tuple[Optional[SensorConfig], list[str]]:
        """
        Create a sensor configuration based on the provided keyword arguments.

        Returns:
            tuple[Optional[SensorConfig], list[str]]: A tuple containing the created sensor configuration (or None if creation failed) and a list of error messages (empty list if successful).
        """
        sensor_type = kwargs.get("sensor_type", "")
        sensor_class = cls._sensor_map.get(sensor_type)

        try:
            return sensor_class(**kwargs), []

        except ValidationError as e:
            print(human_readable_errors(e))

            return None, human_readable_errors(e)
