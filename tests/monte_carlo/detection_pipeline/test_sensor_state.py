"""Unit tests for SensorRuntimeState.get_window - the per-sensor k-of-n history."""

from __future__ import annotations

import pytest

from src.monte_carlo.detection_pipeline.sensor_state import SensorRuntimeState

pytestmark = pytest.mark.unit


def test_get_window_creates_a_new_deque_on_first_use():
    state = SensorRuntimeState()
    window = state.get_window("Red_1", maxlen=3)

    assert list(window) == []
    assert window.maxlen == 3


def test_get_window_returns_the_same_deque_on_repeated_calls():
    state = SensorRuntimeState()
    first = state.get_window("Red_1", maxlen=3)
    first.append(True)

    second = state.get_window("Red_1", maxlen=3)

    assert second is first
    assert list(second) == [True]


def test_different_targets_get_independent_windows():
    state = SensorRuntimeState()
    state.get_window("Red_1", maxlen=3).append(True)
    state.get_window("Red_2", maxlen=3).append(False)

    assert list(state.hit_windows["Red_1"]) == [True]
    assert list(state.hit_windows["Red_2"]) == [False]
