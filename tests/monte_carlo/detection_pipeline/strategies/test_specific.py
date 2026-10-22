"""Unit tests for SpecificSensorDetectionStrategy.detect().

Verifies:
- Trail age window evaluation on older endpoint P1 (inside table vs beyond table end).
- PoD lookup and skipping when PoD == 0.
- Crossing vs non-crossing geometry gating (no RNG consumed when non-crossing).
- Independent k-of-n dice rolls per crossing.
- Exhaustive evaluation over multiple targets.
- Single detection event per target within a single timestep even if multiple segments cross.
- Both Blue-detecting-Red and Red-detecting-Blue scenarios.
"""

from __future__ import annotations

import pytest

from src.monte_carlo.detection_pipeline.strategies.specific import (
    SpecificSensorDetectionStrategy,
)
from src.schemas.movement import Waypoint
from src.schemas.sensor import SpecificSensorConfig

pytestmark = pytest.mark.unit


def make_specific_sensor(**overrides) -> SpecificSensorConfig:
    """Helper to construct SpecificSensorConfig with valid defaults."""
    defaults = dict(
        display_name="SpecificSensor_1",
        interval_time_sec=60.0,
        x_values=[0.0, 2.0, 4.0],  # hours
        pod=[1.0, 0.5, 0.2],
        k=1,
        n=1,
    )
    defaults.update(overrides)
    return SpecificSensorConfig(**defaults)


def test_p1_age_inside_table_detects(platform_factory, fake_random_gen):
    strategy = SpecificSensorDetectionStrategy()
    sensor = make_specific_sensor(x_values=[0.0, 2.0, 4.0], pod=[1.0, 0.5, 0.0], k=1, n=1)

    blue = platform_factory("Blue_1", team="Blue")
    blue.trail.record(7140.0, Waypoint(50.0, 0.0))
    blue.trail.record(7200.0, Waypoint(50.0, 100.0))
    blue.pos = Waypoint(50.0, 100.0)

    # Red crossed horizontally from (0, 50) to (100, 50) at t=0 -> t=60
    red = platform_factory("Red_1", team="Red", x=100.0, y=50.0)
    red.trail.record(0.0, Waypoint(0.0, 50.0))
    red.trail.record(60.0, Waypoint(100.0, 50.0))

    # At t=7200 (2.0 hours), P1 time is 0.0 (age = 2.0 hours).
    # PoD at 2.0h is 0.5. Roll 0.3 < 0.5 -> hit!
    rng = fake_random_gen([0.3])
    detections = strategy.detect(
        sensor,
        blue,
        [red],
        current_time_sec=7200.0,
        random_gen=rng,
    )

    assert len(detections) == 1
    event = detections[0]
    assert event.detecting_platform_id == "Blue_1"
    assert event.target_platform_id == "Red_1"
    assert event.sensor_name == "SpecificSensor_1"
    assert event.distance_m == pytest.approx(70.7106, rel=1e-3)


def test_p1_age_beyond_table_end_is_skipped(platform_factory, fake_random_gen):
    strategy = SpecificSensorDetectionStrategy()
    # Table ends at 4.0 hours
    sensor = make_specific_sensor(x_values=[0.0, 4.0], pod=[1.0, 0.5], k=1, n=1)

    blue = platform_factory("Blue_1", team="Blue")
    blue.trail.record(14435.0, Waypoint(50.0, 0.0))
    blue.trail.record(14436.0, Waypoint(50.0, 100.0))

    red = platform_factory("Red_1", team="Red", x=100.0, y=50.0)
    red.trail.record(0.0, Waypoint(0.0, 50.0))
    red.trail.record(60.0, Waypoint(100.0, 50.0))

    # Current time = 14436s (4.01 hours). P1 time is 0.0 -> age = 4.01h > 4.0h.
    # Empty RNG confirms no random rolls were consumed.
    rng = fake_random_gen([])
    detections = strategy.detect(
        sensor,
        blue,
        [red],
        current_time_sec=14436.0,
        random_gen=rng,
    )
    assert detections == []


