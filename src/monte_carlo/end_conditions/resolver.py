"""Priority-based terminal-condition resolver."""

from __future__ import annotations

from typing import Optional

from .models import EndCondition, EndConditionFacts


def check_end_conditions(
    *,
    current_time_sec: float,
    current_step: int,
    max_steps: int,
    facts: EndConditionFacts,
) -> Optional[EndCondition]:
    """Return the highest-priority terminal condition, if one has been met.

    Priority is deliberately ordered from most specific to least specific:
    team detection, target escape, initial detection, then time limit.
    """

    if facts.completed_team == "Blue":
        return EndCondition(
            result="detected",
            condition="blue_team_detection",
            timestamp_sec=current_time_sec,
            detection=facts.team_detection,
        )

    if facts.completed_team == "Red":
        return EndCondition(
            result="detected",
            condition="red_team_detection",
            timestamp_sec=current_time_sec,
            detection=facts.team_detection,
        )

    if facts.target_escaped:
        return EndCondition(
            result="not_detected",
            condition="target_escaped",
            timestamp_sec=current_time_sec,
        )

    if facts.detection is not None:
        return EndCondition(
            result="detected",
            condition="detection",
            timestamp_sec=current_time_sec,
            detection=facts.detection,
        )

    if current_step >= max_steps - 1:
        return EndCondition(
            result="not_detected",
            condition="time_limit",
            timestamp_sec=current_time_sec,
        )

    return None
