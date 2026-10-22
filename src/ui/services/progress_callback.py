"""
Progress callback factory for Monte Carlo replications.

Provides a factory for creating progress callbacks that update a progress placeholder
(e.g., Streamlit st.empty() or mock in tests).
"""

from __future__ import annotations

from typing import Any, Callable

ProgressCallback = Callable[[int, int], None]


def make_progress_callback(placeholder: Any) -> ProgressCallback:
    """
    Return a progress callback closure that updates the given placeholder.

    Args:
        placeholder: An object supporting .progress(value: float, text: str).

    Returns:
        ProgressCallback: A function accepting (completed: int, total: int).
    """

    def callback(completed: int, total: int) -> None:
        fraction = float(completed) / float(total) if total > 0 else 1.0
        clamped_fraction = max(0.0, min(1.0, fraction))
        placeholder.progress(
            clamped_fraction, text=f"Replication {completed} of {total}"
        )

    return callback