def test_pod_zero_is_skipped_without_geometry_or_rng(platform_factory, fake_random_gen):
    strategy = SpecificSensorDetectionStrategy()
    # At age 2.0h, pod is 0.0
    sensor = make_specific_sensor(x_values=[0.0, 2.0], pod=[1.0, 0.0], k=1, n=1)

    blue = platform_factory("Blue_1", team="Blue")
    blue.trail.record(7140.0, Waypoint(50.0, 0.0))
    blue.trail.record(7200.0, Waypoint(50.0, 100.0))

    red = platform_factory("Red_1", team="Red")
    red.trail.record(0.0, Waypoint(0.0, 50.0))
    red.trail.record(60.0, Waypoint(100.0, 50.0))

    # Age is 2.0h -> pod = 0.0 -> skip, RNG not consumed
    rng = fake_random_gen([])
    detections = strategy.detect(
        sensor,
        blue,
        [red],
        current_time_sec=7200.0,
        random_gen=rng,
    )
    assert detections == []


def test_non_crossing_segment_consumes_no_rng(platform_factory, fake_random_gen):
    strategy = SpecificSensorDetectionStrategy()
    sensor = make_specific_sensor(x_values=[0.0, 4.0], pod=[1.0, 1.0], k=1, n=1)

    # Blue moves parallel to Red without crossing (at x=200, Red is at x=0..100)
    blue = platform_factory("Blue_1", team="Blue")
    blue.trail.record(50.0, Waypoint(200.0, 0.0))
    blue.trail.record(60.0, Waypoint(200.0, 100.0))

    red = platform_factory("Red_1", team="Red")
    red.trail.record(0.0, Waypoint(0.0, 50.0))
    red.trail.record(30.0, Waypoint(100.0, 50.0))

    rng = fake_random_gen([])
    detections = strategy.detect(
        sensor,
        blue,
        [red],
        current_time_sec=60.0,
        random_gen=rng,
    )
    assert detections == []


def test_k_of_n_threshold_with_multiple_rolls(platform_factory, fake_random_gen):
    strategy = SpecificSensorDetectionStrategy()
    # 2 of 3 required, pod = 0.5
    sensor = make_specific_sensor(x_values=[0.0, 2.0], pod=[0.5, 0.5], k=2, n=3)

    blue = platform_factory("Blue_1", team="Blue")
    blue.trail.record(50.0, Waypoint(50.0, 0.0))
    blue.trail.record(60.0, Waypoint(50.0, 100.0))

    red = platform_factory("Red_1", team="Red")
    red.trail.record(0.0, Waypoint(0.0, 50.0))
    red.trail.record(30.0, Waypoint(100.0, 50.0))

    # Case 1: 1 hit out of 3 rolls (< 2) -> no detection
    # Rolls: 0.3 (<0.5 hit), 0.7 (miss), 0.8 (miss)
    rng_fail = fake_random_gen([0.3, 0.7, 0.8])
    detections_fail = strategy.detect(
        sensor,
        blue,
        [red],
        current_time_sec=60.0,
        random_gen=rng_fail,
    )
    assert detections_fail == []

    # Case 2: 2 hits out of 3 rolls (>= 2) -> detection
    # Rolls: 0.3 (hit), 0.4 (hit), 0.9 (miss)
    rng_pass = fake_random_gen([0.3, 0.4, 0.9])
    detections_pass = strategy.detect(
        sensor,
        blue,
        [red],
        current_time_sec=60.0,
        random_gen=rng_pass,
    )
    assert len(detections_pass) == 1
    assert detections_pass[0].target_platform_id == "Red_1"


