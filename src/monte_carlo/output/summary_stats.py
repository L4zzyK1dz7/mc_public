"""
Summary statistics table generation for simulation results.

This module provides functions to generate aggregate statistics tables from
the per-replication detection outcome log (one row per detecting_platform /
sensor / target_platform combination, per replication - see
`OutcomeDetectionManager`). Used by SimulationResult to create the
`summary_stats.csv` output file.

ARCHITECTURAL RULE: "Validate at the Boundary, Trust in the Core"
This is a BOUNDARY LAYER component that transforms core simulation output
for reporting and analysis.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Sequence

import pandas as pd

if TYPE_CHECKING:
    from src.schemas.output import DetectionOutcomeEvent


def _build_detection_outcomes_df(
    detection_outcomes: list[DetectionOutcomeEvent],
) -> pd.DataFrame:
    """Convert the raw detection outcome log into a DataFrame with boundary unit conversions."""
    df = pd.DataFrame(detection_outcomes)
    if df.empty:
        return df

    # Unit conversions: metres -> kilometres, seconds -> minutes
    df["detection_distance_km"] = df["detection_distance_m"] / 1000.0
    df["detection_timestamp_minutes"] = df["detection_timestamp_sec"] / 60.0
    return df


def _first_detection_per_group(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Collapse multiple/simultaneous sensor detections within a group into one row.

    All of a platform's sensors share the platform's position, so simultaneous
    detections always report the same distance - picking one representative
    detection (earliest timestamp, sensor_name breaks ties) keeps distance and
    timestamp paired and prevents a platform being counted more than once per
    replication (which would push a probability above 1.0).
    """
    detected = df[df["detection_outcome"]]
    if detected.empty:
        return detected

    detected = detected.sort_values(["detection_timestamp_minutes", "sensor_name"])
    return detected.groupby(group_cols, as_index=False).first()


def generate_table_1(
    detection_outcomes: Optional[list[DetectionOutcomeEvent]] = None,
) -> pd.DataFrame:
    """
    Per (detecting_platform_id, target_platform_id), the probability the platform
    detected the target at all in a replication (any of its sensors), averaged
    across replications. Simultaneous/multiple sensor detections within the same
    replication are collapsed into a single event first, so a platform is never
    counted as detecting more than once per replication.

    Args:
        detection_outcomes: List of detection outcome rows (one per platform/sensor/target
            combination per replication).

    Returns:
        DataFrame with columns: detecting_platform_id, target_platform_id,
        average_detections, average_detection_distance_km, average_detection_timestamp_minutes
    """
    columns = [
        "detecting_platform_id",
        "target_platform_id",
        "average_detections",
        "average_detection_distance_km",
        "average_detection_timestamp_minutes",
    ]

    df = _build_detection_outcomes_df(detection_outcomes or [])
    if df.empty:
        return pd.DataFrame({col: pd.Series(dtype="object") for col in columns})

    group_cols = ["replication_id", "detecting_platform_id", "target_platform_id"]

    # Every (replication, platform, target) combination that was seeded, whether or
    # not it was ever detected - the denominator for the probability.
    universe = df[group_cols].drop_duplicates()
    representative = _first_detection_per_group(df, group_cols)

    per_replication = universe.merge(representative, on=group_cols, how="left")
    per_replication["detection_outcome"] = per_replication["detection_outcome"].fillna(
        False
    ).astype(bool)

    grouped = (
        per_replication.groupby(["detecting_platform_id", "target_platform_id"])
        .agg(
            average_detections=("detection_outcome", "mean"),
            average_detection_distance_km=("detection_distance_km", "mean"),
            average_detection_timestamp_minutes=(
                "detection_timestamp_minutes",
                "mean",
            ),
        )
        .reset_index()
    )
    return grouped[columns]


def generate_table_2(
    detection_outcomes: Optional[list[DetectionOutcomeEvent]] = None,
) -> pd.DataFrame:
    """
    E.g.
        1 detecting platform and 2 target platforms:
        blue_1 (sensor_1 and sensor_2 equipped):
            red_1:
                sensor_1: average detections, average detection distance, average detection timestamp
                sensor_2: average detections, average detection distance, average detection timestamp
            red_2:
                sensor_1: average detections, average detection distance, average detection timestamp
                sensor_2: average detections, average detection distance, average detection timestamp

    """
    columns = [
        "detecting_platform_id",
        "sensor_name",
        "target_platform_id",
        "average_sensor_detections",
        "average_detection_distance_km",
        "average_detection_timestamp_minutes",
    ]

    df = _build_detection_outcomes_df(detection_outcomes or [])
    if df.empty:
        return pd.DataFrame({col: pd.Series(dtype="object") for col in columns})

    grouped = (
        df.groupby(["detecting_platform_id", "sensor_name", "target_platform_id"])
        .agg(
            average_sensor_detections=("detection_outcome", "mean"),
            average_detection_distance_km=("detection_distance_km", "mean"),
            average_detection_timestamp_minutes=(
                "detection_timestamp_minutes",
                "mean",
            ),
        )
        .reset_index()
    )
    return grouped[columns]


