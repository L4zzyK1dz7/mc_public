"""Data contracts produced by the detection pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionEvent:
    """A detection reported during one simulation timestep."""

    detecting_platform_id: str
    target_platform_id: str
    sensor_name: str
    distance_m: float
