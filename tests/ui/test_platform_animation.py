from __future__ import annotations

from typing import cast
from src.ui.plotting.platform_animation import (
    PlatformAnimationData,
    SimulationTiming,
    SonobuoyDefinition,
    build_animation,
)


def test_animation_slider_uses_minutes_for_display():
    platforms = {
        "Blue_1": cast(
            PlatformAnimationData,
            {
                "positions": [
                    {
                        "platform_id": "Blue_1",
                        "team": "blue",
                        "timestamp_sec": 0.0,
                        "pos_x_km": 0.0,
                        "pos_y_km": 0.0,
                        "waypoint_x_km": 0.0,
                        "waypoint_y_km": 0.0,
                        "detection_made": False,
                        "target_platform_id": None,
                        "detection_sensor_name": None,
                        "detection_distance_km": None,
                    },
                    {
                        "platform_id": "Blue_1",
                        "team": "blue",
                        "timestamp_sec": 120.0,
                        "pos_x_km": 1.0,
                        "pos_y_km": 1.0,
                        "waypoint_x_km": 1.0,
                        "waypoint_y_km": 1.0,
                        "detection_made": False,
                        "target_platform_id": None,
                        "detection_sensor_name": None,
                        "detection_distance_km": None,
                    },
                ],
                "sensors": [],
                "detections": [],
            },
        )
    }

    timing: SimulationTiming = {"time_limit_sec": 120.0, "world_timestep_sec": 60.0}
    figure = build_animation(platforms, timing)

    slider = figure.layout.sliders[0]
    assert slider.currentvalue.prefix == "Time (min): "
    assert slider.steps[0].label == "0.00"
    assert slider.steps[-1].label == "2.00"


def test_sector_points_generates_closed_wedge():
    from src.ui.plotting.platform_animation import _sector_points

    xs, ys = _sector_points(
        centre_x=10.0,
        centre_y=20.0,
        start_deg=0.0,
        end_deg=90.0,
        radius_km=5.0,
    )

    # First point is centre
    assert xs[0] == 10.0 and ys[0] == 20.0
    # Last point closes back to centre
    assert xs[-1] == 10.0 and ys[-1] == 20.0
    # First arc point is at 0 degrees (x = centre_x + radius, y = centre_y)
    assert round(xs[1], 3) == 15.0
    assert round(ys[1], 3) == 20.0
    # Last arc point is at 90 degrees (x = centre_x, y = centre_y + radius)
    assert round(xs[-2], 3) == 10.0
    assert round(ys[-2], 3) == 25.0
    assert len(xs) == 50  # centre + 48 arc points + centre


def test_sector_points_rotates_with_heading():
    from src.ui.plotting.platform_animation import _sector_points

    # Sector is 0 to 90 deg relative to platform, platform heading is 90 deg (facing North).
    # World arc should span 90 deg to 180 deg (from North to West).
    xs, ys = _sector_points(
        centre_x=0.0,
        centre_y=0.0,
        start_deg=0.0,
        end_deg=90.0,
        radius_km=10.0,
        heading_deg=90.0,
    )

    # First arc point should be at 90 deg: x=0, y=10
    assert round(xs[1], 3) == 0.0
    assert round(ys[1], 3) == 10.0
    # Last arc point should be at 180 deg: x=-10, y=0
    assert round(xs[-2], 3) == -10.0
    assert round(ys[-2], 3) == 0.0


