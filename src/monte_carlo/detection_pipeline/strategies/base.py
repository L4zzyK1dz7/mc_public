"""Abstract contract for sensor-type-specific detection algorithms (Strategy pattern).

Each sensor `type` (generic, specific, future...) gets its own concrete strategy.
`detection_pipeline.pipeline.detect` depends only on this abstraction, so new
sensor types can be added without modifying the orchestrator (Open/Closed Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import numpy as np

    from src.monte_carlo.detection_pipeline.events import DetectionEvent
    from src.monte_carlo.states.platform_states import PlatformState
    from src.schemas.sensor import SensorConfig


class SensorDetectionStrategy(ABC):
    """Detection algorithm for a single sensor type."""

    @abstractmethod
    def detect(
        self,
        sensor: SensorConfig,
        detecting_platform: PlatformState,
        target_platforms: list[PlatformState],
        current_time_sec: float,
        random_gen: np.random.Generator,
    ) -> Optional[DetectionEvent]:
        """
        Evaluate whether `detecting_platform`'s `sensor` detects any of `target_platforms`.

        Args:
            sensor: The sensor configuration being evaluated.
            detecting_platform: The platform state that owns the sensor.
            target_platforms: Candidate platforms (opposing team) that could be detected.
            current_time_sec: The current simulation time in seconds.
            random_gen: Random generator for stochastic PoD evaluation.

        Returns:
            A DetectionEvent if a detection occurred this timestep, otherwise None.
        """
        raise NotImplementedError
