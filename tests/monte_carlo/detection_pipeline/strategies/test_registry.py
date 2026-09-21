"""Unit tests for the sensor-type -> strategy registry lookup (Strategy pattern factory)."""

from __future__ import annotations

import pytest

from src.monte_carlo.detection_pipeline.strategies.generic import (
    GenericSensorDetectionStrategy,
)
from src.monte_carlo.detection_pipeline.strategies.registry import get_strategy

pytestmark = pytest.mark.unit


def test_generic_sensor_type_resolves_to_generic_strategy():
    strategy = get_strategy("generic")
    assert isinstance(strategy, GenericSensorDetectionStrategy)


def test_unregistered_sensor_type_returns_none():
    assert get_strategy("future_sensor_type") is None
