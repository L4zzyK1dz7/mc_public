"""Terminal-condition facts and resolution for one simulation replication."""

from .models import EndCondition, EndConditionFacts, EndConditionType, SimulationOutcome
from .resolver import check_end_conditions

__all__ = [
    "EndCondition",
    "EndConditionFacts",
    "EndConditionType",
    "SimulationOutcome",
    "check_end_conditions",
]