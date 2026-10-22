"""Position trail tracking for platform movement history.

Maintains a time-ordered sequence of positions recorded at t=0 and each simulation
timestep, supporting efficient range queries for historical trail intersection.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from typing import Iterator, Optional

from src.schemas.movement import Waypoint


@dataclass(frozen=True)
class TrailSegment:
    """A directed historical segment between two consecutive timesteps.

    Attributes:
        start: Older position endpoint (P1).
        end: Younger position endpoint (P2).
        time_sec: Simulation time at the start endpoint (P1) in seconds.
    """

    start: Waypoint
    end: Waypoint
    time_sec: float


@dataclass
class PositionTrail:
    """Time-ordered record of platform positions across a simulation replication.

    Parallel lists are used to ensure compatibility with Python 3.9's `bisect_left`
    without requiring the `key=` parameter introduced in Python 3.10.
    """

    times_sec: list[float] = field(default_factory=list)
    xs: list[float] = field(default_factory=list)
    ys: list[float] = field(default_factory=list)

    def record(self, time_sec: float, pos: Waypoint) -> None:
        """Record the platform position at a given simulation time.

        Args:
            time_sec: Current simulation time in seconds.
            pos: Current platform position waypoint.
        """
        self.times_sec.append(float(time_sec))
        self.xs.append(float(pos.x))
        self.ys.append(float(pos.y))

    def latest_segment(self) -> Optional[TrailSegment]:
        """Return the newest segment (previous step to current step), if available.

        Returns:
            The most recent TrailSegment, or None if fewer than 2 points exist.
        """
        if len(self.times_sec) < 2:
            return None
        return TrailSegment(
            start=Waypoint(x=self.xs[-2], y=self.ys[-2]),
            end=Waypoint(x=self.xs[-1], y=self.ys[-1]),
            time_sec=self.times_sec[-2],
        )

    def segments_since(self, min_time_sec: float) -> Iterator[TrailSegment]:
        """Yield historical segments whose older endpoint (P1) has time >= min_time_sec.

        Uses binary search to find the start index in O(log n) time.

        Args:
            min_time_sec: Minimum start time in seconds (P1 timestamp).

        Yields:
            TrailSegment instances from oldest valid to newest.
        """
        if len(self.times_sec) < 2:
            return

        start_idx = bisect_left(self.times_sec, min_time_sec)
        max_idx = len(self.times_sec) - 1

        for i in range(start_idx, max_idx):
            yield TrailSegment(
                start=Waypoint(x=self.xs[i], y=self.ys[i]),
                end=Waypoint(x=self.xs[i + 1], y=self.ys[i + 1]),
                time_sec=self.times_sec[i],
            )

    def __len__(self) -> int:
        """Return the number of recorded position points."""
        return len(self.times_sec)
