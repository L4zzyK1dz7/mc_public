"""Per-sensor runtime state that must persist across simulation timesteps.

Kept separate from `SensorConfig` (pure validated config) since this tracks
mutable evaluation history - when a sensor may next fire, and its k-of-n hit
history per target - which only exists once a simulation is running.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class SensorRuntimeState:
    """Runtime state for a single sensor instance on a single platform."""

    next_eval_time_sec: float = 0.0
    hit_windows: dict[str, Deque[bool]] = field(default_factory=dict)

    def get_window(self, target_id: str, maxlen: int) -> Deque[bool]:
        """Return the k-of-n hit history for a target, creating it on first use.

        args:
            target_id: Identifier of the target platform.
            maxlen: Maximum length of the k-of-n hit history deque.
        """
        return self.hit_windows.setdefault(target_id, deque(maxlen=maxlen))
