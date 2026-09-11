from pydantic import BaseModel, ConfigDict, Field


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
    x_values: list[float] = Field(
        default_factory=list, description="The x-values associated with the sensor."
    )
    pod: list[float] = Field(
        default_factory=list, description="The pod values associated with the sensor."
    )
    sensor_type: str = Field(..., description="The type of the sensor.")
    k: int = Field(..., description="An integer parameter associated with the sensor.")
    n: int = Field(..., description="An integer parameter associated with the sensor.")


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
        default=0.0, description="The starting angle of the field of view."
    )
    fov_end_angle: float = Field(
        default=360.0, description="The ending angle of the field of view."
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
    def create_sensor(cls, **kwargs) -> SensorConfig:
        # sensor_class = cls._sensor_map.get(sensor_type)
        sensor_type = kwargs.get("sensor_type", "")
        sensor_class = cls._sensor_map.get(sensor_type)

        if not sensor_class:
            raise ValueError(f"Unknown sensor type: {sensor_type}")

        return sensor_class(**kwargs)
