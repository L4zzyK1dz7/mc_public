"""Unit tests for active ping collection."""

from __future__ import annotations

from types import SimpleNamespace
import pytest

from src.monte_carlo.detection_pipeline.active_pings import (
    ActivePing,
    collect_active_pings,
)

pytestmark = pytest.mark.unit


def make_platform(
    platform_id: str,
    team: str = "Blue",
    pos_x: float = 100.0,
    pos_y: float = 200.0,
    sensors: list | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=platform_id,
        team=team,
        pos=SimpleNamespace(x=pos_x, y=pos_y),
        sensors=sensors or [],
        ping_states={},
    )


def test_happy_path_ping_interval_schedule():
    """Verify pings are emitted at intervals (e.g. interval=5.0s, timestep=1.0s)."""
    sensor = SimpleNamespace(
        display_name="Pinger",
        interval_time_sec=5.0,
        active_source=True,
    )
    platform = make_platform("Blue_1", sensors=[sensor])

    # t=1.0: First ping emitted, next is scheduled for 1.0 + 5.0 = 6.0
    pings_t1 = collect_active_pings([platform], current_time_sec=1.0)
    assert len(pings_t1) == 1
    assert pings_t1[0] == ActivePing(
        source_platform_id="Blue_1",
        sensor_name="Pinger",
        source_x=100.0,
        source_y=200.0,
        timestamp_sec=1.0,
    )

    # t=2.0 to 5.0: No pings
    for t in (2.0, 3.0, 4.0, 5.0):
        assert collect_active_pings([platform], current_time_sec=t) == []

    # t=6.0: Second ping emitted
    pings_t6 = collect_active_pings([platform], current_time_sec=6.0)
    assert len(pings_t6) == 1
    assert pings_t6[0].timestamp_sec == 6.0


def test_non_blue_platform_does_not_ping():
    """Verify Red platforms do not emit active pings."""
    sensor = SimpleNamespace(
        display_name="Enemy Pinger",
        interval_time_sec=1.0,
        active_source=True,
    )
    red_platform = make_platform("Red_1", team="Red", sensors=[sensor])

    pings = collect_active_pings([red_platform], current_time_sec=1.0)
    assert pings == []


def test_passive_sensor_does_not_ping():
    """Verify sensors with active_source=False do not emit pings."""
    sensor = SimpleNamespace(
        display_name="Passive Sonar",
        interval_time_sec=1.0,
        active_source=False,
    )
    platform = make_platform("Blue_1", sensors=[sensor])

    pings = collect_active_pings([platform], current_time_sec=1.0)
    assert pings == []


def test_multiple_pingers_in_same_timestep():
    """Verify multiple active sensors across platforms emit pings in the same timestep."""
    s1 = SimpleNamespace(display_name="Pinger 1", interval_time_sec=2.0, active_source=True)
    s2 = SimpleNamespace(display_name="Pinger 2", interval_time_sec=2.0, active_source=True)
    p1 = make_platform("Blue_1", pos_x=10.0, pos_y=20.0, sensors=[s1])
    p2 = make_platform("Blue_2", pos_x=30.0, pos_y=40.0, sensors=[s2])

    pings = collect_active_pings([p1, p2], current_time_sec=1.0)
    assert len(pings) == 2
    assert {p.source_platform_id for p in pings} == {"Blue_1", "Blue_2"}
    assert {p.sensor_name for p in pings} == {"Pinger 1", "Pinger 2"}