def generate_table_3(
    detection_outcomes: Optional[list[DetectionOutcomeEvent]] = None,
) -> pd.DataFrame:
    """Generates a table summarizing the empirical probability of at least one detection
    for each target platform.

    For each replication, a target counts as "detected" if ANY detecting platform/sensor
    pair against it succeeded (multiple detecting platforms are treated as multiple
    simultaneous trials within that one replication). That per-replication boolean is
    then averaged across replications to give an empirical probability, without assuming
    independence between sensors/platforms the way the analytic complement rule would.

    Args:
        detection_outcomes: List of detection outcome rows.

    Returns:
        DataFrame with columns: target_platform_id, probability_of_at_least_one_detection
    """
    columns = ["target_platform_id", "probability_of_at_least_one_detection"]

    df = _build_detection_outcomes_df(detection_outcomes or [])
    if df.empty:
        return pd.DataFrame({col: pd.Series(dtype="object") for col in columns})

    any_detected_per_replication = df.groupby(["replication_id", "target_platform_id"])[
        "detection_outcome"
    ].any()
    probability = (
        any_detected_per_replication.groupby("target_platform_id")
        .mean()
        .reset_index(name="probability_of_at_least_one_detection")
    )
    return probability[columns]


CANONICAL_END_CONDITIONS: list[str] = [
    "time_limit",
    "target_escaped",
    "barrier_crossed",
    "world_crossed",
    "detection",
    "counter_detection",
    "blue_team_detection",
    "red_team_detection",
    "sonobuoy_single_cycle_detection",
    "sonobuoy_multi_detection",
    "sonobuoy_single_detection",
]



def generate_table_4(
    end_conditions: Optional[Sequence[str]] = None,
    detection_outcomes: Optional[list[DetectionOutcomeEvent]] = None,
) -> pd.DataFrame:
    """Generate Table 4: End condition rates and counts across all replications.

    Args:
        end_conditions: List of end condition string identifiers for each replication.
        detection_outcomes: Optional list of detection outcome events to fallback on if
            end_conditions is not directly provided.

    Returns:
        DataFrame with columns: end_condition, count, rate
    """
    columns = ["end_condition", "count", "rate"]

    conditions_list: list[str] = []
    if end_conditions is not None:
        conditions_list = [c for c in end_conditions if c]
    elif detection_outcomes:
        df = _build_detection_outcomes_df(detection_outcomes)
        if (
            not df.empty
            and "replication_id" in df.columns
            and "end_condition" in df.columns
        ):
            rep_end = df[["replication_id", "end_condition"]].dropna().drop_duplicates(
                subset=["replication_id"]
            )
            conditions_list = rep_end["end_condition"].tolist()

    total_replications = len(conditions_list)
    counts = (
        pd.Series(conditions_list).value_counts()
        if total_replications > 0
        else pd.Series(dtype="int64")
    )

    all_known_conditions = list(CANONICAL_END_CONDITIONS)
    for cond in counts.index:
        if cond not in all_known_conditions:
            all_known_conditions.append(str(cond))

    rows = []
    for cond in all_known_conditions:
        cnt = int(counts.get(cond, 0))
        rate = float(cnt / total_replications) if total_replications > 0 else 0.0
        rows.append({"end_condition": cond, "count": cnt, "rate": rate})

    if not rows:
        return pd.DataFrame({col: pd.Series(dtype="object") for col in columns})
    return pd.DataFrame(rows)


def generate_table_5(
    detection_outcomes: Optional[list[DetectionOutcomeEvent]] = None,
) -> pd.DataFrame:
    """Generate Table 5: Per-replication detection outcome for every (detecting_platform, sensor,
    target_platform) combination - the raw log the other tables are aggregated from.
    """
    columns = [
        "replication_id",
        "detecting_platform_id",
        "target_platform_id",
        "sensor_name",
        "detection_outcome",
        "detection_distance_km",
        "detection_timestamp_minutes",
        "end_condition",
    ]

    df = _build_detection_outcomes_df(detection_outcomes or [])
    if df.empty:
        return pd.DataFrame({col: pd.Series(dtype="object") for col in columns})

    return df[columns]


def write_summary_stats_csv(
    detection_outcomes: list[DetectionOutcomeEvent],
    output_path: Optional[Path] = None,
    end_conditions: Optional[Sequence[str]] = None,
) -> Path:
    """Write all summary statistics tables to summary_stats.csv with section headers."""
    if output_path is None:
        output_path = Path("summary_stats.csv")

    # Generate all tables
    table1 = generate_table_1(detection_outcomes)
    table2 = generate_table_2(detection_outcomes)
    table3 = generate_table_3(detection_outcomes)
    table4 = generate_table_4(
        end_conditions=end_conditions, detection_outcomes=detection_outcomes
    )
    table5 = generate_table_5(detection_outcomes)

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
        f.write("# 4. End Condition Rates Across Replications\n")
        table4.to_csv(f, index=False)
        f.write("\n")

        # Table 5
        f.write("# 5. Replication-Level Detection Outcomes\n")
        table5.to_csv(f, index=False)

    return output_path
