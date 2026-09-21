"""Tracks per-replication detection outcomes for every sensor-target pair.

Unlike OutcomePositionManager (sparse, event-driven position snapshots), this
manager seeds a complete, always-populated row for every (platform, sensor,
target) combination up front, then flips rows to detected as the simulation
proceeds - so summary statistics can report both detections and non-detections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.monte_carlo.detection_pipeline.pairs import iter_platform_sensors

if TYPE_CHECKING:
    from src.monte_carlo.detection_pipeline.events import DetectionEvent
    from src.monte_carlo.states.platform_states import PlatformState
    from src.schemas.output import DetectionOutcomeEvent


class OutcomeDetectionManager:
    """Collect one detection outcome row per (platform, sensor, target) for one replication."""

    def __init__(self, replication_id: int) -> None:
        self.replication_id = replication_id

        # Dictionary to store detection outcome rows keyed by (platform_id, sensor_name, target_platform_id)
        self._rows: dict[tuple[str, str, str], DetectionOutcomeEvent] = {}

    @property
    def rows(self) -> list[DetectionOutcomeEvent]:
        """Return the finalised detection outcome rows."""
        return list(self._rows.values())

    def seed_pairs(self, platform_states: list[PlatformState]) -> None:
        """Create a default 'not detected' row for every sensor-target combination."""
        for platform, sensor, target_platforms in iter_platform_sensors(
            platform_states
        ):
            for target in target_platforms:
                key = (platform.id, sensor.display_name, target.id)
                self._rows[key] = {
                    "replication_id": self.replication_id,
                    "detecting_platform_id": platform.id,
                    "sensor_name": sensor.display_name,
                    "target_platform_id": target.id,
                    "detection_outcome": False,
                    "detection_distance_m": None,
                    "detection_timestamp_sec": None,
                }

    def record_detection(self, detection: DetectionEvent, timestamp: float) -> None:
        """Flip the matching seeded row to a confirmed detection."""
        key = (
            detection.detecting_platform_id,
            detection.sensor_name,
            detection.target_platform_id,
        )
        self._rows[key] = {
            "replication_id": self.replication_id,
            "detecting_platform_id": detection.detecting_platform_id,
            "sensor_name": detection.sensor_name,
            "target_platform_id": detection.target_platform_id,
            "detection_outcome": True,
            "detection_distance_m": detection.distance_m,
            "detection_timestamp_sec": timestamp,
        }
