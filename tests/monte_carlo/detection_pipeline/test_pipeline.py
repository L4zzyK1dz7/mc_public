"""Unit tests for detection_pipeline.pipeline.detect() - the orchestrator that
delegates to whichever strategy is registered for each sensor's type, without
knowing anything about detection algorithms itself.

Uses a fake strategy (via monkeypatch) rather than the real GenericSensorDetectionStrategy,
so a bug in the orchestrator can't be masked by, or confused with, a bug in the algorithm
- that's covered separately in strategies/test_generic.py.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.monte_carlo.detection_pipeline import pipeline
from src.monte_carlo.detection_pipeline.events import DetectionEvent

pytestmark = pytest.mark.unit


class FakeStrategy:
    """Deterministic stand-in for a SensorDetectionStrategy."""

    def __init__(self, produce_events: bool = True) -> None:
        self.produce_events = produce_events
        self.calls: list[tuple[str, str]] = []

    def detect(
        self, sensor, detecting_platform, target_platforms, current_time_sec, random_gen
    ):
        self.calls.append((detecting_platform.id, sensor.display_name))
        if not self.produce_events:
            return []
        return [
            DetectionEvent(
                detecting_platform_id=detecting_platform.id,
                target_platform_id=target.id,
                sensor_name=sensor.display_name,
                distance_m=1.0,
            )
            for target in target_platforms
        ]


def make_sensor(
    type_: str = "generic", display_name: str = "Sensor 1"
) -> SimpleNamespace:
    return SimpleNamespace(type=type_, display_name=display_name)


def test_detect_returns_empty_list_when_no_platforms_have_sensors(platform_factory):
    platform = platform_factory("Blue_1", sensors=[])
    target = platform_factory("Red_1", team="Red")

    assert (
        pipeline.detect([platform, target], current_time_sec=0.0, random_gen=None) == []
    )


def test_detect_skips_sensor_types_with_no_registered_strategy(
    platform_factory, monkeypatch
):
    monkeypatch.setattr(pipeline, "get_strategy", lambda sensor_type: None)

    platform = platform_factory("Blue_1", sensors=[make_sensor(type_="future_type")])
    target = platform_factory("Red_1", team="Red")

    assert (
        pipeline.detect([platform, target], current_time_sec=0.0, random_gen=None) == []
    )


def test_detect_aggregates_across_multiple_platforms_and_sensors(
    platform_factory, monkeypatch
):
    fake_strategy = FakeStrategy()
    monkeypatch.setattr(pipeline, "get_strategy", lambda sensor_type: fake_strategy)

    blue = platform_factory(
        "Blue_1",
        sensors=[make_sensor(display_name="S1"), make_sensor(display_name="S2")],
    )
    red = platform_factory("Red_1", team="Red")

    detections = pipeline.detect([blue, red], current_time_sec=0.0, random_gen=None)

    # One event per (sensor, target) combination: 2 sensors x 1 target = 2 events.
    assert len(detections) == 2
    assert {d.sensor_name for d in detections} == {"S1", "S2"}
    assert all(d.target_platform_id == "Red_1" for d in detections)
    # Both of Blue_1's sensors were evaluated - no short-circuiting after the first.
    assert fake_strategy.calls == [("Blue_1", "S1"), ("Blue_1", "S2")]


def test_detect_returns_empty_list_when_strategy_finds_nothing(
    platform_factory, monkeypatch
):
    fake_strategy = FakeStrategy(produce_events=False)
    monkeypatch.setattr(pipeline, "get_strategy", lambda sensor_type: fake_strategy)

    blue = platform_factory("Blue_1", sensors=[make_sensor()])
    red = platform_factory("Red_1", team="Red")

    assert pipeline.detect([blue, red], current_time_sec=0.0, random_gen=None) == []
