"""2D segment intersection geometry based on vector cross products.

This module provides pure geometric primitives for determining whether two directed
line segments strictly intersect. It avoids slope-intercept equations (y = mx + c)
and divisions, guaranteeing stability for vertical segments, zero-length segments,
and arbitrary coordinate ranges without division-by-zero errors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from src.schemas.movement import Waypoint

if TYPE_CHECKING:
    from src.monte_carlo.states.trail import TrailSegment


def get_turn(a: Waypoint, b: Waypoint, c: Waypoint) -> float:
    """Calculate the 2D cross product of vectors AB and AC.

    The return value indicates the orientation of point C relative to the directed
    segment from A to B:
        - > 0: C is to the left of directed line A -> B (counter-clockwise turn)
        - < 0: C is to the right of directed line A -> B (clockwise turn)
        - == 0: A, B, and C are collinear

    Args:
        a: Starting waypoint of reference segment.
        b: Ending waypoint of reference segment.
        c: Point to test.

    Returns:
        The scalar 2D cross product (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x).
    """
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _opposite_signs(val1: float, val2: float) -> bool:
    """Check if two floats have strictly opposite signs (neither is zero)."""
    return (val1 > 0.0 and val2 < 0.0) or (val1 < 0.0 and val2 > 0.0)


def segments_cross(
    a: Union[Waypoint, TrailSegment],
    b: Union[Waypoint, TrailSegment],
    c: Optional[Waypoint] = None,
    d: Optional[Waypoint] = None,
) -> bool:
    """Determine whether two line segments strictly cross each other.

    Can be invoked with either:
      - Four waypoints: `segments_cross(a, b, c, d)` for segments AB and CD.
      - Two TrailSegments: `segments_cross(seg1, seg2)`.

    Two segments strictly intersect iff endpoints C and D lie on strictly opposite
    sides of segment AB, AND endpoints A and B lie on strictly opposite sides of
    segment CD.

    Note on boundary conditions:
        Touching endpoints or collinear overlap (where any turn == 0) are treated
        as non-crossing. In continuous simulation with floating-point coordinates,
        touching is measure-zero. Treating touching as non-crossing prevents double-
        counting crossings at shared vertices between adjacent trail segments.

    Args:
        a: Start waypoint of segment 1, or the first TrailSegment.
        b: End waypoint of segment 1, or the second TrailSegment.
        c: Start waypoint of segment 2 (if passing four waypoints).
        d: End waypoint of segment 2 (if passing four waypoints).

    Returns:
        True if the two segments strictly cross, False otherwise.
    """
    if c is None and d is None:
        # Called as segments_cross(seg1, seg2)
        p_a = a.start  # type: ignore[union-attr]
        p_b = a.end  # type: ignore[union-attr]
        p_c = b.start  # type: ignore[union-attr]
        p_d = b.end  # type: ignore[union-attr]
    elif c is not None and d is not None:
        p_a = a  # type: ignore[assignment]
        p_b = b  # type: ignore[assignment]
        p_c = c
        p_d = d
    else:
        raise ValueError("segments_cross requires either 2 TrailSegments or 4 Waypoints")

    turn_ab_c = get_turn(p_a, p_b, p_c)
    turn_ab_d = get_turn(p_a, p_b, p_d)
    if not _opposite_signs(turn_ab_c, turn_ab_d):
        return False

    turn_cd_a = get_turn(p_c, p_d, p_a)
    turn_cd_b = get_turn(p_c, p_d, p_b)
    return _opposite_signs(turn_cd_a, turn_cd_b)
