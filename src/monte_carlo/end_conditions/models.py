"""Data contracts used by terminal-condition evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from src.monte_carlo.detection_pipeline.events import DetectionEvent

EndConditionType = Literal[
    "blue_team_detection",
    "red_team_detection",
    "target_escaped",
    "detection",
    "time_limit",
]
SimulationOutcome = Literal["detected", "not_detected"]


@dataclass(frozen=True)
class EndConditionFacts:
    """Facts computed by domain code before terminal-condition resolution."""

    detection: Optional[DetectionEvent] = None
    completed_team: Optional[str] = None
    team_detection: Optional[DetectionEvent] = None
    target_escaped: bool = False


@dataclass(frozen=True)
class EndCondition:
    """The single terminal condition reached by a replication."""

    result: SimulationOutcome
    condition: EndConditionType
    timestamp_sec: float
    detection: Optional[DetectionEvent] = None
