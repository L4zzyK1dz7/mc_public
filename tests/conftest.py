"""Shared fixtures for the monte_carlo test suite."""

from __future__ import annotations

from typing import Iterable, Optional

import pytest

from src.monte_carlo.states.movement_manager import WpProperties
from src.monte_carlo.states.platform_states import PlatformState
from src.schemas.movement import Waypoint


class FakeRandomGen:
    """Deterministic stand-in for np.random.Generator - only implements .random().

    Raises if asked for more values than provided, so a test can assert a code
    path never touches the RNG at all (e.g. a target that's out of FOV).
    """

    def __init__(self, values: Iterable[float]) -> None:
        self._values = list(values)
        self._index = 0

    def random(self) -> float:
        if self._index >= len(self._values):
            raise AssertionError("FakeRandomGen exhausted - provide more values")
        value = self._values[self._index]
        self._index += 1
        return value


def make_platform_state(
    id: str,
    team: str = "Blue",
    x: float = 0.0,
    y: float = 0.0,
    heading: tuple = (1.0, 0.0),
    sensors: Optional[list] = None,
) -> PlatformState:
    """Build a minimal PlatformState for unit tests that don't need real movement."""
    return PlatformState(
        id=id,
        display_name=id,
        team=team,
        speed_mps=0.0,
        pos=Waypoint(x=x, y=y),
        movement_type=None,
        wp_properties=WpProperties(
            pos=Waypoint(x=x, y=y),
            arrival_time=0.0,
            distance=0.0,
            heading=heading,
            total_duration=0.0,
            step_distance=0.0,
        ),
        sensors=sensors or [],
    )


@pytest.fixture
def platform_factory():
    return make_platform_state


@pytest.fixture
def fake_random_gen():
    return FakeRandomGen
