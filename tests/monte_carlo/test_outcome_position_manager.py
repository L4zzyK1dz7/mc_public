from __future__ import annotations

from src.monte_carlo.detection_pipeline.events import DetectionEvent
from src.monte_carlo.output.outcome_position_manager import OutcomePositionManager
from tests.conftest import make_platform_state


def test_record_detection_snapshot_records_all_platforms_at_detection_time():
    blue = make_platform_state("Blue_1", team="Blue", x=10.0, y=20.0)
    red = make_platform_state("Red_1", team="Red", x=40.0, y=50.0)
    manager = OutcomePositionManager(replication_id=7)

    detection = DetectionEvent(
        detecting_platform_id="Blue_1",
        target_platform_id="Red_1",
        sensor_name="Front Radar",
        distance_m=123.0,
    )

    manager.record_detection_snapshot([blue, red], detection, timestamp=15.0)

    events_by_platform = {event["platform_id"]: event for event in manager.events}

    assert len(events_by_platform) == 2
    assert events_by_platform["Blue_1"]["event_type"] == "detection"
    assert events_by_platform["Blue_1"]["detection_made"] is True
    assert events_by_platform["Blue_1"]["target_platform_id"] == "Red_1"
    assert events_by_platform["Blue_1"]["detection_sensor_name"] == "Front Radar"
    assert events_by_platform["Red_1"]["detection_made"] is False
    assert events_by_platform["Red_1"]["target_platform_id"] is None
    assert events_by_platform["Red_1"]["detection_sensor_name"] is None
