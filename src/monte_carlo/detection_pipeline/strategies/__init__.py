"""Strategy pattern implementations for sensor-specific detection logic."""

from __future__ import annotations

from src.monte_carlo.detection_pipeline.strategies.base import SensorDetectionStrategy
from src.monte_carlo.detection_pipeline.strategies.registry import get_strategy

__all__ = ["SensorDetectionStrategy", "get_strategy"]
