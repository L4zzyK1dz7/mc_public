"""Unit tests for GenericSensorDetectionStrategy.detect() - the core stochastic
detection algorithm: interval gating, FOV, PoD interpolation, k-of-n, and
exhaustive (non-short-circuiting) evaluation across targets.
"""

from __future__ import annotations

import pytest

from src.monte_carlo.detection_pipeline.strategies.generic import (
    GenericSensorDetectionStrategy,
)
from src.schemas.sensor import GenericSensorConfig

pytestmark = pytest.mark.unit


def make_sensor(**overrides) -> GenericSensorConfig:
    defaults = dict(
        display_name="Sensor 1",
        interval_time_sec=0.0,
        x_values=[0.0],
        pod=[1.0],
        k=1,
        n=1,
        fov_start_angle=0.0,
        fov_end_angle=360.0,
    )
    defaults.update(overrides)
    return GenericSensorConfig(**defaults)


def test_interval_gating_blocks_reevaluation_until_elapsed(
    platform_factory, fake_random_gen
):
    strategy = GenericSensorDetectionStrategy()
    sensor = make_sensor(interval_time_sec=10.0)
    platform = platform_factory("Blue_1")
    target = platform_factory("Red_1", team="Red", x=10.0)

    # First call at t=5: next_eval_time_sec starts at 0.0, so this is allowed to run.
    strategy.detect(
        sensor,
        platform,
        [target],
        current_time_sec=5.0,
        random_gen=fake_random_gen([0.0]),
    )

    # Second call at t=10, before the 10s interval (from t=5) has elapsed: must be a
    # no-op. Empty RNG proves the sensor never even attempted an evaluation.
    detections = strategy.detect(
        sensor,
        platform,
        [target],
        current_time_sec=10.0,
        random_gen=fake_random_gen([]),
    )
    assert detections == []


def test_target_outside_fov_is_never_detected(platform_factory, fake_random_gen):
    strategy = GenericSensorDetectionStrategy()
    sensor = make_sensor(fov_start_angle=0.0, fov_end_angle=90.0)
    platform = platform_factory("Blue_1", heading=(1.0, 0.0))  # facing +x
    target_behind = platform_factory("Red_1", team="Red", x=-10.0)  # bearing 180 deg

    # Empty RNG proves an out-of-FOV target never reaches the PoD/random step.
    detections = strategy.detect(
        sensor,
        platform,
        [target_behind],
        current_time_sec=0.0,
        random_gen=fake_random_gen([]),
    )
    assert detections == []


def test_fov_wraparound_across_0_degrees(platform_factory, fake_random_gen):
    strategy = GenericSensorDetectionStrategy()
    # FOV wraps through 0: 350 -> 10 degrees.
    sensor = make_sensor(fov_start_angle=350.0, fov_end_angle=10.0)
    platform = platform_factory("Blue_1", heading=(1.0, 0.0))
    # Target at ~5 degrees relative bearing (inside the wrapped FOV).
    target_in_fov = platform_factory("Red_1", team="Red", x=10.0, y=1.0)

    detections = strategy.detect(
        sensor,
        platform,
        [target_in_fov],
        current_time_sec=0.0,
        random_gen=fake_random_gen([0.0]),
    )
    assert len(detections) == 1


def test_pod_is_linearly_interpolated_between_table_points(platform_factory):
    strategy = GenericSensorDetectionStrategy()
    sensor = make_sensor(x_values=[0.0, 100.0, 200.0], pod=[1.0, 0.5, 0.0])
    platform = platform_factory("Blue_1")
    # Distance 50m -> exactly halfway between pod(0)=1.0 and pod(100)=0.5 -> pod = 0.75
    target = platform_factory("Red_1", team="Red", x=50.0)

    class RecordingRandomGen:
        def __init__(self, value):
            self.value = value
            self.calls = 0

        def random(self):
            self.calls += 1
            return self.value

    below_threshold = RecordingRandomGen(0.5)  # 0.5 < 0.75 -> hit
    detections = strategy.detect(
        sensor, platform, [target], current_time_sec=0.0, random_gen=below_threshold
    )
    assert len(detections) == 1
    assert below_threshold.calls == 1


