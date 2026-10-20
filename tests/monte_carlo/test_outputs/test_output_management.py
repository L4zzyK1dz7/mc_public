"""
Suite 7: Output Management & Analytics (OUT-03 to OUT-06)
Verification of detection managers, serialization pipelines, and summary analytics.
"""

from __future__ import annotations

from pathlib import Path
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
    generate_table_5,
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
    assert "# 4. End Condition Rates Across Replications" in content
    assert "# 5. Replication-Level Detection Outcomes" in content


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


# ==============================================================================
# OUT-07: Table 4 End Condition Rates & Table 5 Replication-Level Outcomes
# ==============================================================================
def test_out_07_generate_table_4_and_csv_section(tmp_path: Path):
    """Verify Table 4 calculates accurate end condition rates and serializes cleanly."""
    end_conditions = (
        ["detection"] * 5
        + ["time_limit"] * 3
        + ["target_escaped"] * 2
    )
    t4 = generate_table_4(end_conditions=end_conditions)
    assert "end_condition" in t4.columns
    assert "count" in t4.columns
    assert "rate" in t4.columns

    det_row = t4[t4["end_condition"] == "detection"].iloc[0]
    assert det_row["count"] == 5
    assert det_row["rate"] == pytest.approx(0.5)

    time_row = t4[t4["end_condition"] == "time_limit"].iloc[0]
    assert time_row["count"] == 3
    assert time_row["rate"] == pytest.approx(0.3)

    escape_row = t4[t4["end_condition"] == "target_escaped"].iloc[0]
    assert escape_row["count"] == 2
    assert escape_row["rate"] == pytest.approx(0.2)

    # All canonical conditions exist even with 0 count
    blue_det = t4[t4["end_condition"] == "blue_team_detection"].iloc[0]
    assert blue_det["count"] == 0
    assert blue_det["rate"] == 0.0

    # Serialization test verifying swapped order: Table 4 is End Conditions, Table 5 is Replication-Level Outcomes
    csv_out = tmp_path / "summary_stats.csv"
    write_summary_stats_csv([], csv_out, end_conditions=end_conditions)
    content = csv_out.read_text(encoding="utf-8")
    assert "# 4. End Condition Rates Across Replications" in content
    assert "# 5. Replication-Level Detection Outcomes" in content
    assert content.index("# 4. End Condition Rates Across Replications") < content.index(
        "# 5. Replication-Level Detection Outcomes"
    )
    assert "detection,5,0.5" in content

    # Empty conditions test
    empty_t4 = generate_table_4([])
    assert (empty_t4["count"] == 0).all()
    assert (empty_t4["rate"] == 0.0).all()

    # Table 5 replication outcomes test
    t5 = generate_table_5([])
    assert "detecting_platform_id" in t5.columns
    assert "target_platform_id" in t5.columns


