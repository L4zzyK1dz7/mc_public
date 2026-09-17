"""
End condition checking logic for Monte Carlo simulations.

This module provides functions to evaluate various simulation termination conditions
such as barrier crossing, detection events, and team-level outcomes.

ARCHITECTURAL RULE: "Validate at the Boundary, Trust in the Core"
These are CORE ENGINE functions that operate on validated runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from src.monte_carlo.detection_pipeline.events import DetectionEvent

EndConditionType = Literal["detection", "time_limit"]
SimulationOutcome = Literal["detected", "not_detected"]


@dataclass(frozen=True)
class EndCondition:
    """The single terminal condition reached by a replication."""

    result: SimulationOutcome
    condition: EndConditionType
    timestamp_sec: float
    detection: Optional[DetectionEvent] = None


def check_end_conditions(
    *,
    current_time_sec: float,
    current_step: int,
    max_steps: int,
    detection: Optional[DetectionEvent] = None,
) -> Optional[EndCondition]:
    """Return the terminal condition reached at the current timestep.

    args:
        *: Enforces that all following arguments must be specified as keyword arguments.
        current_time_sec: The current simulation time in seconds.
        current_step: The current simulation step index.
        max_steps: The maximum number of simulation steps allowed.
        detection: An optional detection event that occurred at the current timestep.

    Detection has priority over the time limit when both are observed on the
    final timestep. Returning ``None`` means the replication should continue.

    returns:
        An EndCondition instance if a terminal condition is reached, otherwise None.
    """

    if detection is not None:
        return EndCondition(
            result="detected",
            condition="detection",
            timestamp_sec=current_time_sec,
            detection=detection,
        )

    # Check if the simulation has reached the maximum number of steps (time limit). Record as a time limit end condition.
    if current_step >= max_steps - 1:
        return EndCondition(
            result="not_detected",
            condition="time_limit",
            timestamp_sec=current_time_sec,
        )

    return None
