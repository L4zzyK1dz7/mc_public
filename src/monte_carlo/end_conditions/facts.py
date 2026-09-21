"""Pure computations for terminal-condition facts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterable, List, cast

from src.schemas.simulation import World

if TYPE_CHECKING:
    from src.monte_carlo.states.platform_states import PlatformState


def platforms_by_team(
    platform_states: Iterable["PlatformState"],
) -> Dict[str, List["PlatformState"]]:
    """Group platform states by their canonical team value."""

    grouped = {"Blue": [], "Red": []}
    for platform in platform_states:
        team = cast(str, getattr(platform.team, "value", platform.team))
        if team not in grouped:
            raise ValueError("Unsupported platform team: {!r}".format(team))
        grouped[team].append(platform)
    return grouped


def all_platforms_detected(
    *, required_platform_ids: Iterable[str], detected_platform_ids: Iterable[str]
) -> bool:
    """Return whether every required target platform has been detected.

    Args:
        required_platform_ids: Iterable[str], the IDs of all required target platforms.
        detected_platform_ids: Iterable[str], the IDs of all detected target platforms.

    Returns:
        True if all required target platforms have been detected, False otherwise.

    """

    required_ids = set(required_platform_ids)
    return bool(required_ids) and required_ids.issubset(set(detected_platform_ids))


def target_has_escaped(*, target: PlatformState, world: World) -> bool:
    """Return whether a target position is outside the configured world.

    Args:
        target: The platform state of the target.
        world: The world configuration.

    Returns:
        True if the target has escaped the world boundaries, False otherwise.
    """

    return not (
        world.origin_x <= target.pos.x <= world.origin_x + world.length
        and world.origin_y <= target.pos.y <= world.origin_y + world.height
    )
