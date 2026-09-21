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
