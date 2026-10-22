"""Unit tests for segment_geometry (get_turn and segments_cross)."""

from __future__ import annotations

import pytest

from src.monte_carlo.detection_pipeline.segment_geometry import (
    get_turn,
    segments_cross,
)
from src.monte_carlo.states.trail import TrailSegment
from src.schemas.movement import Waypoint


def test_get_turn():
    a = Waypoint(0.0, 0.0)
    b = Waypoint(10.0, 0.0)

    # Point to the left (above line directed in +x direction)
    c_left = Waypoint(5.0, 5.0)
    assert get_turn(a, b, c_left) > 0.0

    # Point to the right (below line directed in +x direction)
    c_right = Waypoint(5.0, -5.0)
    assert get_turn(a, b, c_right) < 0.0

    # Collinear point
    c_collinear = Waypoint(15.0, 0.0)
    assert get_turn(a, b, c_collinear) == 0.0


def test_x_crossing():
    # Horizontal segment (0, 5) -> (10, 5)
    a = Waypoint(0.0, 5.0)
    b = Waypoint(10.0, 5.0)

    # Vertical segment (5, 0) -> (5, 10)
    c = Waypoint(5.0, 0.0)
    d = Waypoint(5.0, 10.0)

    assert segments_cross(a, b, c, d)
    assert segments_cross(c, d, a, b)


def test_vertical_segment_crossing():
    # Segment 1: Vertical line x = 2 from y = -10 to y = 10
    a = Waypoint(2.0, -10.0)
    b = Waypoint(2.0, 10.0)

    # Segment 2: Slanted line from (0, 0) to (4, 4)
    c = Waypoint(0.0, 0.0)
    d = Waypoint(4.0, 4.0)

    assert segments_cross(a, b, c, d)


def test_t_touch_not_crossing():
    # Horizontal segment (0, 0) -> (10, 0)
    a = Waypoint(0.0, 0.0)
    b = Waypoint(10.0, 0.0)

    # Segment touching at (5, 0)
    c = Waypoint(5.0, 0.0)
    d = Waypoint(5.0, 5.0)

    assert not segments_cross(a, b, c, d)


def test_shared_vertex_not_crossing():
    a = Waypoint(0.0, 0.0)
    b = Waypoint(10.0, 0.0)

    c = Waypoint(10.0, 0.0)
    d = Waypoint(10.0, 10.0)

    assert not segments_cross(a, b, c, d)


def test_parallel_disjoint():
    a = Waypoint(0.0, 0.0)
    b = Waypoint(10.0, 0.0)

    c = Waypoint(0.0, 2.0)
    d = Waypoint(10.0, 2.0)

    assert not segments_cross(a, b, c, d)


def test_collinear_not_crossing():
    a = Waypoint(0.0, 0.0)
    b = Waypoint(10.0, 0.0)

    c = Waypoint(5.0, 0.0)
    d = Waypoint(15.0, 0.0)

    assert not segments_cross(a, b, c, d)


def test_disjoint_non_crossing():
    # Lines would cross at (15, 5), outside these segments
    a = Waypoint(0.0, 0.0)
    b = Waypoint(10.0, 0.0)

    c = Waypoint(15.0, 2.0)
    d = Waypoint(15.0, 10.0)

    assert not segments_cross(a, b, c, d)


def test_zero_length_segment():
    a = Waypoint(5.0, 5.0)
    b = Waypoint(5.0, 5.0)

    c = Waypoint(0.0, 0.0)
    d = Waypoint(10.0, 10.0)

    assert not segments_cross(a, b, c, d)


def test_trail_segment_invocation():
    seg1 = TrailSegment(start=Waypoint(0.0, 5.0), end=Waypoint(10.0, 5.0), time_sec=0.0)
    seg2 = TrailSegment(start=Waypoint(5.0, 0.0), end=Waypoint(5.0, 10.0), time_sec=10.0)
    assert segments_cross(seg1, seg2)

    seg3 = TrailSegment(start=Waypoint(0.0, 20.0), end=Waypoint(10.0, 20.0), time_sec=20.0)
    assert not segments_cross(seg1, seg3)


def test_invalid_arguments_raise():
    a = Waypoint(0.0, 0.0)
    b = Waypoint(1.0, 1.0)
    c = Waypoint(2.0, 2.0)
    with pytest.raises(ValueError, match="segments_cross requires"):
        segments_cross(a, b, c)  # missing d
