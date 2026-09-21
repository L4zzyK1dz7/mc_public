from __future__ import annotations

from typing import Literal, Optional, TypedDict

PositionEventType = Literal[
    "initial_position",
    "waypoint_generated",
    "detection",
    "time_limit",
]


class PlatformPositionEvent(TypedDict):
    """Immutable snapshot of a platform state captured during a replication."""

    replication_id: int
    event_type: PositionEventType
    platform_id: str
    team: str
    timestamp: float
    pos_x: float
    pos_y: float
    heading: float
    speed: float
    waypoint_x: float
    waypoint_y: float
    status: str
    detecting_platform_id: Optional[str]
    target_platform_id: Optional[str]
    detection_made: bool
    detection_sensor_name: Optional[str]
    detection_distance_m: Optional[float]


class DetectionOutcomeEvent(TypedDict):
    """Outcome of one (detecting_platform, sensor, target_platform) pair for one replication.

    Unlike PlatformPositionEvent (sparse, event-driven), exactly one row exists
    per pair per replication regardless of whether a detection occurred.
    """

    replication_id: int
    detecting_platform_id: str
    sensor_name: str
    target_platform_id: str
    detection_outcome: bool
    detection_distance_m: Optional[float]
    detection_timestamp_sec: Optional[float]


class SimulationResult(TypedDict):
    """Outcome and captured position events for one replication."""

    result: Literal["detected", "not_detected"]
    end_condition: Literal[
        "time_limit",
        "target_escaped",
        "barrier_crossed",
        "world_crossed",
        "detection",
        "counter_detection",
        "blue_team_detection",
        "red_team_detection",
    ]
    platform_position_events: list[PlatformPositionEvent]
    detection_outcomes: list[DetectionOutcomeEvent]


SimulationResults = list[dict[int, SimulationResult]]
