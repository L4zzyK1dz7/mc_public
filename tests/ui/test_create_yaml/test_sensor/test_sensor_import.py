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
    assert _x_axis_label("specific") == "x_values"
    assert _x_axis_label("Specific") == "x_values"


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
    df = pd.DataFrame({"x_values": [10.0, 20.0], "pod": [0.5, 0.8]})
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
