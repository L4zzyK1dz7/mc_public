"""Shared iteration over (platform, sensor, target_platforms) combinations.

Both `detection_pipeline.pipeline.detect` and `OutcomeDetectionManager.seed_pairs`
need the exact same "which platforms can detect which opposing platforms" logic.
Defining it once here keeps the two from silently drifting out of sync.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from src.monte_carlo.states.platform_states import PlatformState
    from src.schemas.sensor import SensorConfig


def iter_platform_sensors(
    platform_states: list[PlatformState],
) -> Iterator[tuple[PlatformState, SensorConfig, list[PlatformState]]]:
    """Yield (platform, sensor, target_platforms) for every sensor with potential targets."""
    for platform in platform_states:
        if not platform.sensors:
            continue  # No sensor fitted, nothing to evaluate for this platform

        target_platforms = [p for p in platform_states if p.team != platform.team]
        if not target_platforms:
            continue

        for sensor in platform.sensors:
            yield platform, sensor, target_platforms
