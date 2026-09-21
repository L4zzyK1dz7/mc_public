"""Registry mapping sensor type identifiers to their detection strategy.

This is the factory half of the Strategy pattern: adding support for a new
sensor type only requires registering a new strategy instance here, the
orchestrator in `detection_pipeline.pipeline` never needs to change.
"""

from __future__ import annotations

from typing import Optional

from src.monte_carlo.detection_pipeline.strategies.base import SensorDetectionStrategy
from src.monte_carlo.detection_pipeline.strategies.generic import (
    GenericSensorDetectionStrategy,
)

_STRATEGIES: dict[str, SensorDetectionStrategy] = {
    "generic": GenericSensorDetectionStrategy(),
    # "specific": SpecificSensorDetectionStrategy(),  # register once implemented
}


def get_strategy(sensor_type: str) -> Optional[SensorDetectionStrategy]:
    """Look up the detection strategy registered for a sensor type.

    Returns:
        The registered strategy, or None if the sensor type has no algorithm yet.
    """
    return _STRATEGIES.get(sensor_type)
