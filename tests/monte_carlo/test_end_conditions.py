"""
Suite 5: End Conditions & Rule Resolution (END-01 to END-05)
Verification of termination conditions, facts generation, and priority resolution.
"""

from __future__ import annotations

from types import SimpleNamespace
import pytest

from src.monte_carlo.detection_pipeline.events import DetectionEvent
from src.monte_carlo.end_conditions import EndConditionFacts, check_end_conditions
from src.monte_carlo.end_conditions.facts import (
    all_platforms_detected,
    platforms_by_team,
    target_has_escaped,
)
from src.schemas.movement import IntruderSearchMovement, Waypoint
from src.schemas.simulation import World


# ==============================================================================
# END-01: Simulation horizon termination (time limit reached)
# ==============================================================================
def test_end_01_time_limit_reached():
    """Verify replication terminates when elapsed time / steps reach maximum."""
    facts = EndConditionFacts(
        detection=None,
        team_detection=None,
        completed_team=None,
        target_escaped=False,
    )
    # Step < max_steps - 1 -> No end condition
    assert check_end_conditions(
        current_time_sec=50.0, current_step=49, max_steps=100, facts=facts
    ) is None

    # Step >= max_steps - 1 -> time_limit
    end_condition = check_end_conditions(
        current_time_sec=100.0, current_step=99, max_steps=100, facts=facts
    )
    assert end_condition is not None
    assert end_condition.condition == "time_limit"
    assert end_condition.result == "not_detected"
    assert end_condition.timestamp_sec == 100.0


# ==============================================================================
# END-02: Spatial boundary escape detection
# ==============================================================================
def test_end_02_spatial_boundary_escape():
    """Verify intruder boundary escape detection when traversing beyond world bounds."""
    world = World(origin_x=0.0, origin_y=0.0, length=1000.0, height=1000.0)

    # Intruder inside world
    inside_target = SimpleNamespace(
        pos=Waypoint(x=500.0, y=100.0),
        movement_type=IntruderSearchMovement(),
    )
    assert target_has_escaped(target=inside_target, world=world) is False

    # Intruder at or below bottom boundary (y <= origin_y)
    escaped_target = SimpleNamespace(
        pos=Waypoint(x=500.0, y=0.0),
        movement_type=IntruderSearchMovement(),
    )
    assert target_has_escaped(target=escaped_target, world=world) is True

    # Check resolver yields target_escaped
    facts = EndConditionFacts(
        detection=None,
        team_detection=None,
        completed_team=None,
        target_escaped=True,
    )
    end_condition = check_end_conditions(
        current_time_sec=45.0, current_step=44, max_steps=100, facts=facts
    )
    assert end_condition is not None
    assert end_condition.condition == "target_escaped"
    assert end_condition.result == "not_detected"


# ==============================================================================
# END-03: Immediate replication termination under initial detection mode
# ==============================================================================
def test_end_03_initial_detection_termination():
    """Verify immediate replication completion upon the first confirmed detection event."""
    detection = DetectionEvent(
        detecting_platform_id="Blue_1",
        target_platform_id="Red_1",
        sensor_name="Radar",
        distance_m=150.0,
    )
    facts = EndConditionFacts(
        detection=detection,
        team_detection=None,
        completed_team=None,
        target_escaped=False,
    )
    end_condition = check_end_conditions(
        current_time_sec=25.0, current_step=24, max_steps=100, facts=facts
    )
    assert end_condition is not None
    assert end_condition.condition == "detection"
    assert end_condition.result == "detected"
    assert end_condition.detection == detection
    assert end_condition.timestamp_sec == 25.0


# ==============================================================================
# END-04: Multi-target team detection termination criteria
# ==============================================================================
def test_end_04_team_detection_termination():
    """Verify simulation terminates only upon confirmation of detection for all team members."""
    red_platforms = {"Red_1", "Red_2", "Red_3"}

    # 1 of 3 detected -> Not completed
    assert all_platforms_detected(
        required_platform_ids=red_platforms, detected_platform_ids={"Red_1"}
    ) is False

    # 2 of 3 detected -> Not completed
    assert all_platforms_detected(
        required_platform_ids=red_platforms, detected_platform_ids={"Red_1", "Red_2"}
    ) is False

    # 3 of 3 detected -> Completed!
    assert all_platforms_detected(
        required_platform_ids=red_platforms,
        detected_platform_ids={"Red_1", "Red_2", "Red_3"},
    ) is True

    # Check resolver produces team detection outcome
    detection = DetectionEvent("Blue_1", "Red_3", "Radar", 80.0)
    facts = EndConditionFacts(
        detection=None,
        team_detection=detection,
        completed_team="Red",
        target_escaped=False,
    )
    end_condition = check_end_conditions(
        current_time_sec=55.0, current_step=54, max_steps=100, facts=facts
    )
    assert end_condition is not None
    assert end_condition.condition == "red_team_detection"
    assert end_condition.result == "detected"


# ==============================================================================
# END-05: Conflict resolution and priority ranking
# ==============================================================================
def test_end_05_conflict_resolution_priority_ranking():
    """Verify deterministic priority: team detection > target escape > detection > time limit."""
    detection = DetectionEvent("Blue_1", "Red_1", "generic", 10.0)

    # When all 4 events occur at the final step, team detection wins
    facts_all = EndConditionFacts(
        detection=detection,
        team_detection=detection,
        completed_team="Blue",
        target_escaped=True,
    )
    end_all = check_end_conditions(
        current_time_sec=100.0, current_step=99, max_steps=100, facts=facts_all
    )
    assert end_all is not None
    assert end_all.condition == "blue_team_detection"

    # When target_escaped, detection, and time_limit occur, target escape wins over detection and time limit
    facts_escape_and_detection = EndConditionFacts(
        detection=detection,
        team_detection=None,
        completed_team=None,
        target_escaped=True,
    )
    end_escape = check_end_conditions(
        current_time_sec=100.0, current_step=99, max_steps=100, facts=facts_escape_and_detection
    )
    assert end_escape is not None
    assert end_escape.condition == "target_escaped"

    # When detection and time_limit occur, detection wins over time limit
    facts_detection_and_time = EndConditionFacts(
        detection=detection,
        team_detection=None,
        completed_team=None,
        target_escaped=False,
    )
    end_det = check_end_conditions(
        current_time_sec=100.0, current_step=99, max_steps=100, facts=facts_detection_and_time
    )
    assert end_det is not None
    assert end_det.condition == "detection"


def test_platforms_grouped_by_team_helper():
    """Verify platforms_by_team groups Blue and Red platforms."""
    blue = SimpleNamespace(team="Blue")
    red = SimpleNamespace(team="Red")
    grouped = platforms_by_team([blue, red])
    assert grouped["Blue"] == [blue]
    assert grouped["Red"] == [red]
