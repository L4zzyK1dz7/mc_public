"""Unit tests for multistatic range_equivalent geometry calculations."""

from __future__ import annotations

import math
import pytest

from src.monte_carlo.sonobuoy.geometry import range_equivalent

pytestmark = pytest.mark.unit


def test_range_equivalent_happy_path():
    """Verify Requiv = sqrt(R1 * R2) for 3-4-5 triangle geometry."""
    # Source (0, 0), Target (300, 400) -> R1 = 500
    # Buoy (300, 0), Target (300, 400) -> R2 = 400
    # Requiv = sqrt(500 * 400) = sqrt(200000) ≈ 447.213595
    source = (0.0, 0.0)
    target = (300.0, 400.0)
    buoy = (300.0, 0.0)

    requiv = range_equivalent(source, target, buoy)
    expected = math.sqrt(500.0 * 400.0)
    assert pytest.approx(requiv, rel=1e-6) == expected


def test_range_equivalent_target_on_source_or_receiver():
    """Verify Requiv is 0.0 when target is collocated with source or receiver."""
    source = (100.0, 100.0)
    buoy = (500.0, 500.0)

    # Target on source
    assert range_equivalent(source, source, buoy) == 0.0

    # Target on receiver
    assert range_equivalent(source, buoy, buoy) == 0.0


def test_range_equivalent_large_coordinates_stay_finite():
    """Verify very large coordinates compute without overflow or precision loss."""
    source = (0.0, 0.0)
    target = (1e7, 1e7)
    buoy = (2e7, 2e7)

    requiv = range_equivalent(source, target, buoy)
    assert math.isfinite(requiv)
    assert requiv > 0.0


def test_range_equivalent_invalid_nan_or_inf():
    """Verify ValueError is raised if any coordinate is NaN or inf."""
    with pytest.raises(ValueError, match="must be finite real numbers"):
        range_equivalent((float("nan"), 0.0), (10.0, 10.0), (20.0, 20.0))

    with pytest.raises(ValueError, match="must be finite real numbers"):
        range_equivalent((0.0, 0.0), (float("inf"), 10.0), (20.0, 20.0))
