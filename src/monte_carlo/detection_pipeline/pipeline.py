"""Detection pipeline entry points.

The detection rules are intentionally left unimplemented. This module defines
the boundary that the simulation orchestrator will call once those rules exist.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.monte_carlo.detection_pipeline.events import DetectionEvent

if TYPE_CHECKING:
    from src.monte_carlo.states.platform_states import PlatformState


def detect(
    platform_states: list[PlatformState],
    current_time_sec: float,
) -> Optional[DetectionEvent]:
    """
    Detection pipeline orchestrator to determine the type of detection the platform will perform

    args:
            platform_states: List of current platform states.
            current_time_sec: The current simulation time in seconds.

    Returns:
            Optional DetectionEvent if a detection occurred, otherwise None.
    """

    # 1. Iterate all platforms
    # 2. Check if platform has a sensor. Return early if no sensor

    # 3. Determine type of sensor: [Generic, Special or Future]

    del platform_states, current_time_sec
    return None
