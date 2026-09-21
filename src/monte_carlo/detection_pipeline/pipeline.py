"""Detection pipeline entry point.

Sensor-specific detection algorithms live behind the Strategy pattern in
`detection_pipeline.strategies`. This module only orchestrates which platforms
get a chance to detect and delegates to the strategy registered for each
sensor's type, so it never needs to change when a new sensor type is added.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.monte_carlo.detection_pipeline.events import DetectionEvent
from src.monte_carlo.detection_pipeline.pairs import iter_platform_sensors
from src.monte_carlo.detection_pipeline.strategies import get_strategy

if TYPE_CHECKING:
    import numpy as np

    from src.monte_carlo.detection_pipeline.strategies import SensorDetectionStrategy
    from src.monte_carlo.states.platform_states import PlatformState


def detect(
    platform_states: list[PlatformState],
    current_time_sec: float,
    random_gen: np.random.Generator,
) -> list[DetectionEvent]:
    """
    Detection pipeline orchestrator to determine the type of detection the platform will perform

    Every platform/sensor/target combination is evaluated exhaustively each timestep
    (no short-circuiting), so simultaneous detections by multiple sensors or against
    multiple targets are all reported rather than only the first one found.

    args:
        platform_states: List of current platform states.
        current_time_sec: The current simulation time in seconds.
        random_gen: Random generator passed to detection strategies for stochastic evaluation.

    Returns:
            A list of DetectionEvents (possibly empty) reported this timestep.
    """

    detections: list[DetectionEvent] = []

    for platform, sensor, target_platforms in iter_platform_sensors(platform_states):
        strategy: Optional[SensorDetectionStrategy] = get_strategy(sensor.type)
        if strategy is None:
            continue  # Sensor type has no detection strategy registered yet

        detections.extend(
            strategy.detect(
                sensor=sensor,
                detecting_platform=platform,
                target_platforms=target_platforms,
                current_time_sec=current_time_sec,
                random_gen=random_gen,
            )
        )

    return detections
