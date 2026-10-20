"""Multistatic receiver evaluation for active pings and sonobuoys."""

from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np

from src.monte_carlo.sonobuoy.geometry import range_equivalent

if TYPE_CHECKING:
    from src.monte_carlo.detection_pipeline.active_pings import ActivePing
    from src.monte_carlo.sonobuoy.state import SonobuoyRuntimeState
    from src.monte_carlo.states.platform_states import PlatformState
    from src.schemas.sonobuoy import SonobuoyConfig


def evaluate_pings(
    pings: list[ActivePing],
    sonobuoys: list[SonobuoyConfig],
    target_platforms: list[PlatformState],
    state: SonobuoyRuntimeState,
    random_gen: np.random.Generator,
) -> None:
    """Evaluate active pings against sonobuoys and opposing target platforms.

    At each timestep, single-cycle latest results are cleared. If no pings are emitted,
    windows remain unchanged and no evaluation takes place.
    For each ping, buoy, and target:
    1. Computes equivalent range Requiv = sqrt(R1 * R2).
    2. Interpolates PoD from the buoy's distance_m and pod table.
    3. If PoD > 0, rolls the random generator for a hit; if PoD == 0, hit is False (no RNG draw).
    4. Appends hit to the buoy's sliding window for that target and records it in state.latest.

    Args:
        pings: Active pings emitted in the current timestep.
        sonobuoys: Configured sonobuoy receivers.
        target_platforms: Target (Red) platforms to evaluate.
        state: Runtime state tracking hit windows and current-cycle results.
        random_gen: Simulation random generator.
    """
    state.clear_cycle()

    if not pings or not sonobuoys or not target_platforms:
        return

    for ping in pings:
        source_xy = (ping.source_x, ping.source_y)
        for buoy in sonobuoys:
            receiver_xy = (buoy.x_m, buoy.y_m)
            max_dist = max(buoy.distance_m) if buoy.distance_m else 0.0

            for target in target_platforms:
                target_xy = (float(target.pos.x), float(target.pos.y))
                requiv = range_equivalent(source_xy, target_xy, receiver_xy)

                if requiv > max_dist:
                    pod = 0.0
                else:
                    pod = float(np.interp(requiv, buoy.distance_m, buoy.pod))

                if pod > 0.0:
                    hit = bool(random_gen.random() < pod)
                else:
                    hit = False

                window = state.get_window(buoy.display_name, target.id, buoy.n)
                window.append(hit)
                state.record_latest(buoy.display_name, target.id, hit)
