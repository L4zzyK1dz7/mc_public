from __future__ import annotations

import pandas as pd

from src.schemas.movement import (
    BarrierPatrollerMovement,
    IntruderSearchMovement,
    RandomWalkMovement,
    UserDefinedWaypointsMovement,
    Waypoint,
)
from src.schemas.platform import PlatformConfig, Team
from src.schemas.sensor import GenericSensorConfig
from src.schemas.sonobuoy import SonobuoyConfig
from src.ui.services.platform_summary import (
    build_platform_summary,
    build_sonobuoy_summary,
)


def test_build_platform_summary_empty():
    df = build_platform_summary([])
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    assert list(df.columns) == ["Name", "Team", "Speed (m/s)", "Movement", "Sensors"]


def test_build_platform_summary_populated():
    sensor_1 = GenericSensorConfig(
        display_name="Radar_A",
        interval_time_sec=1.0,
        x_values=[0.0, 1000.0],
        pod=[1.0, 0.5],
        k=1,
        n=1,
    )
    sensor_2 = GenericSensorConfig(
        display_name="Sonar_B",
        interval_time_sec=1.0,
        x_values=[0.0, 1000.0],
        pod=[1.0, 0.5],
        k=1,
        n=1,
    )

    p1 = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Hunter",
        team=Team.BLUE,
        speed_mps=12.5,
        neutralised_platform_behaviour="stop",
        movement_type=BarrierPatrollerMovement(
            pattern="barrier_patrol",
            start_x_pos=0.0,
            start_y_pos=100.0,
            length=500.0,
            height=200.0,
        ),
        sensors=[sensor_1, sensor_2],
    )

    p2 = PlatformConfig(
        platform_config_folder="red_1",
        display_name="Target",
        team="Red",
        speed_mps=5.0,
        neutralised_platform_behaviour="stop",
        movement_type=RandomWalkMovement(pattern="random_walk"),
        sensors=[],
    )

    p3 = PlatformConfig(
        platform_config_folder="blue_2",
        display_name="Searcher",
        team="Blue",
        speed_mps=8.0,
        neutralised_platform_behaviour="stop",
        movement_type=IntruderSearchMovement(pattern="intruder_search"),
        sensors=[],
    )

    p4 = PlatformConfig(
        platform_config_folder="blue_3",
        display_name="Waypointer",
        team=Team.BLUE,
        speed_mps=7.0,
        neutralised_platform_behaviour="stop",
        movement_type=UserDefinedWaypointsMovement(
            pattern="user_defined_waypoints",
            waypoints=[Waypoint(x=0.0, y=0.0), Waypoint(x=10.0, y=10.0)],
        ),
        sensors=[],
    )

    df = build_platform_summary([p1, p2, p3, p4])
    assert len(df) == 4
    assert df.iloc[0]["Name"] == "Hunter"
    assert df.iloc[0]["Team"] == "Blue"
    assert df.iloc[0]["Speed (m/s)"] == 12.5
    assert df.iloc[0]["Movement"] == "Barrier Patroller"
    assert df.iloc[0]["Sensors"] == "Radar_A, Sonar_B"

    assert df.iloc[1]["Name"] == "Target"
    assert df.iloc[1]["Team"] == "Red"
    assert df.iloc[1]["Movement"] == "Random Walk"
    assert df.iloc[1]["Sensors"] == "None"

    assert df.iloc[2]["Movement"] == "Intruder Search"
    assert df.iloc[3]["Movement"] == "User Defined Waypoints"


def test_build_sonobuoy_summary_empty():
    df = build_sonobuoy_summary([])
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_build_sonobuoy_summary_populated():
    buoy = SonobuoyConfig(
        display_name="Buoy_1",
        x_m=5.0,
        y_m=10.0,
        k=2,
        n=3,
        evaluation_modes=["single_cycle", "multi"],
        distance_m=[0.0, 1000.0],
        pod=[1.0, 0.5],
    )
    df = build_sonobuoy_summary([buoy])
    assert len(df) == 1
    assert df.iloc[0]["Name"] == "Buoy_1"
    assert df.iloc[0]["X (km)"] == 5.0
    assert df.iloc[0]["Y (km)"] == 10.0
    assert df.iloc[0]["K"] == 2
    assert df.iloc[0]["N"] == 3
    assert df.iloc[0]["Modes"] == "single_cycle, multi"
    assert df.iloc[0]["PoD Points"] == 2
