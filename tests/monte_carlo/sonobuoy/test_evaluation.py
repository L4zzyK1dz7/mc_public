"""Unit tests for multistatic receiver evaluation."""

from __future__ import annotations

from types import SimpleNamespace
import numpy as np
import pytest

from src.monte_carlo.detection_pipeline.active_pings import ActivePing
from src.monte_carlo.sonobuoy.evaluation import evaluate_pings
from src.monte_carlo.sonobuoy.state import SonobuoyRuntimeState
from src.schemas.sonobuoy import SonobuoyConfig

pytestmark = pytest.mark.unit


def make_target(target_id: str, x: float, y: float) -> SimpleNamespace:
    return SimpleNamespace(id=target_id, pos=SimpleNamespace(x=x, y=y))


def test_evaluate_pings_pod_lookup_and_dice():
    """Verify interpolation and hit recording with seeded RNG."""
    # Buoy at (0, 0), Source at (0, 0), Target at (100, 0) -> R1=100, R2=100 -> Requiv=100
    buoy = SonobuoyConfig(
        display_name="Buoy_1",
        x_m=0.0,
        y_m=0.0,
        k=1,
        n=3,
        distance_m=[0.0, 100.0, 200.0],
        pod=[1.0, 0.6, 0.0],
    )
    target = make_target("Red_1", 100.0, 0.0)
    ping = ActivePing("Blue_1", "Pinger", 0.0, 0.0, 1.0)
    state = SonobuoyRuntimeState()
    rng = np.random.default_rng(42)

    evaluate_pings([ping], [buoy], [target], state, rng)

    window = state.get_window("Buoy_1", "Red_1", 3)
    assert len(window) == 1
    # Check that latest also recorded the result
    assert state.latest["Buoy_1"]["Red_1"] == window[-1]


def test_evaluate_pings_pod_zero_appends_false_without_rng_draw():
    """Verify Requiv > max(distance_m) appends False and does NOT advance RNG."""
    # Distance is 1000m, but table max is 200m -> PoD = 0.0
    buoy = SonobuoyConfig(
        display_name="Buoy_1",
        x_m=0.0,
        y_m=0.0,
        k=1,
        n=3,
        distance_m=[0.0, 200.0],
        pod=[1.0, 0.0],
    )
    target = make_target("Red_1", 1000.0, 0.0)
    ping = ActivePing("Blue_1", "Pinger", 0.0, 0.0, 1.0)
    state = SonobuoyRuntimeState()

    rng1 = np.random.default_rng(12345)
    rng2 = np.random.default_rng(12345)

    evaluate_pings([ping], [buoy], [target], state, rng1)

    window = state.get_window("Buoy_1", "Red_1", 3)
    assert len(window) == 1
    assert window[0] is False
    assert state.latest["Buoy_1"]["Red_1"] is False

    # RNG state must be identical because no random call was made for PoD == 0.0
    assert rng1.random() == rng2.random()


def test_evaluate_pings_multiple_pings_same_timestep():
    """Verify multiple pings each append to window, latest is True if any hit."""
    buoy = SonobuoyConfig(
        display_name="Buoy_1",
        x_m=0.0,
        y_m=0.0,
        k=1,
        n=5,
        distance_m=[0.0, 100.0],
        pod=[1.0, 1.0],  # 100% detection for near ping
    )
    target = make_target("Red_1", 50.0, 0.0)
    # Ping 1 is close (hit = True), Ping 2 is far away (PoD = 0, hit = False)
    ping1 = ActivePing("Blue_1", "Pinger_1", 0.0, 0.0, 1.0)
    ping2 = ActivePing("Blue_2", "Pinger_2", 10000.0, 0.0, 1.0)

    state = SonobuoyRuntimeState()
    rng = np.random.default_rng(42)

    evaluate_pings([ping1, ping2], [buoy], [target], state, rng)

    window = state.get_window("Buoy_1", "Red_1", 5)
    assert len(window) == 2
    assert list(window) == [True, False]
    # latest must be True because at least one ping hit
    assert state.latest["Buoy_1"]["Red_1"] is True


def test_evaluate_pings_no_pings_leaves_history_unchanged():
    """Verify no pings in a timestep leaves window unchanged and clears latest."""
    buoy = SonobuoyConfig(
        display_name="Buoy_1",
        x_m=0.0,
        y_m=0.0,
        k=1,
        n=3,
        distance_m=[0.0, 100.0],
        pod=[1.0, 1.0],
    )
    target = make_target("Red_1", 10.0, 0.0)
    state = SonobuoyRuntimeState()
    state.get_window("Buoy_1", "Red_1", 3).append(True)
    state.record_latest("Buoy_1", "Red_1", True)

    rng = np.random.default_rng(42)
    # Timestep with no active pings
    evaluate_pings([], [buoy], [target], state, rng)

    # Window still has previous value
    assert list(state.get_window("Buoy_1", "Red_1", 3)) == [True]
    # latest is cleared
    assert state.latest == {}
