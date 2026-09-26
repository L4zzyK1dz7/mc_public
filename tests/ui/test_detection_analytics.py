"""Unit tests for src.ui.plotting.detection_analytics."""

from __future__ import annotations

import pandas as pd
import pytest

from src.ui.plotting.detection_analytics import (
    build_detection_histogram,
    build_fleet_convergence_chart,
    build_interaction_heatmap,
    build_pairwise_convergence_chart,
    compute_running_probability,
)


@pytest.fixture
def sample_outcomes_df() -> pd.DataFrame:
    # 10 replications, 2 observers (Blue_1, Blue_2), 2 targets (Red_1, Red_2)
    rows = []
    for r in range(10):
        # Blue_1 vs Red_1: detected on even replications
        rows.append(
            {
                "replication_id": r,
                "detecting_platform_id": "Blue_1",
                "target_platform_id": "Red_1",
                "sensor_name": "Radar",
                "detection_outcome": (r % 2 == 0),
                "detection_distance_km": 1.5 if (r % 2 == 0) else None,
                "detection_timestamp_minutes": 25.0 + r if (r % 2 == 0) else None,
            }
        )
        # Blue_1 vs Red_2: detected on r >= 5
        rows.append(
            {
                "replication_id": r,
                "detecting_platform_id": "Blue_1",
                "target_platform_id": "Red_2",
                "sensor_name": "Radar",
                "detection_outcome": (r >= 5),
                "detection_distance_km": 2.0 if (r >= 5) else None,
                "detection_timestamp_minutes": 50.0 + r if (r >= 5) else None,
            }
        )
    return pd.DataFrame(rows)


def test_compute_running_probability(sample_outcomes_df: pd.DataFrame):
    df = compute_running_probability(sample_outcomes_df, total_replications=10)
    assert len(df) == 10
    assert "p_det" in df.columns
    assert "ci_lower" in df.columns
    assert "ci_upper" in df.columns
    assert 0.0 <= df["p_det"].iloc[-1] <= 1.0


def test_build_fleet_convergence_chart(sample_outcomes_df: pd.DataFrame):
    fig = build_fleet_convergence_chart(sample_outcomes_df)
    assert fig is not None
    # Traces: Overall Fleet + Red_1 + Red_2 = 3 traces
    trace_names = [trace.name for trace in fig.data]
    assert any("Overall Fleet" in name for name in trace_names)
    assert any("Red_1" in name for name in trace_names)
    assert any("Red_2" in name for name in trace_names)


def test_build_interaction_heatmap():
    table_1 = pd.DataFrame(
        [
            {
                "detecting_platform_id": "Blue_1",
                "target_platform_id": "Red_1",
                "average_detections": 0.85,
            },
            {
                "detecting_platform_id": "Blue_1",
                "target_platform_id": "Red_2",
                "average_detections": 0.10,
            },
            {
                "detecting_platform_id": "Blue_2",
                "target_platform_id": "Red_1",
                "average_detections": 0.05,
            },
            {
                "detecting_platform_id": "Blue_2",
                "target_platform_id": "Red_2",
                "average_detections": 0.90,
            },
        ]
    )
    fig = build_interaction_heatmap(table_1)
    assert fig is not None
    assert len(fig.data) == 1
    assert fig.data[0].type == "heatmap"


def test_build_pairwise_convergence_chart(sample_outcomes_df: pd.DataFrame):
    filtered = sample_outcomes_df[sample_outcomes_df["target_platform_id"] == "Red_1"]
    fig = build_pairwise_convergence_chart(
        filtered, observer_name="Blue_1", target_name="Red_1", total_replications=10
    )
    assert fig is not None
    assert len(fig.data) >= 2  # CI band + Line


def test_build_detection_histogram(sample_outcomes_df: pd.DataFrame):
    fig_time = build_detection_histogram(
        sample_outcomes_df,
        metric_col="detection_timestamp_minutes",
        title="Time-to-Detection",
        xlabel="Minutes",
    )
    assert fig_time is not None
    assert len(fig_time.data) == 1
    assert fig_time.data[0].type == "histogram"

    # Test empty returns None
    empty_fig = build_detection_histogram(
        pd.DataFrame(), metric_col="missing", title="None", xlabel="None"
    )
    assert empty_fig is None