# ==============================================================================
# OUT-08: Sonobuoy Field as Detector in Summary Stats (Tables 1, 2, 3, 5)
# ==============================================================================
def test_out_08_sonobuoy_field_detector_seeding_and_summary_stats():
    """Verify treating sonobuoy field as a detector across summary stats tables."""
    from src.monte_carlo.sonobuoy.events import SonobuoyDetectionEvent
    from src.schemas.sonobuoy import SonobuoyConfig

    buoy_a = SonobuoyConfig(
        display_name="Buoy A",
        x_m=100.0,
        y_m=200.0,
        k=1,
        n=1,
        distance_m=[0.0, 1000.0],
        pod=[1.0, 0.5],
        evaluation_modes=["single", "multi", "single_cycle"],
    )
    buoy_b = SonobuoyConfig(
        display_name="Buoy B",
        x_m=300.0,
        y_m=400.0,
        k=1,
        n=1,
        distance_m=[0.0, 1000.0],
        pod=[1.0, 0.5],
        evaluation_modes=["single", "single_cycle"],
    )
    buoys = [buoy_a, buoy_b]

    sensor = GenericSensorConfig(
        display_name="Radar",
        interval_time_sec=1.0,
        x_values=[0.0, 500.0],
        pod=[1.0, 0.5],
        k=1,
        n=1,
    )
    blue = make_platform_state("Blue_1", team="Blue", sensors=[sensor])
    red = make_platform_state("Red_1", team="Red")

    # Replication 0: sonobuoy single-cycle detects Red_1
    mgr_0 = OutcomeDetectionManager(replication_id=0)
    mgr_0.seed_pairs([blue, red], buoys)

    # 1 platform sensor + 2 field modes (single_cycle, multi) + 2 buoys in single mode = 5 rows
    assert len(mgr_0.rows) == 5
    mgr_0.record_sonobuoy_detection(
        SonobuoyDetectionEvent(
            timestamp_sec=60.0,
            detecting_id="sonobuoy_field",
            target_platform_id="Red_1",
            mode="single_cycle",
            distance_m=1500.0,
        )
    )
    mgr_0.set_end_condition("sonobuoy_single_cycle_detection")

    # Replication 1: no detection, ends with time_limit
    mgr_1 = OutcomeDetectionManager(replication_id=1)
    mgr_1.seed_pairs([blue, red], buoys)
    mgr_1.set_end_condition("time_limit")

    all_rows = mgr_0.rows + mgr_1.rows
    assert len(all_rows) == 10

    # Table 1: All agents (Blue_1, sonobuoy_field, Buoy A, Buoy B)
    t1 = generate_table_1(all_rows)
    field_t1 = t1[
        (t1["detecting_platform_id"] == "sonobuoy_field")
        & (t1["target_platform_id"] == "Red_1")
    ].iloc[0]
    assert field_t1["average_detections"] == pytest.approx(0.5)
    assert field_t1["average_detection_distance_km"] == pytest.approx(1.5)
    assert field_t1["average_detection_timestamp_minutes"] == pytest.approx(1.0)

    buoy_a_t1 = t1[
        (t1["detecting_platform_id"] == "Buoy A")
        & (t1["target_platform_id"] == "Red_1")
    ].iloc[0]
    assert buoy_a_t1["average_detections"] == pytest.approx(0.0)

    # Table 2: All sensors/modes
    t2 = generate_table_2(all_rows)
    sc_t2 = t2[
        (t2["detecting_platform_id"] == "sonobuoy_field")
        & (t2["sensor_name"] == "single_cycle")
    ].iloc[0]
    assert sc_t2["average_sensor_detections"] == pytest.approx(0.5)
    assert sc_t2["average_detection_distance_km"] == pytest.approx(1.5)

    multi_t2 = t2[
        (t2["detecting_platform_id"] == "sonobuoy_field")
        & (t2["sensor_name"] == "multi")
    ].iloc[0]
    assert multi_t2["average_sensor_detections"] == pytest.approx(0.0)

    single_t2 = t2[
        (t2["detecting_platform_id"] == "Buoy A")
        & (t2["sensor_name"] == "single")
    ].iloc[0]
    assert single_t2["average_sensor_detections"] == pytest.approx(0.0)

    # Table 3: Target overall detection probability
    t3 = generate_table_3(all_rows)
    assert t3[t3["target_platform_id"] == "Red_1"]["probability_of_at_least_one_detection"].iloc[0] == pytest.approx(0.5)

    # Table 5: Raw audit log
    t5 = generate_table_5(all_rows)
    assert len(t5) == 10
    detected_t5 = t5[t5["detection_outcome"]]
    assert len(detected_t5) == 1
    assert detected_t5["detecting_platform_id"].iloc[0] == "sonobuoy_field"
    assert detected_t5["sensor_name"].iloc[0] == "single_cycle"
    assert detected_t5["detection_distance_km"].iloc[0] == pytest.approx(1.5)

