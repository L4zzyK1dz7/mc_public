"""Unit tests for sonobuoy fusion algorithms and priority order."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional
import pytest

from src.monte_carlo.sonobuoy.fusion import (
    evaluate_fusion,
    multi_buoy_detections,
    single_buoy_detections,
    single_cycle_detections,
)
from src.monte_carlo.sonobuoy.state import SonobuoyRuntimeState
from src.schemas.sonobuoy import SonobuoyConfig

pytestmark = pytest.mark.unit


def make_buoy(name: str, k: int = 1, n: int = 3, modes: Optional[list[str]] = None) -> SonobuoyConfig:
    return SonobuoyConfig(
        display_name=name,
        x_m=0.0,
        y_m=0.0,
        k=k,
        n=n,
        distance_m=[0.0, 1000.0],
        pod=[1.0, 0.0],
        evaluation_modes=modes or ["single", "multi", "single_cycle"],
    )


def make_target(target_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=target_id, pos=SimpleNamespace(x=10.0, y=10.0))


def test_single_cycle_detections_happy_path():
    """Verify single-cycle detection triggers when active buoys meet requirement."""
    b1 = make_buoy("B1")
    b2 = make_buoy("B2")
    b3 = make_buoy("B3")
    target = make_target("Red_1")

    state = SonobuoyRuntimeState()
    # B1 and B2 detected in this timestep, B3 did not
    state.record_latest("B1", "Red_1", True)
    state.record_latest("B2", "Red_1", True)
    state.record_latest("B3", "Red_1", False)

    # Requirement 2 -> meets >= 2
    events = single_cycle_detections([b1, b2, b3], [target], state, data_fusion_requirement=2, timestamp_sec=10.0)
    assert len(events) == 1
    assert events[0].mode == "single_cycle"
    assert events[0].detecting_id == "sonobuoy_field"
    assert events[0].target_platform_id == "Red_1"

    # Requirement 3 -> fails (only 2 active)
    assert single_cycle_detections([b1, b2, b3], [target], state, data_fusion_requirement=3, timestamp_sec=10.0) == []


def test_single_cycle_ignores_stale_history():
    """Verify single_cycle does not use older window values, only state.latest."""
    b1 = make_buoy("B1")
    target = make_target("Red_1")

    state = SonobuoyRuntimeState()
    # Sliding window has 3 Trues, but in this timestep latest is empty (no ping)
    state.get_window("B1", "Red_1", 3).extend([True, True, True])

    events = single_cycle_detections([b1], [target], state, data_fusion_requirement=1, timestamp_sec=10.0)
    assert events == []


def test_multi_buoy_detections():
    """Verify multi_buoy sums hits across participating buoys."""
    b1 = make_buoy("B1", modes=["multi"])
    b2 = make_buoy("B2", modes=["multi"])
    b3_excluded = make_buoy("B3", modes=["single"])  # Does not participate in multi
    target = make_target("Red_1")

    state = SonobuoyRuntimeState()
    # B1 has [True, False], B2 has [True] -> total 2 hits
    state.get_window("B1", "Red_1", 3).extend([True, False])
    state.get_window("B2", "Red_1", 3).extend([True])
    # B3 has [True, True] but is excluded from multi mode
    state.get_window("B3", "Red_1", 3).extend([True, True])

    # Requirement 2: B1 + B2 = 2 hits >= 2 -> True
    events = multi_buoy_detections([b1, b2, b3_excluded], [target], state, data_fusion_requirement=2, timestamp_sec=10.0)
    assert len(events) == 1
    assert events[0].mode == "multi"

    # Requirement 3: B1 + B2 = 2 < 3 -> False (B3 excluded)
    assert multi_buoy_detections([b1, b2, b3_excluded], [target], state, data_fusion_requirement=3, timestamp_sec=10.0) == []


def test_single_buoy_detections():
    """Verify single buoy k-of-n detection."""
    b1 = make_buoy("B1", k=2, n=3, modes=["single"])
    b2 = make_buoy("B2", k=2, n=3, modes=["single"])
    target = make_target("Red_1")

    state = SonobuoyRuntimeState()
    state.get_window("B1", "Red_1", 3).extend([True, False, True])  # 2 hits >= 2 -> detected
    state.get_window("B2", "Red_1", 3).extend([True, False, False])  # 1 hit < 2 -> no detection

    events = single_buoy_detections([b1, b2], [target], state, timestamp_sec=10.0)
    assert len(events) == 1
    assert events[0].mode == "single"
    assert events[0].detecting_id == "B1"


def test_evaluate_fusion_priority_order():
    """Verify priority: single_cycle beats multi, multi beats single."""
    b1 = make_buoy("B1", k=1, n=3)
    b2 = make_buoy("B2", k=1, n=3)
    target = make_target("Red_1")

    state = SonobuoyRuntimeState()
    # All three conditions met simultaneously:
    # 1. latest has B1=True, B2=True -> single_cycle (requirement 2) met!
    # 2. windows have B1=[True], B2=[True] -> multi (requirement 2) met!
    # 3. B1 window has 1 True >= k(1) -> single met!
    state.get_window("B1", "Red_1", 3).append(True)
    state.get_window("B2", "Red_1", 3).append(True)
    state.record_latest("B1", "Red_1", True)
    state.record_latest("B2", "Red_1", True)

    res = evaluate_fusion([b1, b2], [target], state, data_fusion_requirement=2, timestamp_sec=10.0)
    assert res is not None
    assert res.mode == "single_cycle"

    # Now simulate no single_cycle (latest is empty/cleared), multi and single remain met -> multi wins
    state.clear_cycle()
    res2 = evaluate_fusion([b1, b2], [target], state, data_fusion_requirement=2, timestamp_sec=11.0)
    assert res2 is not None
    assert res2.mode == "multi"

    # Now make multi requirement higher so only single is met -> single wins
    res3 = evaluate_fusion([b1, b2], [target], state, data_fusion_requirement=5, timestamp_sec=12.0)
    assert res3 is not None
    assert res3.mode == "single"

    # When no conditions met
    state.reset()
    assert evaluate_fusion([b1, b2], [target], state, data_fusion_requirement=2, timestamp_sec=13.0) is None

