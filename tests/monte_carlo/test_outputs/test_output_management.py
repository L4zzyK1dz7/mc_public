"""
Suite 7: Output Management & Analytics (OUT-03 to OUT-06)
Verification of detection managers, serialization pipelines, and summary analytics.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from src.monte_carlo.detection_pipeline.events import DetectionEvent
from src.monte_carlo.output.file_utils import get_next_run_folder
from src.monte_carlo.output.outcome_detection_manager import OutcomeDetectionManager
from src.monte_carlo.output.raw_positions import CSV_COLUMN_ORDER, build_positions_df
from src.monte_carlo.output.summary_stats import (
    generate_table_1,
    generate_table_2,
    generate_table_3,
    generate_table_4,
    write_summary_stats_csv,
)
from src.schemas.output import DetectionOutcomeEvent, PlatformPositionEvent
from tests.conftest import make_platform_state
from src.schemas.sensor import GenericSensorConfig


# ==============================================================================
# OUT-03: Detection record payload schema compliance upon logging events
# ==============================================================================
def test_out_03_outcome_detection_manager_payload_schema():
    """Verify OutcomeDetectionManager emits schema-compliant detection outcome rows."""
    sensor = GenericSensorConfig(
        display_name="Front Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 500.0],
        pod=[1.0, 0.5],
        k=1,
        n=1,
    )
    blue = make_platform_state("Blue_1", team="Blue", sensors=[sensor])
    red = make_platform_state("Red_1", team="Red")

    manager = OutcomeDetectionManager(replication_id=3)
    manager.seed_pairs([blue, red])

    # Default seeded state: not detected
    rows = manager.rows
    assert len(rows) == 1
    row = rows[0]
    assert row["replication_id"] == 3
    assert row["detecting_platform_id"] == "Blue_1"
    assert row["sensor_name"] == "Front Radar"
    assert row["target_platform_id"] == "Red_1"
    assert row["detection_outcome"] is False
    assert row["detection_distance_m"] is None
    assert row["detection_timestamp_sec"] is None
    assert row["end_condition"] is None

    # Record confirmed detection
    det_event = DetectionEvent(
        detecting_platform_id="Blue_1",
        target_platform_id="Red_1",
        sensor_name="Front Radar",
        distance_m=250.0,
    )
    manager.record_detection(det_event, timestamp=12.5)
    manager.set_end_condition("detection")

    updated_row = manager.rows[0]
    assert updated_row["detection_outcome"] is True
    assert updated_row["detection_distance_m"] == 250.0
    assert updated_row["detection_timestamp_sec"] == 12.5
    assert updated_row["end_condition"] == "detection"


# ==============================================================================
# OUT-04: Serialization and schema validity for exported simulation artefacts
# ==============================================================================
def test_out_04_serialization_positions_df_and_summary_csv(tmp_path: Path):
    """Verify build_positions_df schema validity and write_summary_stats_csv export."""
    # Test build_positions_df
    events: list[PlatformPositionEvent] = [
        {
            "replication_id": 1,
            "event_type": "initial_position",
            "platform_id": "Blue_1",
            "team": "Blue",
            "timestamp": 0.0,
            "pos_x": 1000.0,
            "pos_y": 2000.0,
            "heading": 90.0,
            "speed": 10.0,
            "waypoint_x": 1500.0,
            "waypoint_y": 2500.0,
            "status": "active",
            "detecting_platform_id": None,
            "target_platform_id": None,
            "detection_made": False,
            "detection_sensor_name": None,
            "detection_distance_m": None,
        }
    ]
    df = build_positions_df(events)
    assert list(df.columns) == list(CSV_COLUMN_ORDER)
    assert df["pos_x_km"].iloc[0] == pytest.approx(1.0)
    assert df["pos_y_km"].iloc[0] == pytest.approx(2.0)
    assert df["speed_kmh"].iloc[0] == pytest.approx(36.0)

    # Test write_summary_stats_csv
    sample_outcomes: list[DetectionOutcomeEvent] = [
        {
            "replication_id": 0,
            "detecting_platform_id": "Blue_1",
            "sensor_name": "Radar",
            "target_platform_id": "Red_1",
            "detection_outcome": True,
            "detection_distance_m": 500.0,
            "detection_timestamp_sec": 30.0,
            "end_condition": "detection",
        }
    ]
    csv_file = tmp_path / "summary_stats.csv"
    written_path = write_summary_stats_csv(sample_outcomes, csv_file)
    assert written_path.exists()
    content = written_path.read_text(encoding="utf-8")
    assert "# 1. Average Detections Across All Agents" in content
    assert "# 2. Average Detections Across All Agent Sensors" in content
    assert "# 3. Probability of At Least One Detection" in content
    assert "# 4. Replication-Level Detection Outcomes" in content


# ==============================================================================
# OUT-05: Statistical metric calculations from aggregated replication sample
# ==============================================================================
def test_out_05_statistical_metric_calculations():
    """Verify P_det = 0.650 and mean detection times from sample of 100 replications."""
    outcomes: list[DetectionOutcomeEvent] = []
    # 65 detections (each at 1000m / 1km and 60s / 1 min)
    for rep in range(65):
        outcomes.append(
            {
                "replication_id": rep,
                "detecting_platform_id": "Blue_1",
                "sensor_name": "Radar",
                "target_platform_id": "Red_1",
                "detection_outcome": True,
                "detection_distance_m": 1000.0,
                "detection_timestamp_sec": 60.0,
                "end_condition": "detection",
            }
        )
    # 35 non-detections
    for rep in range(65, 100):
        outcomes.append(
            {
                "replication_id": rep,
                "detecting_platform_id": "Blue_1",
                "sensor_name": "Radar",
                "target_platform_id": "Red_1",
                "detection_outcome": False,
                "detection_distance_m": None,
                "detection_timestamp_sec": None,
                "end_condition": "time_limit",
            }
        )

    # Table 1: P_det across all agent sensors
    t1 = generate_table_1(outcomes)
    assert len(t1) == 1
    assert t1["average_detections"].iloc[0] == pytest.approx(0.650)
    assert t1["average_detection_distance_km"].iloc[0] == pytest.approx(1.0)
    assert t1["average_detection_timestamp_minutes"].iloc[0] == pytest.approx(1.0)

    # Table 2: sensor-level breakdown
    t2 = generate_table_2(outcomes)
    assert len(t2) == 1
    assert t2["average_sensor_detections"].iloc[0] == pytest.approx(0.650)

    # Table 3: probability of at least one detection
    t3 = generate_table_3(outcomes)
    assert len(t3) == 1
    assert t3["probability_of_at_least_one_detection"].iloc[0] == pytest.approx(0.650)


# ==============================================================================
# OUT-06: Safe directory hierarchy generation
# ==============================================================================
def test_out_06_safe_directory_hierarchy_generation(tmp_path: Path):
    """Verify get_next_run_folder safely generates deeply nested parent directories."""
    nested_base = tmp_path / "deeply" / "nested" / "output_root"
    assert not nested_base.exists()

    run1 = get_next_run_folder(nested_base)
    assert nested_base.exists()
    assert run1.exists()
    assert run1.is_dir()
    assert "run_001" in run1.name

    run2 = get_next_run_folder(nested_base)
    assert run2.exists()
    assert "run_002" in run2.name
