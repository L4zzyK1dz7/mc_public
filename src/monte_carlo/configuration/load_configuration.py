"""
YAML configuration loader module.

This module provides functionality to load and validate YAML configuration files
against the SimulationConfig attrs model.
"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from src.monte_carlo.configuration.sensor_loader import resolve_platform_sensors
from src.schemas.error_handling import human_readable_errors
from src.schemas.simulation import ConfigData


def load_config_from_yaml(yaml_path: Path) -> ConfigData:
    """
    Load and validate a YAML configuration file.

    This function reads a YAML file, parses it, and validates the content
    against the ConfigData Pydantic model. All values are expected to be
    in SI base units (meters, seconds, m/s).

    Args:
        yaml_path: Path to the YAML configuration file.

    Returns:
        A validated SimulationConfig instance.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        yaml.YAMLError: If the YAML syntax is invalid.
        ValueError: If the configuration fails attrs validation.

    """
    # Convert to Path object if string is passed
    yaml_path = Path(yaml_path)

    # Check if file exists
    if not yaml_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

    # Read and parse YAML file
    with open(yaml_path, "r", encoding="utf-8") as f:
        try:
            raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML syntax in {yaml_path}: {e}") from e

    # Resolve each platform's sensor type names (e.g. "generic") into full SensorConfig
    # objects by reading their CSV files, before pydantic ever sees a bare string.
    platforms = raw_config.get("platforms", [])
    for platform in platforms:
        platform["sensors"] = resolve_platform_sensors(platform, yaml_path.parent)

    # Construct ConfigData from the parsed YAML
    # The YAML structure has nested keys: simulation, world, agents
    # Flatten these into top-level keys for attrs validation
    config_dict = {
        "simulation": raw_config.get("simulation", {}),
        "world": raw_config.get("world", {}),
        "platforms": platforms,
    }

    # Validate and return the configuration
    try:
        config_data = ConfigData.from_dict(config_dict)
    except ValidationError as e:
        readable_errors = "\n".join(human_readable_errors(e))
        raise ValueError(
            f"Invalid configuration in {yaml_path}:\n{readable_errors}"
        ) from e

    return config_data


def load_seeds(seeds_path: Path, replications: int) -> dict:
    """
    Load seed values from a YAML file.

    Args:
        seeds_path: Path to the YAML file containing seed values.
        replications: Number of replications for which seeds are required.

    Returns:
        A dictionary of seed values.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        yaml.YAMLError: If the YAML syntax is invalid.
    """
    seeds_path = Path(seeds_path)
    if not seeds_path.exists():
        raise FileNotFoundError(f"Seed file not found: {seeds_path}")

    # Initialize a list to store the loaded seeds
    loaded_seeds = []

    with open(seeds_path, "r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            try:
                loaded_seeds.append(int(line))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid seed value on line {line_number} in {seeds_path}: '{line}'"
                ) from exc

    # Check for duplicate seeds
    if len(loaded_seeds) != len(set(loaded_seeds)):
        raise ValueError(f"Duplicate seed values found in {seeds_path}")

    # Check seeds equal to number of replications
    if len(loaded_seeds) < replications:
        raise ValueError(
            f"Number of seed values ({len(loaded_seeds)}) does not match the number of replications ({replications}) in {seeds_path}"
        )

    return {"seeds": loaded_seeds}
