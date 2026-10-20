"""Active ping emission for multistatic acoustic detection.

Active source sensors mounted on Blue platforms emit acoustic pings at regular
intervals. Sonobuoy receivers listen for these pings to detect targets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.monte_carlo.states.platform_states import PlatformState


@dataclass(frozen=True)
class ActivePing:
    """An active ping emitted by an active source sensor."""

    source_platform_id: str
    sensor_name: str
    source_x: float
    source_y: float
    timestamp_sec: float


def collect_active_pings(
    platform_states: list[PlatformState],
    current_time_sec: float,
) -> list[ActivePing]:
    """Collect active pings emitted at the current timestep from all eligible platforms.

    Only Blue platforms with sensors marked active_source=True emit pings. Pings are
    omnidirectional and independent of the sensor's own receiver evaluation.

    Args:
        platform_states: Current runtime platform states.
        current_time_sec: Current simulation time in seconds.

    Returns:
        A list of ActivePing instances emitted during this timestep.
    """
    pings: list[ActivePing] = []

    for platform in platform_states:
        team_str = (
            platform.team.value
            if hasattr(platform.team, "value")
            else str(platform.team)
        )
        if team_str != "Blue":
            continue

        if not hasattr(platform, "ping_states") or platform.ping_states is None:
            platform.ping_states = {}

        for sensor in platform.sensors:
            if not getattr(sensor, "active_source", False):
                continue

            sensor_id = id(sensor)
            next_ping_time = platform.ping_states.get(sensor_id, 0.0)

            if current_time_sec >= next_ping_time:
                pings.append(
                    ActivePing(
                        source_platform_id=platform.id,
                        sensor_name=sensor.display_name,
                        source_x=float(platform.pos.x),
                        source_y=float(platform.pos.y),
                        timestamp_sec=float(current_time_sec),
                    )
                )
                interval = float(getattr(sensor, "interval_time_sec", 1.0))
                platform.ping_states[sensor_id] = current_time_sec + interval

    return pings
