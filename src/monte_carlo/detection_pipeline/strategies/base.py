"""Abstract contract for sensor-type-specific detection algorithms (Strategy pattern).

Each sensor `type` (generic, specific, future...) gets its own concrete strategy.
`detection_pipeline.pipeline.detect` depends only on this abstraction, so new
sensor types can be added without modifying the orchestrator (Open/Closed Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

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
    ) -> list[DetectionEvent]:
        """
        Evaluate `detecting_platform`'s `sensor` against every target in `target_platforms`.

        Every target must be evaluated exhaustively (no short-circuiting on the first
        hit), so that simultaneous detections in the same timestep are never missed
        and every target's k-of-n history is updated every timestep.

        Args:
            sensor: The sensor configuration being evaluated.
            detecting_platform: The platform state that owns the sensor.
            target_platforms: Candidate platforms (opposing team) that could be detected.
            current_time_sec: The current simulation time in seconds.
            random_gen: Random generator for stochastic PoD evaluation.

        Returns:
            A list of DetectionEvents (possibly empty) for this timestep.
        """
        raise NotImplementedError