def test_multiple_crossings_in_one_timestep_emits_one_event_per_target(
    platform_factory, fake_random_gen
):
    strategy = SpecificSensorDetectionStrategy()
    sensor = make_specific_sensor(x_values=[0.0, 4.0], pod=[1.0, 1.0], k=1, n=1)

    # Blue crosses two horizontal red segments in one step
    blue = platform_factory("Blue_1", team="Blue")
    blue.trail.record(50.0, Waypoint(50.0, 0.0))
    blue.trail.record(60.0, Waypoint(50.0, 200.0))

    red = platform_factory("Red_1", team="Red")
    # Red segment 1: y = 50
    red.trail.record(0.0, Waypoint(0.0, 50.0))
    red.trail.record(10.0, Waypoint(100.0, 50.0))
    # Red segment 2: y = 150
    red.trail.record(20.0, Waypoint(0.0, 150.0))
    red.trail.record(30.0, Waypoint(100.0, 150.0))

    # Segment 1 succeeds on first roll (0.0 < 1.0), so evaluation breaks for this target
    # Only 1 random number should be drawn, not 2
    rng = fake_random_gen([0.0])
    detections = strategy.detect(
        sensor,
        blue,
        [red],
        current_time_sec=60.0,
        random_gen=rng,
    )
    assert len(detections) == 1


def test_exhaustive_evaluation_across_multiple_targets(
    platform_factory, fake_random_gen
):
    strategy = SpecificSensorDetectionStrategy()
    sensor = make_specific_sensor(x_values=[0.0, 4.0], pod=[1.0, 1.0], k=1, n=1)

    blue = platform_factory("Blue_1", team="Blue")
    blue.trail.record(50.0, Waypoint(50.0, 0.0))
    blue.trail.record(60.0, Waypoint(50.0, 100.0))

    # Red_1 crosses blue
    red1 = platform_factory("Red_1", team="Red")
    red1.trail.record(0.0, Waypoint(0.0, 30.0))
    red1.trail.record(10.0, Waypoint(100.0, 30.0))

    # Red_2 also crosses blue
    red2 = platform_factory("Red_2", team="Red")
    red2.trail.record(0.0, Waypoint(0.0, 70.0))
    red2.trail.record(10.0, Waypoint(100.0, 70.0))

    rng = fake_random_gen([0.1, 0.2])
    detections = strategy.detect(
        sensor,
        blue,
        [red1, red2],
        current_time_sec=60.0,
        random_gen=rng,
    )
    assert len(detections) == 2
    assert {d.target_platform_id for d in detections} == {"Red_1", "Red_2"}


def test_red_platform_detecting_blue_target(platform_factory, fake_random_gen):
    strategy = SpecificSensorDetectionStrategy()
    sensor = make_specific_sensor(x_values=[0.0, 4.0], pod=[1.0, 1.0], k=1, n=1)

    # Red platform has sensor
    red = platform_factory("Red_1", team="Red")
    red.trail.record(50.0, Waypoint(50.0, 0.0))
    red.trail.record(60.0, Waypoint(50.0, 100.0))

    # Blue is target
    blue = platform_factory("Blue_1", team="Blue")
    blue.trail.record(0.0, Waypoint(0.0, 50.0))
    blue.trail.record(10.0, Waypoint(100.0, 50.0))

    rng = fake_random_gen([0.0])
    detections = strategy.detect(
        sensor,
        red,
        [blue],
        current_time_sec=60.0,
        random_gen=rng,
    )
    assert len(detections) == 1
    assert detections[0].detecting_platform_id == "Red_1"
    assert detections[0].target_platform_id == "Blue_1"


def test_no_latest_segment_returns_empty(platform_factory, fake_random_gen):
    strategy = SpecificSensorDetectionStrategy()
    sensor = make_specific_sensor()

    # Blue only recorded at t=0 (single point, no segment)
    blue = platform_factory("Blue_1", team="Blue")
    blue.trail.record(0.0, Waypoint(0.0, 0.0))

    red = platform_factory("Red_1", team="Red")
    red.trail.record(0.0, Waypoint(0.0, 0.0))
    red.trail.record(10.0, Waypoint(10.0, 10.0))

    rng = fake_random_gen([])
    detections = strategy.detect(sensor, blue, [red], current_time_sec=0.0, random_gen=rng)
    assert detections == []
