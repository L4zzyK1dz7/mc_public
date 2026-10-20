"""Runtime state management for sonobuoys across simulation timesteps."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

PlatformId = str
SonobuoyId = str
HitWindow = Deque[bool]
TargetWindows = dict[PlatformId, HitWindow]
SonobuoyWindows = dict[SonobuoyId, TargetWindows]


@dataclass
class SonobuoyRuntimeState:
    """Runtime state holding sliding hit windows and latest ping cycle outcomes.

    Attributes:
        windows: Sliding windows of boolean detection results per buoy and target.
        latest: Map of buoy_id -> target_id -> bool for evaluations in the current timestep.
        latest_requiv: Map of buoy_id -> target_id -> float for equivalent range in current timestep.
    """

    windows: SonobuoyWindows = field(default_factory=dict)
    latest: dict[SonobuoyId, dict[PlatformId, bool]] = field(default_factory=dict)
    latest_requiv: dict[SonobuoyId, dict[PlatformId, float]] = field(default_factory=dict)

    def get_window(self, buoy_id: str, target_id: str, maxlen: int) -> HitWindow:
        """Retrieve or initialise the sliding hit window for a specific buoy and target."""
        buoy_windows = self.windows.setdefault(buoy_id, {})
        if target_id not in buoy_windows:
            buoy_windows[target_id] = deque(maxlen=maxlen)
        return buoy_windows[target_id]

    def record_latest(
        self,
        buoy_id: str,
        target_id: str,
        hit: bool,
        requiv: Optional[float] = None,
    ) -> None:
        """Record the latest result for this buoy and target in the current timestep."""
        target_map = self.latest.setdefault(buoy_id, {})
        # If multiple pings hit in the same timestep, True takes precedence
        target_map[target_id] = target_map.get(target_id, False) or hit
        if requiv is not None and hit:
            requiv_map = self.latest_requiv.setdefault(buoy_id, {})
            existing = requiv_map.get(target_id)
            requiv_map[target_id] = min(existing, requiv) if existing is not None else requiv

    def clear_cycle(self) -> None:
        """Clear the single-cycle latest results map at the start of each timestep."""
        self.latest.clear()
        self.latest_requiv.clear()

    def reset(self) -> None:
        """Reset all runtime state for a new replication."""
        self.windows.clear()
        self.latest.clear()
        self.latest_requiv.clear()
