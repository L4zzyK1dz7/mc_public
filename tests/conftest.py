"""Shared fixtures for the monte_carlo test suite."""

from __future__ import annotations

from typing import Iterable, Optional

import pytest

from src.monte_carlo.states.platform_states import PlatformState, WpProperties
from src.schemas.movement import RandomWalkMovement, Waypoint
from src.schemas.platform import PlatformConfig


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
    blueprint = PlatformConfig.model_construct(
        platform_config_folder=id,
        display_name=id,
        team=team,
        speed_mps=0.0,
        movement_type=RandomWalkMovement(),
        sensors=sensors or [],
    )
    return PlatformState(
        id=id,
        blueprint=blueprint,
        pos=Waypoint(x=x, y=y),
        movement_runtime=None,  # type: ignore[arg-type]  # not needed in detection-only tests
        movement_state=None,    # type: ignore[arg-type]  # not needed in detection-only tests
        wp_properties=WpProperties(
            pos=Waypoint(x=x, y=y),
            arrival_time=0.0,
            distance=0.0,
            heading=heading,
            total_duration=0.0,
            step_distance=0.0,
        ),
    )


@pytest.fixture
def platform_factory():
    return make_platform_state


@pytest.fixture
def fake_random_gen():
    return FakeRandomGen
