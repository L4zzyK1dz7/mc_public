"""Platform neutralisation logic for Monte Carlo simulation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Collection, Iterable

if TYPE_CHECKING:
    from src.monte_carlo.states.platform_states import PlatformState


def neutralise_detected_platforms(
    platform_states: Iterable[PlatformState],
    detected_ids: Collection[str],
) -> list[str]:
    """Mark detected platforms as neutralised.

    Idempotent helper that checks each platform in ``platform_states``. If its ID
    is in ``detected_ids`` and it is not already neutralised, marks
    ``platform.neutralised = True``. Unknown IDs in ``detected_ids`` are ignored.

    Args:
        platform_states: Platforms to check and potentially neutralise.
        detected_ids: Platform IDs that have been detected.

    Returns:
        List of platform IDs that were newly neutralised in this call.
    """
    newly_neutralised: list[str] = []
    detected_set = set(detected_ids)
    for platform in platform_states:
        if platform.id in detected_set and not platform.neutralised:
            platform.neutralised = True
            newly_neutralised.append(platform.id)
    return newly_neutralised
