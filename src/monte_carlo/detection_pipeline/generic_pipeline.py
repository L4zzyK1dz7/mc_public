"""Detection pipeline entry points.

The detection rules are intentionally left unimplemented. This module defines
the boundary that the simulation orchestrator will call once those rules exist.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.monte_carlo.detection_pipeline.events import DetectionEvent

if TYPE_CHECKING:
	from src.monte_carlo.states.platform_states import PlatformState


def detect(
	platform_states: list[PlatformState],
	current_time_sec: float,
) -> Optional[DetectionEvent]:
	"""Return the first detection at the current simulation time.

	Detection rules will be implemented after the pipeline contract has been
	reviewed. The current placeholder reports no detection.
	"""

	del platform_states, current_time_sec
	return None
