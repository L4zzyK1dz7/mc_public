"""Data contracts for sonobuoy detection events and fusion results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.schemas.sonobuoy import SonobuoyEvaluationMode


@dataclass(frozen=True)
class SonobuoyDetectionEvent:
    """An individual detection event produced by sonobuoy evaluation or fusion."""

    timestamp_sec: float
    detecting_id: str  # Display name of buoy or "sonobuoy_field"
    target_platform_id: str
    mode: SonobuoyEvaluationMode
    distance_m: Optional[float] = None


@dataclass(frozen=True)
class SonobuoyFusionResult:
    """Outcome of fusion evaluation across all buoys for a single timestep."""

    mode: SonobuoyEvaluationMode
    events: tuple[SonobuoyDetectionEvent, ...]
