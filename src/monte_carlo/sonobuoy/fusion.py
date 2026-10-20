"""Fusion algorithms for multistatic sonobuoy receivers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Sequence

from src.monte_carlo.sonobuoy.events import (
    SonobuoyDetectionEvent,
    SonobuoyFusionResult,
)

if TYPE_CHECKING:
    from src.monte_carlo.sonobuoy.state import SonobuoyRuntimeState
    from src.schemas.sonobuoy import SonobuoyConfig


def single_cycle_detections(
    sonobuoys: list[SonobuoyConfig],
    target_platforms: Sequence[Any],
    state: SonobuoyRuntimeState,
    data_fusion_requirement: int,
    timestamp_sec: float,
) -> list[SonobuoyDetectionEvent]:
    """Scenario 3: Single ping cycle detection.

    For each target, count the number of buoys participating in 'single_cycle' whose
    latest result in the current timestep is True. If count >= data_fusion_requirement,
    a detection occurs.

    Args:
        sonobuoys: Configured sonobuoy receivers.
        target_platforms: Target (Red) platforms.
        state: Runtime state holding current-cycle results.
        data_fusion_requirement: Minimum distinct buoys required.
        timestamp_sec: Current simulation timestamp.

    Returns:
        List of single-cycle detection events for targets meeting the requirement.
    """
    events: list[SonobuoyDetectionEvent] = []
    eligible_buoys = [b for b in sonobuoys if "single_cycle" in b.evaluation_modes]

    for target in target_platforms:
        active_hits = sum(
            1
            for b in eligible_buoys
            if state.latest.get(b.display_name, {}).get(target.id, False)
        )
        if active_hits >= data_fusion_requirement:
            events.append(
                SonobuoyDetectionEvent(
                    timestamp_sec=timestamp_sec,
                    detecting_id="sonobuoy_field",
                    target_platform_id=target.id,
                    mode="single_cycle",
                )
            )
    return events


def multi_buoy_detections(
    sonobuoys: list[SonobuoyConfig],
    target_platforms: Sequence[Any],
    state: SonobuoyRuntimeState,
    data_fusion_requirement: int,
    timestamp_sec: float,
) -> list[SonobuoyDetectionEvent]:
    """Scenario 2: Multi-buoy sliding window fusion.

    For each target, sum the boolean True values across the sliding windows of all buoys
    participating in 'multi'. If total >= data_fusion_requirement, a detection occurs.

    Args:
        sonobuoys: Configured sonobuoy receivers.
        target_platforms: Target (Red) platforms.
        state: Runtime state holding sliding windows.
        data_fusion_requirement: Minimum combined hits required.
        timestamp_sec: Current simulation timestamp.

    Returns:
        List of multi-buoy detection events for targets meeting the requirement.
    """
    events: list[SonobuoyDetectionEvent] = []
    eligible_buoys = [b for b in sonobuoys if "multi" in b.evaluation_modes]

    for target in target_platforms:
        total_hits = sum(
            sum(state.get_window(b.display_name, target.id, b.n))
            for b in eligible_buoys
        )
        if total_hits >= data_fusion_requirement:
            events.append(
                SonobuoyDetectionEvent(
                    timestamp_sec=timestamp_sec,
                    detecting_id="sonobuoy_field",
                    target_platform_id=target.id,
                    mode="multi",
                )
            )
    return events


def single_buoy_detections(
    sonobuoys: list[SonobuoyConfig],
    target_platforms: Sequence[Any],
    state: SonobuoyRuntimeState,
    timestamp_sec: float,
) -> list[SonobuoyDetectionEvent]:
    """Scenario 1: Single-buoy k-of-n detection.

    For each buoy participating in 'single' and each target, checks if the sum of hits
    in that buoy's sliding window is >= k.

    Args:
        sonobuoys: Configured sonobuoy receivers.
        target_platforms: Target (Red) platforms.
        state: Runtime state holding sliding windows.
        timestamp_sec: Current simulation timestamp.

    Returns:
        List of single-buoy detection events.
    """
    events: list[SonobuoyDetectionEvent] = []
    eligible_buoys = [b for b in sonobuoys if "single" in b.evaluation_modes]

    for buoy in eligible_buoys:
        for target in target_platforms:
            window = state.get_window(buoy.display_name, target.id, buoy.n)
            if sum(window) >= buoy.k:
                events.append(
                    SonobuoyDetectionEvent(
                        timestamp_sec=timestamp_sec,
                        detecting_id=buoy.display_name,
                        target_platform_id=target.id,
                        mode="single",
                    )
                )
    return events


def evaluate_fusion(
    sonobuoys: list[SonobuoyConfig],
    target_platforms: Sequence[Any],
    state: SonobuoyRuntimeState,
    data_fusion_requirement: int,
    timestamp_sec: float,
) -> Optional[SonobuoyFusionResult]:
    """Evaluate fusion rules in priority order: single_cycle -> multi -> single.

    Returns the first rule met with its detection events, or None if no rule is met.
    """
    sc_events = single_cycle_detections(
        sonobuoys=sonobuoys,
        target_platforms=target_platforms,
        state=state,
        data_fusion_requirement=data_fusion_requirement,
        timestamp_sec=timestamp_sec,
    )
    if sc_events:
        return SonobuoyFusionResult(mode="single_cycle", events=tuple(sc_events))

    multi_events = multi_buoy_detections(
        sonobuoys=sonobuoys,
        target_platforms=target_platforms,
        state=state,
        data_fusion_requirement=data_fusion_requirement,
        timestamp_sec=timestamp_sec,
    )
    if multi_events:
        return SonobuoyFusionResult(mode="multi", events=tuple(multi_events))

    single_events = single_buoy_detections(
        sonobuoys=sonobuoys,
        target_platforms=target_platforms,
        state=state,
        timestamp_sec=timestamp_sec,
    )
    if single_events:
        return SonobuoyFusionResult(mode="single", events=tuple(single_events))

    return None
