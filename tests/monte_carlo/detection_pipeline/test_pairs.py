"""Unit tests for iter_platform_sensors - the shared platform/sensor/target
iteration used by both the detection pipeline and OutcomeDetectionManager.seed_pairs.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.monte_carlo.detection_pipeline.pairs import iter_platform_sensors

pytestmark = pytest.mark.unit


def make_sensor(name: str = "Sensor 1") -> SimpleNamespace:
    return SimpleNamespace(type="generic", display_name=name)


def test_platform_with_no_sensors_is_skipped(platform_factory):
    platform = platform_factory("Blue_1", sensors=[])
    target = platform_factory("Red_1", team="Red")

    assert list(iter_platform_sensors([platform, target])) == []


def test_platform_with_no_opposing_team_is_skipped(platform_factory):
    platform = platform_factory("Blue_1", sensors=[make_sensor()])
    other_blue = platform_factory("Blue_2", sensors=[])

    assert list(iter_platform_sensors([platform, other_blue])) == []


def test_yields_one_entry_per_sensor_with_all_opposing_targets(platform_factory):
    sensor_1 = make_sensor("S1")
    sensor_2 = make_sensor("S2")
    blue = platform_factory("Blue_1", sensors=[sensor_1, sensor_2])
    red_1 = platform_factory("Red_1", team="Red")
    red_2 = platform_factory("Red_2", team="Red")

    pairs = list(iter_platform_sensors([blue, red_1, red_2]))

    assert len(pairs) == 2  # one per sensor
    for platform, _sensor, targets in pairs:
        assert platform is blue
        assert {t.id for t in targets} == {"Red_1", "Red_2"}
    assert [sensor for _, sensor, _ in pairs] == [sensor_1, sensor_2]


def test_skips_sensors_where_can_detect_is_false(platform_factory):
    normal_sensor = SimpleNamespace(type="generic", display_name="Normal", can_detect=True)
    ping_only_sensor = SimpleNamespace(type="generic", display_name="Ping Only", can_detect=False)
    blue = platform_factory("Blue_1", sensors=[normal_sensor, ping_only_sensor])
    red = platform_factory("Red_1", team="Red")

    pairs = list(iter_platform_sensors([blue, red]))
    assert len(pairs) == 1
    assert pairs[0][1] is normal_sensor


def test_excludes_neutralised_targets_from_target_platforms(platform_factory):
    sensor = make_sensor()
    blue = platform_factory("Blue_1", sensors=[sensor])
    red_active = platform_factory("Red_1", team="Red")
    red_neutralised = platform_factory("Red_2", team="Red")
    red_neutralised.neutralised = True

    pairs = list(iter_platform_sensors([blue, red_active, red_neutralised]))
    assert len(pairs) == 1
    _, _, targets = pairs[0]
    assert [t.id for t in targets] == ["Red_1"]


def test_skips_platform_when_all_opposing_targets_are_neutralised(platform_factory):
    sensor = make_sensor()
    blue = platform_factory("Blue_1", sensors=[sensor])
    red = platform_factory("Red_1", team="Red")
    red.neutralised = True

    pairs = list(iter_platform_sensors([blue, red]))
    assert pairs == []


def test_neutralised_detecting_platform_still_yields_sensors(platform_factory):
    sensor = make_sensor()
    blue = platform_factory("Blue_1", sensors=[sensor])
    blue.neutralised = True
    red = platform_factory("Red_1", team="Red")

    pairs = list(iter_platform_sensors([blue, red]))
    assert len(pairs) == 1
    detecting, s, targets = pairs[0]
    assert detecting is blue
    assert s is sensor
    assert [t.id for t in targets] == ["Red_1"]


