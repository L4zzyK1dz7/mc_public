"""Tracks per-replication detection outcomes for every sensor-target pair.

Unlike OutcomePositionManager (sparse, event-driven position snapshots), this
manager seeds a complete, always-populated row for every (platform, sensor,
target) combination up front, then flips rows to detected as the simulation
proceeds - so summary statistics can report both detections and non-detections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.monte_carlo.detection_pipeline.pairs import iter_platform_sensors

if TYPE_CHECKING:
    from typing import Any, Sequence

    from src.monte_carlo.detection_pipeline.events import DetectionEvent
    from src.monte_carlo.sonobuoy.events import SonobuoyDetectionEvent
    from src.monte_carlo.states.platform_states import PlatformState
    from src.schemas.output import DetectionOutcomeEvent
    from src.schemas.sonobuoy import SonobuoyConfig



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

    def seed_pairs(
        self,
        platform_states: list[PlatformState],
        sonobuoys: Optional[Sequence[SonobuoyConfig]] = None,
    ) -> None:
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
                    "end_condition": None,
                }

        if sonobuoys:
            red_targets = [
                p
                for p in platform_states
                if (p.team.value if hasattr(p.team, "value") else str(p.team)) == "Red"
            ]
            self.seed_sonobuoys(sonobuoys, red_targets)

    def seed_sonobuoys(
        self,
        sonobuoys: Sequence[SonobuoyConfig],
        target_platforms: Sequence[Any],
    ) -> None:
        """Create default 'not detected' rows for sonobuoy field and participating buoys.

        Seeds:
        - ("sonobuoy_field", "single_cycle", target_id) if any buoy participates in single_cycle
        - ("sonobuoy_field", "multi", target_id) if any buoy participates in multi
        - (buoy.display_name, "single", target_id) for each buoy participating in single
        """
        if not sonobuoys or not target_platforms:
            return

        has_single_cycle = any("single_cycle" in b.evaluation_modes for b in sonobuoys)
        has_multi = any("multi" in b.evaluation_modes for b in sonobuoys)
        single_buoys = [b for b in sonobuoys if "single" in b.evaluation_modes]

        for target in target_platforms:
            target_id = getattr(target, "id", str(target))
            if has_single_cycle:
                key = ("sonobuoy_field", "single_cycle", target_id)
                self._rows[key] = {
                    "replication_id": self.replication_id,
                    "detecting_platform_id": "sonobuoy_field",
                    "sensor_name": "single_cycle",
                    "target_platform_id": target_id,
                    "detection_outcome": False,
                    "detection_distance_m": None,
                    "detection_timestamp_sec": None,
                    "end_condition": None,
                }
            if has_multi:
                key = ("sonobuoy_field", "multi", target_id)
                self._rows[key] = {
                    "replication_id": self.replication_id,
                    "detecting_platform_id": "sonobuoy_field",
                    "sensor_name": "multi",
                    "target_platform_id": target_id,
                    "detection_outcome": False,
                    "detection_distance_m": None,
                    "detection_timestamp_sec": None,
                    "end_condition": None,
                }
            for buoy in single_buoys:
                key = (buoy.display_name, "single", target_id)
                self._rows[key] = {
                    "replication_id": self.replication_id,
                    "detecting_platform_id": buoy.display_name,
                    "sensor_name": "single",
                    "target_platform_id": target_id,
                    "detection_outcome": False,
                    "detection_distance_m": None,
                    "detection_timestamp_sec": None,
                    "end_condition": None,
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
            "end_condition": None,
        }

    def record_sonobuoy_detection(
        self, event: SonobuoyDetectionEvent
    ) -> None:
        """Record a detection outcome row for a sonobuoy detection event."""
        key = (
            event.detecting_id,
            event.mode,
            event.target_platform_id,
        )
        self._rows[key] = {
            "replication_id": self.replication_id,
            "detecting_platform_id": event.detecting_id,
            "sensor_name": event.mode,
            "target_platform_id": event.target_platform_id,
            "detection_outcome": True,
            "detection_distance_m": event.distance_m,
            "detection_timestamp_sec": event.timestamp_sec,
            "end_condition": None,
        }

    def set_end_condition(self, end_condition: str) -> None:

        """Stamp every seeded row with the replication's terminal condition, so summary
        stats can show why a replication ended even when no detection occurred.
        """
        if not self._rows:
            # No sensor/target pairs were ever seeded (e.g. no sensors equipped) -
            # emit a placeholder row so the replication's end_condition is still visible.
            self._rows[("", "", "")] = {
                "replication_id": self.replication_id,
                "detecting_platform_id": "",
                "sensor_name": "",
                "target_platform_id": "",
                "detection_outcome": False,
                "detection_distance_m": None,
                "detection_timestamp_sec": None,
                "end_condition": end_condition,
            }
            return

        for row in self._rows.values():
            row["end_condition"] = end_condition
