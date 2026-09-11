from pathlib import Path

import yaml

from src.schemas.movement import (
    BarrierPatrollerMovement,
    IntruderEndCondition,
    IntruderSearchMovement,
    RandomWalkMovement,
)
from src.schemas.platform import PlatformConfig
from src.schemas.simulation import ConfigData, SimulationConfig, WorldConfig
from src.ui.services.create_yaml import create_config_yaml

TEST_DIR = Path(__file__).parent
MOCK_CONFIG_PATH = TEST_DIR / "mock_config.yaml"


def test_config_matches_mock_yaml():
    """Verify that the generated config.yaml matches the mock_config.yaml."""

    simulation_config = SimulationConfig(
        replications=5,
        time_limit_sec=3600.0,
        world_timestep_sec=1.0,
        seeds_file=True,
        detection_end_condition="initial_detection",
    )
    world_config = WorldConfig(
        origin_x=0.0,
        origin_y=0.0,
        length=1000000.0,
        height=800000.0,
    )

    search_movement_blue_1 = BarrierPatrollerMovement(
        pattern="barrier_patrol",
        start_x_pos=100.0,
        start_y_pos=100.0,
        length=500.0,
        height=200.0,
    )
    search_movement_blue_2 = IntruderSearchMovement(
        pattern="intruder_search",
        start_distance=100.0,
        end_condition=IntruderEndCondition.CROSS_WORLD.value,
    )
    search_movement_red_1 = RandomWalkMovement(pattern="random_walk")

    platform1 = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Agent_1",
        team="Blue",
        speed_mps=2.7777777777777777,
        neutralised_platform_behaviour="stop",
        movement_type=search_movement_blue_1,
    )
    platform2 = PlatformConfig(
        platform_config_folder="blue_2",
        display_name="Agent_2",
        team="Blue",
        speed_mps=2.7777777777777777,
        neutralised_platform_behaviour="stop",
        movement_type=search_movement_blue_2,
    )
    platform3 = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Agent_3",
        team="Red",
        speed_mps=2.7777777777777777,
        neutralised_platform_behaviour="stop",
        movement_type=search_movement_red_1,
    )

    cfg_data = ConfigData(
        simulation=simulation_config,
        world=world_config,
        platforms=[platform1, platform2, platform3],
    )
    generated_yaml = create_config_yaml(cfg_data)

    with open(MOCK_CONFIG_PATH, "r") as mock_file:
        mock_yaml = yaml.safe_load(mock_file)

    # Assert that the generated YAML matches the mock YAML
    assert generated_yaml == mock_yaml, (
        "Generated config.yaml does not match the mock_config.yaml"
    )


# Command to run the test:
# python -m pytest -s src/tests/ui/test_create_yaml/test_create_yaml.py -vv
