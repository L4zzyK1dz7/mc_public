from types import SimpleNamespace

from src.monte_carlo.detection_pipeline.events import DetectionEvent
from src.monte_carlo.end_conditions import EndConditionFacts, check_end_conditions
from src.monte_carlo.end_conditions.facts import (
    all_platforms_detected,
    platforms_by_team,
    target_has_escaped,
)
from src.schemas.simulation import World


def test_priority_is_team_detection_then_escape_then_detection_then_time_limit():
    detection = DetectionEvent("Blue_1", "Red_1", "generic", 10.0)

    end_condition = check_end_conditions(
        current_time_sec=1.0,
        current_step=0,
        max_steps=1,
        facts=EndConditionFacts(
            detection=detection,
            team_detection=detection,
            completed_team="Blue",
            target_escaped=True,
        ),
    )

    assert end_condition is not None
    assert end_condition.condition == "blue_team_detection"
    assert end_condition.result == "detected"
    assert end_condition.detection == detection


def test_team_detection_requires_every_required_platform():
    assert (
        all_platforms_detected(
            required_platform_ids={"Red_1", "Red_2"},
            detected_platform_ids={"Red_1"},
        )
        is False
    )


def test_platforms_are_grouped_by_team():
    blue = SimpleNamespace(team="Blue")
    red = SimpleNamespace(team="Red")

    grouped = platforms_by_team([blue, red])

    assert grouped["Blue"] == [blue]
    assert grouped["Red"] == [red]
    assert (
        all_platforms_detected(
            required_platform_ids={"Red_1", "Red_2"},
            detected_platform_ids={"Red_1", "Red_2", "Blue_1"},
        )
        is True
    )


def test_target_escape_uses_world_boundaries():
    world = World(origin_x=0.0, origin_y=0.0, length=100.0, height=100.0)
    target = SimpleNamespace(pos=SimpleNamespace(x=101.0, y=50.0))

    assert target_has_escaped(target=target, world=world) is True
