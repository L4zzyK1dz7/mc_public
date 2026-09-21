"""Detection strategy for generic sensors.

1. Check sensor interval time
2. Check Target in FOV
3. Get PoD value based on distance to the target
4. Evaluate PoD against Rnd number and record result into sliding window
5. Evaluate K-of-n
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from src.monte_carlo.detection_pipeline.events import DetectionEvent
from src.monte_carlo.detection_pipeline.sensor_state import SensorRuntimeState
from src.monte_carlo.detection_pipeline.strategies.base import SensorDetectionStrategy

if TYPE_CHECKING:
    from src.monte_carlo.states.platform_states import PlatformState
    from src.schemas.sensor import SensorConfig


class GenericSensorDetectionStrategy(SensorDetectionStrategy):
    """Detection algorithm for `GenericSensorConfig` sensors."""

    def detect(
        self,
        sensor: SensorConfig,
        detecting_platform: PlatformState,
        target_platforms: list[PlatformState],
        current_time_sec: float,
        random_gen: np.random.Generator,
    ) -> list[DetectionEvent]:
        """
        Perform detection for the given sensor on the detecting platform against every target.

        Every target is evaluated exhaustively (no early return) so simultaneous
        detections against multiple targets in the same timestep are all captured,
        and every target's k-of-n sliding window is updated every timestep.

        Args:
            sensor: The sensor configuration.
            detecting_platform: The platform on which the sensor is mounted.
            target_platforms: List of potential target platforms to detect.
            current_time_sec: The current simulation time in seconds.
            random_gen: Random generator passed to detection strategies for stochastic evaluation.

        Returns:
            A list of DetectionEvents (possibly empty) for this timestep.
        """

        # State persists on the platform (keyed by sensor identity) so interval
        # timing and k-of-n history survive across timesteps within a replication.
        state: SensorRuntimeState = detecting_platform.sensor_states.setdefault(
            id(sensor), SensorRuntimeState()
        )

        # 1. Check sensor interval time against simulation time; exit early if not ready yet
        if current_time_sec < state.next_eval_time_sec:
            return []
        state.next_eval_time_sec = current_time_sec + sensor.interval_time_sec

        platform_heading_deg = self._heading_deg(detecting_platform)
        fov_start = getattr(sensor, "fov_start_angle", 0.0)
        fov_end = getattr(sensor, "fov_end_angle", 360.0)

        detections: list[DetectionEvent] = []

        for target in target_platforms:
            distance_m = math.hypot(
                target.pos.x - detecting_platform.pos.x,
                target.pos.y - detecting_platform.pos.y,
            )
            window = state.get_window(target.id, sensor.n)

            # 2. Check target in FOV; a miss still consumes a slot in the sliding window
            if not self._in_fov(
                detecting_platform, target, platform_heading_deg, fov_start, fov_end
            ):
                window.append(False)
                continue

            # 3. Get PoD value based on distance to the target
            pod = (
                float(np.interp(distance_m, sensor.x_values, sensor.pod))
                if sensor.x_values and sensor.pod
                else 0.0
            )

            # 4. Evaluate PoD against Rnd number and record result into sliding window
            window.append(bool(random_gen.random() < pod))

            # 5. Evaluate K-of-n
            if sum(window) >= sensor.k:
                detections.append(
                    DetectionEvent(
                        detecting_platform_id=detecting_platform.id,
                        target_platform_id=target.id,
                        sensor_name=sensor.display_name,
                        distance_m=distance_m,
                    )
                )

        return detections

    @staticmethod
    def _heading_deg(platform: PlatformState) -> float:
        """World-frame heading of the platform, in degrees."""
        heading = platform.wp_properties.heading
        return math.degrees(math.atan2(heading[1], heading[0])) % 360.0

    @staticmethod
    def _in_fov(
        platform: PlatformState,
        target: PlatformState,
        platform_heading_deg: float,
        fov_start: float,
        fov_end: float,
    ) -> bool:
        """Whether `target` falls within the sensor's field of view, relative to heading."""
        bearing_deg = (
            math.degrees(
                math.atan2(target.pos.y - platform.pos.y, target.pos.x - platform.pos.x)
            )
            % 360.0
        )
        relative_angle = (bearing_deg - platform_heading_deg) % 360.0

        if fov_start <= fov_end:
            return fov_start <= relative_angle <= fov_end
        return relative_angle >= fov_start or relative_angle <= fov_end  # FOV wraps 360
