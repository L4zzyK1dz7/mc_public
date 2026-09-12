from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from src.schemas.simulation import ConfigData

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_config_yaml(cfg_data: ConfigData) -> dict:
    """
    Create YAML file from CFG data

    Args:
        cfg_data (ConfigData): The configuration data to be converted to YAML.

    Returns:
        dict: The dictionary representation of the configuration data.
    """
    if not cfg_data.simulation or not cfg_data.world or not cfg_data.platforms:
        raise ValueError(
            "Incomplete configuration data. Ensure simulation, world, and platforms are defined."
        )

    # Define the path to save the YAML file
    output_path = Path("input_data/config.yaml")
    output_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

    # Clear contents of the output path
    if output_path.exists():
        if output_path.is_file():
            output_path.unlink()  # Remove existing file if it exists
        else:
            shutil.rmtree(
                output_path, ignore_errors=True
            )  # Remove existing directory if it exists
    logger.info("Cleared existing configuration at: %s", output_path)

    # Convert dataclass to dictionary

    cfg_dict = cfg_data.model_dump(
        mode="json"
    )  # Use model_dump to convert Pydantic model to dict

    logger.info("Configuration dictionary created: %s", cfg_dict)

    # Write the dictionary to a YAML file
    with open(output_path, "w") as yaml_file:
        yaml.dump(cfg_dict, yaml_file, default_flow_style=False)

    return cfg_dict
