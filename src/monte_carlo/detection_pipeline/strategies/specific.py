"""Detection strategy for specific sensors (cross-product sector cross).

Evaluates whether the detecting platform's current step segment crossed any
historical trail segment of an opposing target, looking up probability of detection
(PoD) based on trail age (in hours) and rolling n independent trials per crossing.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from src.monte_carlo.detection_pipeline.events import DetectionEvent
from src.monte_carlo.detection_pipeline.segment_geometry import segments_cross
from src.monte_carlo.detection_pipeline.strategies.base import SensorDetectionStrategy

if TYPE_CHECKING:
    from src.monte_carlo.states.platform_states import PlatformState
    from src.schemas.sensor import SensorConfig


class SpecificSensorDetectionStrategy(SensorDetectionStrategy):
    """Detection algorithm for `SpecificSensorConfig` sensors."""

    def detect(
        self,
        sensor: SensorConfig,
        detecting_platform: PlatformState,
        target_platforms: list[PlatformState],
        current_time_sec: float,
        random_gen: np.random.Generator,
    ) -> list[DetectionEvent]:
        """Evaluate detection against all target platforms via trail segment crossing.

        Every target platform is evaluated exhaustively. For each target, historical
        trail segments within the sensor's maximum time table are tested in order.
        If a trail segment is crossed and passes the k-of-n roll for that crossing,
        a DetectionEvent is emitted and evaluation moves to the next target.

        Args:
            sensor: Sensor configuration (SpecificSensorConfig).
            detecting_platform: Platform mounting the specific sensor.
            target_platforms: Opposing candidate target platforms.
            current_time_sec: Current simulation time in seconds.
            random_gen: NumPy random generator.

        Returns:
            List of DetectionEvents emitted during this timestep.
        """
        blue_seg = detecting_platform.trail.latest_segment()
        if blue_seg is None or not sensor.x_values:
            return []

        max_age_hours = float(max(sensor.x_values))
        max_age_sec = max_age_hours * 3600.0

        events: list[DetectionEvent] = []

        for target in target_platforms:
            for red_seg in target.trail.segments_since(current_time_sec - max_age_sec):
                age_h = (current_time_sec - red_seg.time_sec) / 3600.0
                if age_h > max_age_hours:
                    continue

                pod = float(np.interp(age_h, sensor.x_values, sensor.pod))
                if pod <= 0.0:
                    continue

                if not segments_cross(blue_seg, red_seg):
                    continue

                rolls = random_gen.random(sensor.n)
                hits = int(np.sum(np.asarray(rolls) < pod))
                if hits >= sensor.k:
                    distance_m = math.hypot(
                        target.pos.x - detecting_platform.pos.x,
                        target.pos.y - detecting_platform.pos.y,
                    )
                    events.append(
                        DetectionEvent(
                            detecting_platform_id=detecting_platform.id,
                            target_platform_id=target.id,
                            sensor_name=sensor.display_name,
                            distance_m=distance_m,
                        )
                    )
                    break

        return events