def test_animation_frames_dynamically_rotate_sensor():
    from src.ui.plotting.platform_animation import build_animation

    platforms = {
        "Blue_1": {
            "positions": [
                {
                    "platform_id": "Blue_1",
                    "team": "blue",
                    "timestamp_sec": 0.0,
                    "pos_x_km": 0.0,
                    "pos_y_km": 0.0,
                    "waypoint_x_km": 10.0,
                    "waypoint_y_km": 0.0,
                    "heading": 0.0,  # Moving East
                    "detection_made": False,
                    "target_platform_id": None,
                    "detection_sensor_name": None,
                    "detection_distance_km": None,
                },
                {
                    "platform_id": "Blue_1",
                    "team": "blue",
                    "timestamp_sec": 60.0,
                    "pos_x_km": 0.0,
                    "pos_y_km": 0.0,
                    "waypoint_x_km": 0.0,
                    "waypoint_y_km": 10.0,
                    "heading": 90.0,  # Turned North
                    "detection_made": False,
                    "target_platform_id": None,
                    "detection_sensor_name": None,
                    "detection_distance_km": None,
                },
            ],
            "sensors": [
                {
                    "platform_id": "Blue_1",
                    "name": "Forward Radar",
                    "fov_start_deg": 0.0,
                    "fov_end_deg": 90.0,
                    "range_km": 10.0,
                }
            ],
            "detections": [],
        }
    }
    platforms = {"Blue_1": cast(PlatformAnimationData, platforms["Blue_1"])}
    timing: SimulationTiming = {"time_limit_sec": 60.0, "world_timestep_sec": 60.0}
    figure = build_animation(platforms, timing)

    # Frame 0 (t=0.0): Heading 0 deg -> arc starts at (10, 0)
    frame_0_sensor = figure.frames[0].data[2]  # trace 0: trail, 1: platform, 2: sensor
    assert round(frame_0_sensor.x[1], 2) == 10.0
    assert round(frame_0_sensor.y[1], 2) == 0.0

    # Frame 1 (t=60.0): Heading 90 deg -> arc starts at (0, 10)
    frame_1_sensor = figure.frames[1].data[2]
    assert round(frame_1_sensor.x[1], 2) == 0.0
    assert round(frame_1_sensor.y[1], 2) == 10.0


def test_animation_slider_respects_end_time_sec():
    platforms = {
        "Blue_1": {
            "display_name": "Carrier",
            "positions": [
                {
                    "platform_id": "Blue_1",
                    "team": "blue",
                    "timestamp_sec": 0.0,
                    "pos_x_km": 0.0,
                    "pos_y_km": 0.0,
                    "waypoint_x_km": 0.0,
                    "waypoint_y_km": 0.0,
                    "heading": 0.0,
                    "detection_made": False,
                    "target_platform_id": None,
                    "detection_sensor_name": None,
                    "detection_distance_km": None,
                },
                {
                    "platform_id": "Blue_1",
                    "team": "blue",
                    "timestamp_sec": 180.0,
                    "pos_x_km": 1.0,
                    "pos_y_km": 1.0,
                    "waypoint_x_km": 1.0,
                    "waypoint_y_km": 1.0,
                    "heading": 0.0,
                    "detection_made": False,
                    "target_platform_id": None,
                    "detection_sensor_name": None,
                    "detection_distance_km": None,
                },
            ],
            "sensors": [],
            "detections": [],
        }
    }

    platforms = {"Blue_1": cast(PlatformAnimationData, platforms["Blue_1"])}
    # Time limit is 1 hour (3600s), but replication finished at 180s (3 min)
    timing: SimulationTiming = {
        "time_limit_sec": 3600.0,
        "world_timestep_sec": 60.0,
        "end_time_sec": 180.0,
    }
    figure = build_animation(platforms, timing)

    slider = figure.layout.sliders[0]
    assert slider.steps[0].label == "0.00"
    assert slider.steps[-1].label == "3.00"


