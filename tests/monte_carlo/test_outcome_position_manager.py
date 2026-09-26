"""
Suite 7: Output Management & Analytics (OUT-01 to OUT-02)
Verification of position sampling, snapshots, and event recordings.
"""

from __future__ import annotations

import pytest

from src.monte_carlo.detection_pipeline.events import DetectionEvent
from src.monte_carlo.output.outcome_position_manager import OutcomePositionManager
from tests.conftest import make_platform_state


# ==============================================================================
# OUT-01: Periodic and milestone platform state sampling
# ==============================================================================
def test_out_01_periodic_platform_state_sampling():
    """Verify position manager records structured coordinates and kinematics on events."""
    blue = make_platform_state("Blue_1", team="Blue", x=15.0, y=25.0)
    red = make_platform_state("Red_1", team="Red", x=50.0, y=60.0)
    manager = OutcomePositionManager(replication_id=1)

    # Record initial positions
    manager.record_initial_positions([blue, red], timestamp=0.0)
    assert len(manager.events) == 2
    initial_blue = manager.events[0]
    assert initial_blue["event_type"] == "initial_position"
    assert initial_blue["platform_id"] == "Blue_1"
    assert initial_blue["pos_x"] == 15.0
    assert initial_blue["pos_y"] == 25.0
    assert initial_blue["timestamp"] == 0.0

    # Record waypoint generation event
    manager.record_waypoint_generated(blue, timestamp=5.0)
    assert len(manager.events) == 3
    wp_event = manager.events[2]
    assert wp_event["event_type"] == "waypoint_generated"
    assert wp_event["timestamp"] == 5.0

    # Record time limit terminal event
    manager.record_time_limit([blue, red], timestamp=60.0)
    assert len(manager.events) == 5
    tl_events = [e for e in manager.events if e["event_type"] == "time_limit"]
    assert len(tl_events) == 2
    assert tl_events[0]["timestamp"] == 60.0


# ==============================================================================
# OUT-02: Instantaneous full-fleet spatial snapshot generation upon detection
# ==============================================================================
def test_out_02_instantaneous_detection_snapshot():
    """Verify instantaneous full-fleet snapshot is captured when detection occurs."""
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
    assert events_by_platform["Blue_1"]["detection_distance_m"] == 123.0
    assert events_by_platform["Blue_1"]["timestamp"] == 15.0

    assert events_by_platform["Red_1"]["event_type"] == "detection"
    assert events_by_platform["Red_1"]["detection_made"] is False
    assert events_by_platform["Red_1"]["target_platform_id"] is None
    assert events_by_platform["Red_1"]["detection_sensor_name"] is None
    assert events_by_platform["Red_1"]["timestamp"] == 15.0
