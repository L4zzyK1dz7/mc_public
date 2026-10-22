from __future__ import annotations

import pandas as pd
from src.ui.views.create_platform_sensors import (
    _extract_valid_sensor_points,
    _parse_sensor_csv,
    _x_axis_label,
)


def test_x_axis_label():
    assert _x_axis_label("generic") == "distance_m"
    assert _x_axis_label("Generic") == "distance_m"
    assert _x_axis_label("specific") == "time_late_hours"
    assert _x_axis_label("Specific") == "time_late_hours"


def test_parse_sensor_csv_with_distance_m_column():
    df = pd.DataFrame({"distance_m": [100.0, 500.0], "pod": [0.9, 0.4]})
    parsed, msg = _parse_sensor_csv(df, sensor_type="generic")
    assert msg is None
    assert list(parsed.columns) == ["x_values", "pod"]
    assert len(parsed) == 2
    assert parsed["x_values"].tolist() == [100.0, 500.0]


def test_parse_sensor_csv_with_range_m_column():
    df = pd.DataFrame({"range_m": [100.0, 500.0], "pod": [0.9, 0.4]})
    parsed, msg = _parse_sensor_csv(df, sensor_type="generic")
    assert msg is not None
    assert "mapped to distance_m" in msg
    assert list(parsed.columns) == ["x_values", "pod"]
    assert len(parsed) == 2


def test_parse_sensor_csv_with_exact_columns():
    df = pd.DataFrame({"time_late_hours": [10.0, 20.0], "pod": [0.5, 0.8]})
    parsed, msg = _parse_sensor_csv(df, sensor_type="specific")
    assert msg is None
    assert list(parsed.columns) == ["x_values", "pod"]
    assert len(parsed) == 2


def test_parse_sensor_csv_with_alternative_columns():
    df = pd.DataFrame({"col1": [10.0, 20.0], "col2": [0.5, 0.8]})
    parsed, msg = _parse_sensor_csv(df, sensor_type="generic")
    assert msg is not None
    assert list(parsed.columns) == ["x_values", "pod"]
    assert len(parsed) == 2


def test_extract_valid_sensor_points_validates_pod_bounds():
    df = pd.DataFrame({"x_values": [10.0, 20.0], "pod": [0.5, 1.5]})
    x, pod, err = _extract_valid_sensor_points(df)
    assert err == "All pod values must be between 0 and 1."
    assert x == []
    assert pod == []


def test_create_sensor_file_specific_writes_time_late_hours(tmp_path):
    from src.schemas.sensor import SpecificSensorConfig
    from src.ui.services.create_yaml import create_sensor_file

    sensor = SpecificSensorConfig(
        display_name="TrailSensor",
        interval_time_sec=10.0,
        x_values=[1.0, 2.0],
        pod=[0.8, 0.4],
        k=1,
        n=1,
    )
    platform_dir = tmp_path / "platform_1"
    ok = create_sensor_file(sensor, platform_dir)
    assert ok is True

    csv_path = platform_dir / "sensors" / "specific" / "TrailSensor.csv"
    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8")
    assert "time_late_hours,pod" in content
    assert "1.0,0.8" in content