def test_pod_is_zero_when_sensor_has_no_table(platform_factory, fake_random_gen):
    strategy = GenericSensorDetectionStrategy()
    sensor = make_sensor(x_values=[], pod=[])
    platform = platform_factory("Blue_1")
    target = platform_factory("Red_1", team="Red", x=10.0)

    # pod=0.0, so even a random draw of exactly 0.0 must not be < 0.0 -> no detection.
    detections = strategy.detect(
        sensor,
        platform,
        [target],
        current_time_sec=0.0,
        random_gen=fake_random_gen([0.0]),
    )
    assert detections == []


def test_k_of_n_triggers_once_threshold_reached(platform_factory, fake_random_gen):
    strategy = GenericSensorDetectionStrategy()
    sensor = make_sensor(k=2, n=3, x_values=[0.0], pod=[1.0])
    platform = platform_factory("Blue_1")
    target = platform_factory("Red_1", team="Red", x=10.0)

    first = strategy.detect(
        sensor,
        platform,
        [target],
        current_time_sec=0.0,
        random_gen=fake_random_gen([0.1]),
    )
    assert first == []  # 1 hit out of k=2 required

    second = strategy.detect(
        sensor,
        platform,
        [target],
        current_time_sec=1.0,
        random_gen=fake_random_gen([0.1]),
    )
    assert len(second) == 1  # 2nd hit reaches k=2 -> detection


def test_k_of_n_not_triggered_below_threshold(platform_factory, fake_random_gen):
    strategy = GenericSensorDetectionStrategy()
    sensor = make_sensor(k=3, n=3, x_values=[0.0], pod=[1.0])
    platform = platform_factory("Blue_1")
    target = platform_factory("Red_1", team="Red", x=10.0)

    strategy.detect(
        sensor,
        platform,
        [target],
        current_time_sec=0.0,
        random_gen=fake_random_gen([0.1]),
    )
    detections = strategy.detect(
        sensor,
        platform,
        [target],
        current_time_sec=1.0,
        random_gen=fake_random_gen([0.1]),
    )
    assert detections == []  # only 2 of 3 required hits so far


def test_evaluates_every_target_exhaustively_in_one_call(
    platform_factory, fake_random_gen
):
    """A detection on one target must not prevent evaluating the remaining targets."""
    strategy = GenericSensorDetectionStrategy()
    sensor = make_sensor(k=1, n=1, fov_start_angle=0.0, fov_end_angle=90.0)
    platform = platform_factory("Blue_1", heading=(1.0, 0.0))
    target_hit = platform_factory("Red_1", team="Red", x=10.0)  # in FOV -> detected
    target_miss = platform_factory(
        "Red_2", team="Red", x=-10.0
    )  # out of FOV -> not detected

    detections = strategy.detect(
        sensor,
        platform,
        [target_hit, target_miss],
        current_time_sec=0.0,
        random_gen=fake_random_gen([0.0]),
    )

    assert [d.target_platform_id for d in detections] == ["Red_1"]
    # The missed target's window must still have been updated this timestep.
    state = platform.sensor_states[id(sensor)]
    assert list(state.hit_windows["Red_2"]) == [False]


def test_sliding_window_persists_and_respects_maxlen(platform_factory, fake_random_gen):
    strategy = GenericSensorDetectionStrategy()
    sensor = make_sensor(k=1, n=2, x_values=[], pod=[])  # pod=0 -> always a miss
    platform = platform_factory("Blue_1")
    target = platform_factory("Red_1", team="Red", x=10.0)

    for t in range(3):
        strategy.detect(
            sensor,
            platform,
            [target],
            current_time_sec=float(t),
            random_gen=fake_random_gen([0.0]),
        )

    window = platform.sensor_states[id(sensor)].hit_windows["Red_1"]
    assert len(window) == 2  # bounded by n=2 despite 3 calls
