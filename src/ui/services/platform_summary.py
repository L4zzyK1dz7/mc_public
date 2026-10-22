"""
Platform and sonobuoy summary services.

Pure data transformations for generating UI summary DataFrames without Streamlit dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from src.schemas.platform import PlatformConfig
    from src.schemas.sonobuoy import SonobuoyConfig

MOVEMENT_LABEL_MAP: dict[str, str] = {
    "random_walk": "Random Walk",
    "intruder_search": "Intruder Search",
    "barrier_patrol": "Barrier Patroller",
    "user_defined_waypoints": "User Defined Waypoints",
}


def build_platform_summary(platforms: list[Any]) -> pd.DataFrame:
    """
    Build a summary DataFrame for configured platforms.

    Columns: Name, Team, Speed (m/s), Movement, Sensors.
    """
    if not platforms:
        return pd.DataFrame(
            columns=["Name", "Team", "Speed (m/s)", "Movement", "Sensors"]
        )

    rows = []
    for platform in platforms:
        # Extract team label
        team = getattr(platform, "team", "")
        team_label = team.value if hasattr(team, "value") else str(team)

        # Extract movement label
        movement = getattr(platform, "movement_type", None)
        if movement is not None:
            raw_type = getattr(movement, "type", None) or (
                movement.get("type") if isinstance(movement, dict) else str(movement)
            )
            movement_label = MOVEMENT_LABEL_MAP.get(str(raw_type), str(raw_type))
        else:
            movement_label = "None"

        # Extract sensor display names
        sensors = getattr(platform, "sensors", []) or []
        sensor_names = [
            getattr(s, "display_name", "") or getattr(s, "name", "")
            for s in sensors
        ]
        sensor_names = [name for name in sensor_names if name]
        sensors_label = ", ".join(sensor_names) if sensor_names else "None"

        name = getattr(platform, "display_name", "")
        speed = getattr(platform, "speed_mps", 0.0)

        rows.append(
            {
                "Name": name,
                "Team": team_label,
                "Speed (m/s)": speed,
                "Movement": movement_label,
                "Sensors": sensors_label,
            }
        )

    return pd.DataFrame(rows)


def build_sonobuoy_summary(buoys: list[Any]) -> pd.DataFrame:
    """Build summary dataframe of configured sonobuoys."""
    if not buoys:
        return pd.DataFrame()

    rows = []
    for idx, buoy in enumerate(buoys):
        rows.append(
            {
                "Index": idx + 1,
                "Name": buoy.display_name,
                "X (km)": buoy.x_m,
                "Y (km)": buoy.y_m,
                "K": buoy.k,
                "N": buoy.n,
                "Modes": ", ".join(buoy.evaluation_modes),
                "PoD Points": len(buoy.distance_m),
            }
        )
    return pd.DataFrame(rows)
