from __future__ import annotations

import csv
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from src.schemas.platform import PlatformConfig
    from src.schemas.sensor import SensorConfig
    from src.schemas.simulation import ConfigData

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_sensor_file(
    sensor: SensorConfig,
    platform_path: Path,
) -> bool:
    """
    Create a sensor file for the given sensor within the specified platform directory.
    The column for the table could range_m or distance_m or some other measurement depending on the sensor type.

    Example CSV file:
    # name: sensor_1
    # type: generic
    # interval_time_sec: 1.0
    # fov_start_angle: 0.0
    # fov_end_angle: 0.0
    # active_sensor: False

    range_m, pod
    0,1.0
    100,0.8
    500,0.4

    Args:
        sensor (SensorConfig): The sensor configuration.
        platform_path (Path): The path to the platform directory where the sensor file should be created.

    Returns:
        bool: True if the sensor file was successfully created, False otherwise.
    """
    sensor_file = platform_path / "sensors" / sensor.type / f"{sensor.display_name}.csv"
    try:
        sensor_dict = sensor.model_dump()
        table_fields = {"x_values", "pod"}
        x_values = sensor_dict.pop("x_values")
        pod = sensor_dict.pop("pod")

        # if generic x_values is set to range_m
        if sensor.type == "generic":
            x_values_label = "range_m"

        with open(sensor_file, "w", newline="") as f:
            # Metadata comment header for every field except the x_values/pod table
            for field_name, value in sensor_dict.items():
                if field_name not in table_fields:
                    f.write(f"# {field_name}: {value}\n")

            f.write("\n")

            writer = csv.writer(f)
            writer.writerow([x_values_label, "pod"])
            writer.writerows(zip(x_values, pod))
        return True
    except Exception as e:
        logger.error(f"Failed to create sensor file {sensor_file}: {e}")
        return False


def organise_input_data_directory(
    config_data: ConfigData,
    input_data_path: Path = Path("input_data"),
) -> list[PlatformConfig]:
    """
    Organise the input data directory. Platforms will have their own dedicated directories split between team colour

    Folder structure:
    input_data/
        - Platforms/
            - Blue/
                - blue_1
                    - sensors/
                        - generic/
                            - sensor_1.csv
                        - specific/
                    - user_defined_movements/
                        - ribbon_movement.csv
                - blue_2

            - Red
                - red_1
                - red_2
    """
    input_data_path.mkdir(parents=True, exist_ok=True)

    # Create the input data directory structure based on the configuration data
    platforms_path = input_data_path / "platforms"
    platforms_path.mkdir(parents=True, exist_ok=True)
    platforms: list[PlatformConfig] = config_data.platforms

    # Create directories for each platform based on team and display name
    for platform in platforms:
        team_path = platforms_path / str(platform.team)
        team_path.mkdir(parents=True, exist_ok=True)

        platform_path = team_path / platform.display_name
        platform_path.mkdir(parents=True, exist_ok=True)

        # Create folders derived by the sensor types
        for sensor in platform.sensors:
            (platform_path / "sensors" / sensor.type).mkdir(parents=True, exist_ok=True)
        (platform_path / "user_defined_movements").mkdir(parents=True, exist_ok=True)

        # If the platform has a sensor add the sensor files to the appropriate directories
        sensors: list[SensorConfig] = platform.sensors
        if sensors:
            for sensor in sensors:
                # Create and populate sensor file
                create_sensor_file(sensor, platform_path)

    return platforms


def generate_seeds_file(replications: int) -> None:
    """
    Generate a seeds.txt file with random seeds.
    """
    import random

    seeds_path = Path("input_data/seeds.txt")
    seeds_path.parent.mkdir(parents=True, exist_ok=True)
    with open(seeds_path, "w") as f:
        for _ in range(replications):  # Generate seeds based on replications
            f.write(f"{random.randint(0, 1000000)}\n")


def create_config_yaml(
    config_data: ConfigData, input_data_path: Path = Path("input_data")
) -> dict:
    """
    Create YAML file from CFG data. Also generate seeds.txt file if seeds_file is False

    Args:
        config_data (ConfigData): The configuration data to be converted to YAML.

    Returns:
        dict: The dictionary representation of the configuration data.
    """
    if not config_data.simulation or not config_data.world or not config_data.platforms:
        raise ValueError(
            "Incomplete configuration data. Ensure simulation, world, and platforms are defined."
        )

    # Define the path to save the YAML file
    output_path = input_data_path / "config.yaml"

    # Clear the entire input_data directory so it can be regenerated from scratch
    if input_data_path.exists():
        shutil.rmtree(input_data_path, ignore_errors=True)
    input_data_path.mkdir(parents=True, exist_ok=True)
    logger.info("Cleared existing configuration at: %s", input_data_path)

    generate_seeds_file(config_data.simulation.replications)

    # Organise input data directory
    config_data.platforms = organise_input_data_directory(config_data)
    logger.info(
        "Organised input data directory. Platforms updated. %s", config_data.platforms
    )

    # Convert to SI units
    config_data.simulation.time_limit_sec = float(
        config_data.simulation.time_limit_sec * 60 * 60
    )  # hours to seconds
    config_data.world.height = float(config_data.world.height * 1000)  # km to meters
    config_data.world.length = float(config_data.world.length * 1000)  # km to meters

    # Convert dataclass to dictionary
    cfg_dict = config_data.model_dump(
        mode="json"
    )  # Use model_dump to convert Pydantic model to dict

    logger.info("Configuration dictionary created: %s", cfg_dict)

    # remove sensor data but leave the sensor names as a list
    for platform in cfg_dict.get("platforms", []):
        if "sensors" in platform:
            platform["sensors"] = [sensor["type"] for sensor in platform["sensors"]]
            print(platform["sensors"])

    # Write the dictionary to a YAML file
    with open(output_path, "w") as yaml_file:
        yaml.dump(cfg_dict, yaml_file, default_flow_style=False)

    return cfg_dict
