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
