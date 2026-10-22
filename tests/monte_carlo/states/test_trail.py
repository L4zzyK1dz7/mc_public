"""Unit tests for PositionTrail and TrailSegment."""

from __future__ import annotations

import pytest

from src.monte_carlo.states.trail import PositionTrail, TrailSegment
from src.schemas.movement import Waypoint


def test_empty_trail():
    trail = PositionTrail()
    assert len(trail) == 0
    assert trail.latest_segment() is None
    assert list(trail.segments_since(0.0)) == []


def test_single_point_trail():
    trail = PositionTrail()
    trail.record(0.0, Waypoint(10.0, 20.0))
    assert len(trail) == 1
    assert trail.latest_segment() is None
    assert list(trail.segments_since(0.0)) == []


def test_two_point_trail():
    trail = PositionTrail()
    trail.record(0.0, Waypoint(0.0, 0.0))
    trail.record(60.0, Waypoint(100.0, 50.0))

    assert len(trail) == 2
    seg = trail.latest_segment()
    assert seg is not None
    assert seg.start == Waypoint(0.0, 0.0)
    assert seg.end == Waypoint(100.0, 50.0)
    assert seg.time_sec == 0.0

    segs = list(trail.segments_since(0.0))
    assert len(segs) == 1
    assert segs[0] == seg


def test_multi_segment_and_ordering():
    trail = PositionTrail()
    # 4 points -> 3 segments
    trail.record(0.0, Waypoint(0.0, 0.0))
    trail.record(60.0, Waypoint(10.0, 10.0))
    trail.record(120.0, Waypoint(20.0, 20.0))
    trail.record(180.0, Waypoint(30.0, 30.0))

    assert len(trail) == 4
    latest = trail.latest_segment()
    assert latest is not None
    assert latest.start == Waypoint(20.0, 20.0)
    assert latest.end == Waypoint(30.0, 30.0)
    assert latest.time_sec == 120.0

    # All segments since 0.0
    all_segs = list(trail.segments_since(0.0))
    assert len(all_segs) == 3
    assert [s.time_sec for s in all_segs] == [0.0, 60.0, 120.0]

    # Segments since exact boundary 60.0
    segs_from_60 = list(trail.segments_since(60.0))
    assert len(segs_from_60) == 2
    assert [s.time_sec for s in segs_from_60] == [60.0, 120.0]

    # Segments since between boundaries (e.g. 75.0)
    segs_from_75 = list(trail.segments_since(75.0))
    assert len(segs_from_75) == 1
    assert segs_from_75[0].time_sec == 120.0

    # Segments since latest point time (180.0) -> no subsequent point, empty
    assert list(trail.segments_since(180.0)) == []

    # Segments since future time -> empty
    assert list(trail.segments_since(300.0)) == []


def test_trail_segment_immutability():
    seg = TrailSegment(
        start=Waypoint(0.0, 0.0),
        end=Waypoint(1.0, 1.0),
        time_sec=0.0,
    )
    with pytest.raises(AttributeError):
        seg.time_sec = 10.0  # type: ignore[misc]