def test_animation_renders_display_names():
    platforms = {
        "Blue_1": {
            "display_name": "Defender One",
            "positions": [
                {
                    "platform_id": "Blue_1",
                    "team": "blue",
                    "timestamp_sec": 0.0,
                    "pos_x_km": 0.0,
                    "pos_y_km": 0.0,
                    "waypoint_x_km": 0.0,
                    "waypoint_y_km": 0.0,
                    "heading": 0.0,
                    "detection_made": True,
                    "target_platform_id": "Red_1",
                    "detection_sensor_name": "Sonar",
                    "detection_distance_km": 2.0,
                }
            ],
            "sensors": [
                {
                    "platform_id": "Blue_1",
                    "name": "Sonar",
                    "fov_start_deg": 0.0,
                    "fov_end_deg": 360.0,
                    "range_km": 5.0,
                }
            ],
            "detections": [
                {
                    "timestamp_sec": 0.0,
                    "detecting_platform_id": "Blue_1",
                    "target_platform_id": "Red_1",
                    "sensor_name": "Sonar",
                    "distance_m": 2000.0,
                }
            ],
        },
        "Red_1": {
            "display_name": "Intruder Alpha",
            "positions": [
                {
                    "platform_id": "Red_1",
                    "team": "red",
                    "timestamp_sec": 0.0,
                    "pos_x_km": 2.0,
                    "pos_y_km": 0.0,
                    "waypoint_x_km": 2.0,
                    "waypoint_y_km": 0.0,
                    "heading": 180.0,
                    "detection_made": False,
                    "target_platform_id": None,
                    "detection_sensor_name": None,
                    "detection_distance_km": None,
                }
            ],
            "sensors": [],
            "detections": [],
        },
    }

    typed_platforms = {
        pid: cast(PlatformAnimationData, p) for pid, p in platforms.items()
    }
    timing: SimulationTiming = {
        "time_limit_sec": 60.0,
        "world_timestep_sec": 60.0,
        "end_time_sec": 0.0,
    }
    figure = build_animation(typed_platforms, timing)

    # Check trace names use display names
    trace_names = [trace.name for trace in figure.data]
    assert "Defender One trail" in trace_names
    assert "Defender One (blue)" in trace_names
    assert "Defender One Sonar" in trace_names
    assert "Intruder Alpha trail" in trace_names
    assert "Intruder Alpha (red)" in trace_names

    # Check detection jump button uses display names
    buttons = figure.layout.updatemenus[0].buttons
    jump_buttons = [b for b in buttons if "Jump to detection" in b.label]
    assert len(jump_buttons) == 1
    assert "Defender One -> Intruder Alpha" in jump_buttons[0].label


def test_build_animation_with_sonobuoys_and_detections():
    platforms = {
        "Red_1": cast(
            PlatformAnimationData,
            {
                "display_name": "Target Red",
                "positions": [
                    {
                        "platform_id": "Red_1",
                        "team": "red",
                        "timestamp_sec": 0.0,
                        "pos_x_km": 10.0,
                        "pos_y_km": 10.0,
                        "waypoint_x_km": 10.0,
                        "waypoint_y_km": 10.0,
                        "detection_made": False,
                        "target_platform_id": None,
                        "detection_sensor_name": None,
                        "detection_distance_km": None,
                    },
                    {
                        "platform_id": "Red_1",
                        "team": "red",
                        "timestamp_sec": 60.0,
                        "pos_x_km": 12.0,
                        "pos_y_km": 10.0,
                        "waypoint_x_km": 12.0,
                        "waypoint_y_km": 10.0,
                        "detection_made": False,
                        "target_platform_id": None,
                        "detection_sensor_name": None,
                        "detection_distance_km": None,
                    },
                ],
                "sensors": [],
                "detections": [],
            },
        )
    }
    timing: SimulationTiming = {"time_limit_sec": 60.0, "world_timestep_sec": 60.0}
    sonobuoys: list[SonobuoyDefinition] = [{"name": "Buoy_Alpha", "x_km": 50.0, "y_km": 50.0}]
    sb_detections = [
        {
            "replication_id": 0,
            "timestamp_minutes": 1.0,
            "mode": "single_cycle",
            "detecting_id": "Buoy_Alpha",
            "target_platform_id": "Red_1",
        }
    ]

    figure = build_animation(
        platforms, timing, sonobuoys=sonobuoys, sonobuoy_detections=sb_detections
    )

    # Verify buoy trace is present as blue square
    buoy_traces = [t for t in figure.data if t.name == "Buoy_Alpha"]
    assert len(buoy_traces) == 1
    assert buoy_traces[0].marker.symbol == "square"
    assert buoy_traces[0].marker.color == "#08306b"
    assert buoy_traces[0].x[0] == 50.0
    assert buoy_traces[0].y[0] == 50.0

    # Verify no coverage rings/wedges were drawn for buoy
    assert not hasattr(buoy_traces[0], "fill") or buoy_traces[0].fill is None

    # Verify frame data preserves trace count
    assert len(figure.frames) >= 1
    for frame in figure.frames:
        assert len(frame.data) == len(figure.data)

    # Verify detection jump button and annotation
    buttons = figure.layout.updatemenus[0].buttons
    jump_buttons = [b for b in buttons if "Jump to detection" in b.label]
    assert len(jump_buttons) == 1
    assert "Buoy_Alpha (single_cycle) -> Target Red" in jump_buttons[0].label

    assert len(figure.layout.annotations) == 1
    assert "Buoy_Alpha (single_cycle) -> Target Red" in figure.layout.annotations[0].text



