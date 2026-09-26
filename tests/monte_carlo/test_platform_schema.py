from src.schemas.platform import PlatformConfig, Team
from src.schemas.movement import RandomWalkMovement

def test_platform_schema_kinematics():
    """Test that platform config correctly validates kinematics like speed_mps."""
    config = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=15.5,
        movement_type=RandomWalkMovement(),
        neutralised_platform_behaviour="stop",
        sensors=[]
    )
    assert config.speed_mps == 15.5
    assert config.team == Team.BLUE
    assert config.movement_type is not None
