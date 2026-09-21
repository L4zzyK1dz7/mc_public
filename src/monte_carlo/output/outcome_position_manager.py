from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

from src.schemas.output import PlatformPositionEvent, PositionEventType

if TYPE_CHECKING:
    from src.monte_carlo.detection_pipeline.events import DetectionEvent
    from src.monte_carlo.states.platform_states import PlatformState


class OutcomePositionManager:
    """Collect platform position snapshots for one simulation replication."""

    def __init__(self, replication_id: int) -> None:
        self.replication_id = replication_id
        self._events: list[PlatformPositionEvent] = []

    @property
    def events(self) -> list[PlatformPositionEvent]:
        """Return a copy of the captured events."""

        return list(self._events)

    def record_initial_positions(
        self,
        platform_states: list[PlatformState],
        timestamp: float = 0.0,
    ) -> None:
        """Capture the initial state of every platform in the replication."""

        for platform in platform_states:
            self._record_platform_event(
                event_type="initial_position",
                platform=platform,
                timestamp=timestamp,
            )

    def record_waypoint_generated(
        self,
        platform: PlatformState,
        timestamp: float,
    ) -> None:
        """Capture a platform after its new waypoint has been assigned."""

        self._record_platform_event(
            event_type="waypoint_generated",
            platform=platform,
            timestamp=timestamp,
        )

    def record_detection(
        self,
        platform: PlatformState,
        timestamp: float,
        target_platform_id: str,
        sensor_name: str,
        distance_m: float,
    ) -> None:
        """Capture the detecting platform and its detection metadata."""

        self._record_platform_event(
            event_type="detection",
            platform=platform,
            timestamp=timestamp,
            detecting_platform_id=platform.id,
            target_platform_id=target_platform_id,
            detection_made=True,
            detection_sensor_name=sensor_name,
            detection_distance_m=distance_m,
        )

    def record_detection_snapshot(
        self,
        platform_states: list[PlatformState],
        detection: DetectionEvent,
        timestamp: float,
    ) -> None:
        """Capture a full-platform snapshot at the instant a detection is reported.

        The raw position history expects one row per platform per timestep, with the
        detecting platform annotated with the detection metadata and the remaining
        platforms left as non-detecting snapshots.
        """

        for platform in platform_states:
            is_detecting_platform = platform.id == detection.detecting_platform_id
            self._record_platform_event(
                event_type="detection",
                platform=platform,
                timestamp=timestamp,
                detecting_platform_id=(platform.id if is_detecting_platform else None),
                target_platform_id=(
                    detection.target_platform_id if is_detecting_platform else None
                ),
                detection_made=is_detecting_platform,
                detection_sensor_name=(
                    detection.sensor_name if is_detecting_platform else None
                ),
                detection_distance_m=(
                    detection.distance_m if is_detecting_platform else None
                ),
            )

    def record_time_limit(
        self,
        platform_states: list[PlatformState],
        timestamp: float,
    ) -> None:
        """Capture the final state of every platform at the time limit."""

        for platform in platform_states:
            self._record_platform_event(
                event_type="time_limit",
                platform=platform,
                timestamp=timestamp,
            )

    def _record_platform_event(
        self,
        event_type: PositionEventType,
        platform: PlatformState,
        timestamp: float,
        detecting_platform_id: Optional[str] = None,
        target_platform_id: Optional[str] = None,
        detection_made: bool = False,
        detection_sensor_name: Optional[str] = None,
        detection_distance_m: Optional[float] = None,
    ) -> None:
        heading_vector = platform.wp_properties.heading
        heading = math.degrees(math.atan2(heading_vector[1], heading_vector[0])) % 360

        self._events.append(
            PlatformPositionEvent(
                replication_id=self.replication_id,
                event_type=event_type,
                platform_id=platform.id,
                team=str(platform.team),
                timestamp=timestamp,
                pos_x=platform.pos.x,
                pos_y=platform.pos.y,
                heading=heading,
                speed=platform.speed_mps,
                waypoint_x=platform.wp_properties.pos.x,
                waypoint_y=platform.wp_properties.pos.y,
                status="active",
                detecting_platform_id=detecting_platform_id,
                target_platform_id=target_platform_id,
                detection_made=detection_made,
                detection_sensor_name=detection_sensor_name,
                detection_distance_m=detection_distance_m,
            )
        )
