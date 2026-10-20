"""Multistatic geometry calculations."""

from __future__ import annotations

import math


def range_equivalent(
    source_xy: tuple[float, float],
    target_xy: tuple[float, float],
    receiver_xy: tuple[float, float],
) -> float:
    """Calculate the equivalent bistatic range Requiv = sqrt(R1 * R2).

    Args:
        source_xy: 2D coordinates (x, y) of the active ping source in metres.
        target_xy: 2D coordinates (x, y) of the target platform in metres.
        receiver_xy: 2D coordinates (x, y) of the sonobuoy receiver in metres.

    Returns:
        The equivalent monostatic range Requiv in metres.

    Raises:
        ValueError: If any coordinate value is NaN or infinite.
    """
    for point, label in (
        (source_xy, "source_xy"),
        (target_xy, "target_xy"),
        (receiver_xy, "receiver_xy"),
    ):
        if not (math.isfinite(point[0]) and math.isfinite(point[1])):
            raise ValueError(f"Coordinates for {label} must be finite real numbers, got {point}")

    r1 = math.hypot(target_xy[0] - source_xy[0], target_xy[1] - source_xy[1])
    r2 = math.hypot(receiver_xy[0] - target_xy[0], receiver_xy[1] - target_xy[1])
    return math.sqrt(r1 * r2)
