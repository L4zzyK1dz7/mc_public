"""
Unit tests for src/ui/services/performance_table.py.
"""

from __future__ import annotations

import pandas as pd
from src.ui.services.performance_table import (
    extract_valid_sensor_points,
    parse_sensor_csv,
    x_axis_label,
)


def test_x_axis_label():
    assert x_axis_label("generic") == "distance_m"
    assert x_axis_label("GENERIC") == "distance_m"
    assert x_axis_label("specific") == "x_values"
    assert x_axis_label("") == "x_values"


def test_parse_sensor_csv_standard():
    df = pd.DataFrame({"distance_m": [10.0, 50.0], "pod": [0.8, 0.2]})
    parsed, msg = parse_sensor_csv(df, "generic")
    assert msg is None
    assert list(parsed.columns) == ["x_values", "pod"]
    assert parsed["x_values"].tolist() == [10.0, 50.0]


def test_parse_sensor_csv_mapped_range():
    df = pd.DataFrame({"range_m": [100.0], "pod": [0.5]})
    parsed, msg = parse_sensor_csv(df, "generic")
    assert msg is not None
    assert "mapped to distance_m" in msg
    assert parsed["x_values"].tolist() == [100.0]


def test_parse_sensor_csv_auto_mapping_first_two_columns():
    df = pd.DataFrame({"dist": [200.0], "probability": [0.7], "extra": [1.0]})
    parsed, msg = parse_sensor_csv(df, "generic")
    assert msg is not None
    assert "auto-mapped" in msg
    assert parsed["x_values"].tolist() == [200.0]


def test_parse_sensor_csv_insufficient_columns():
    df = pd.DataFrame({"single_column": [10.0]})
    parsed, msg = parse_sensor_csv(df, "generic")
    assert parsed.empty
    assert msg is not None and "must include" in msg


def test_extract_valid_sensor_points_valid():
    df = pd.DataFrame({"x_values": [0.0, 100.0], "pod": [1.0, 0.5]})
    x, pod, err = extract_valid_sensor_points(df)
    assert err is None
    assert x == [0.0, 100.0]
    assert pod == [1.0, 0.5]


def test_extract_valid_sensor_points_empty():
    df = pd.DataFrame({"x_values": [], "pod": []})
    x, pod, err = extract_valid_sensor_points(df)
    assert err is not None and "No valid sensor rows found" in err
    assert x == []
    assert pod == []


def test_extract_valid_sensor_points_out_of_bounds():
    df = pd.DataFrame({"x_values": [10.0], "pod": [1.2]})
    x, pod, err = extract_valid_sensor_points(df)
    assert err == "All pod values must be between 0 and 1."
    assert x == []
    assert pod == []
