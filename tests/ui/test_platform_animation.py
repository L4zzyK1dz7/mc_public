from __future__ import annotations

from src.ui.plotting.platform_animation import build_animation


def test_animation_slider_uses_minutes_for_display():
    platforms = {
        "Blue_1": {
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
        }
    }

    timing = {"time_limit_sec": 120.0, "world_timestep_sec": 60.0}
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

    timing = {"time_limit_sec": 60.0, "world_timestep_sec": 60.0}
    figure = build_animation(platforms, timing)

    # Frame 0 (t=0.0): Heading 0 deg -> arc starts at (10, 0)
    frame_0_sensor = figure.frames[0].data[2]  # trace 0: trail, 1: platform, 2: sensor
    assert round(frame_0_sensor.x[1], 2) == 10.0
    assert round(frame_0_sensor.y[1], 2) == 0.0

    # Frame 1 (t=60.0): Heading 90 deg -> arc starts at (0, 10)
    frame_1_sensor = figure.frames[1].data[2]
    assert round(frame_1_sensor.x[1], 2) == 0.0
    assert round(frame_1_sensor.y[1], 2) == 10.0

