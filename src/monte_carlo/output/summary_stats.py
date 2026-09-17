"""
Summary statistics table generation for simulation results.

This module provides functions to generate aggregate statistics tables from
confirmed detection events and replication summaries. Used by
SimulationResult to create the `summary_stats.csv` output file.

ARCHITECTURAL RULE: "Validate at the Boundary, Trust in the Core"
This is a BOUNDARY LAYER component that transforms core simulation output
for reporting and analysis.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd

if TYPE_CHECKING:
    from src.monte_carlo.monte_carlo import SimulationResults


def generate_table_1(detection_events_log: list[dict[str, Any]] = None) -> pd.DataFrame:
    """
    Groups detections by (detecting_agent_id, target_agent_id) per replication
    to compute per-replication count/distance/timestamp, then averages across
    replications.

    Args:
        detection_events_log: List of detection event dictionaries.

    Returns:
        DataFrame with columns: detecting_agent_id, target_agent_id,
        average_detections, average_detection_distance, average_detection_timestampgroups detection by d
    """
    df = pd.DataFrame(
        {
            "detecting_platform_id": pd.Series(dtype="str"),
            "target_platform_id": pd.Series(dtype="str"),
            "average_detections": pd.Series(dtype="float"),
            "average_detection_distance": pd.Series(dtype="float"),
            "average_detection_timestamp": pd.Series(dtype="float"),
        }
    )

    return df


def generate_table_2(detection_events_log: list[dict[str, Any]] = None) -> pd.DataFrame:
    """ """
    df = pd.DataFrame(
        {
            "detecting_platform_id": pd.Series(dtype="str"),
            "sensor_name": pd.Series(dtype="str"),
            "target_platform_id": pd.Series(dtype="str"),
            "average_detections": pd.Series(dtype="float"),
            "average_detection_distance": pd.Series(dtype="float"),
            "average_detection_timestamp": pd.Series(dtype="float"),
        }
    )

    return df


def generate_table_3(detection_events_log: list[dict[str, Any]] = None) -> pd.DataFrame:
    """Generates a table summarizing the probability of at least one detection for each target platform.

    Calculate P(None detects) = 1 - P(A detection)
    P(One detects) = Product each platform P(None detects)

    Args:
        detection_events_log: List of detection event dictionaries.

    Returns:
        DataFrame with columns: target_platform_id, probability_of_at_least_one_detection
    """
    df = pd.DataFrame(
        {
            "target_platform_id": pd.Series(dtype="str"),
            "probability_of_at_least_one_detection": pd.Series(dtype="float"),
        }
    )

    return df


def generate_table_4(
    detection_events_log: list[dict[str, Any]], simulation_results: SimulationResults
) -> pd.DataFrame:
    """ """
    df = pd.DataFrame(
        {
            "detecting_platform_id": pd.Series(dtype="str"),
            "target_platform_id": pd.Series(dtype="str"),
            "average_detections": pd.Series(dtype="float"),
            "average_detection_distance": pd.Series(dtype="float"),
            "average_detection_timestamp": pd.Series(dtype="float"),
        }
    )

    return df


def write_summary_stats_csv(
    detection_events_log: list[dict[str, Any]],
    simulation_results: SimulationResults,
    output_path: Optional[Path] = None,
) -> Path:

    if output_path is None:
        output_path = Path("summary_stats.csv")

    # Generate all tables
    table1 = generate_table_1(detection_events_log)
    table2 = generate_table_2(detection_events_log)
    table3 = generate_table_3(detection_events_log)
    table4 = generate_table_4(detection_events_log, simulation_results)

    # Write to file with section headers
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        # Table 1
        f.write("# 1. Average Detections Across All Agents\n")
        table1.to_csv(f, index=False)
        f.write("\n")

        # Table 2
        f.write("# 2. Average Detections Across All Agent Sensors\n")
        table2.to_csv(f, index=False)
        f.write("\n")

        # Table 3
        f.write("# 3. Probability of At Least One Detection\n")
        table3.to_csv(f, index=False)
        f.write("\n")

        # Table 4
        f.write("# 4. Replication-Level Detection Outcomes\n")
        table4.to_csv(f, index=False)

    return output_path
