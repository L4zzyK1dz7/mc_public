"""
Module for holding and exporting simulation results.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pandas as pd

from src.monte_carlo.output.file_utils import get_next_run_folder
from src.monte_carlo.output.raw_positions import build_positions_df
from src.monte_carlo.output.summary_stats import write_summary_stats_csv

if TYPE_CHECKING:
    from src.schemas.output import SimulationResults

logger = logging.getLogger(__name__)


def aggregate_and_output_results(
    simulation_results: SimulationResults,
    output_dir: Optional[Path] = None,
    has_sonobuoys: Optional[bool] = None,
):
    """
    Aggregate the simulation results and export them to the specified output directory: 'outcomes/' directory.

    1. Export tables as summary_stats.csv - Summary statistics of the simulation results.
    2. Export raw_positions.csv - Positional data of all platforms events
    3. Export sonobuoy_detections.csv - Multistatic sonobuoy detection events (if sonobuoys configured)

    Args:
        simulation_results: List of simulation results from all replications.
        output_dir: Directory where the aggregated results will be saved.
        has_sonobuoys: Optional flag indicating whether sonobuoys are configured.
    """


    if output_dir is None:
        run_output_dir = get_next_run_folder()
    else:
        run_output_dir = output_dir

    run_output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Export summary statistics
    detection_outcomes = [
        outcome
        for replication_result in simulation_results
        for result in replication_result.values()
        for outcome in result["detection_outcomes"]
    ]
    end_conditions = [
        result["end_condition"]
        for replication_result in simulation_results
        for result in replication_result.values()
    ]
    summary_stats_path = run_output_dir / "summary_stats.csv"
    summary_stats_logged = write_summary_stats_csv(
        detection_outcomes=detection_outcomes,
        output_path=summary_stats_path,
        end_conditions=end_conditions,
    )
    logger.info("Summary statistics written to %s", summary_stats_logged)

    raw_positions_path = run_output_dir / "raw_positions.csv"
    position_events = [
        event
        for replication_result in simulation_results
        for result in replication_result.values()
        for event in result["platform_position_events"]
    ]
    df = build_positions_df(position_events)
    df.to_csv(raw_positions_path, index=False)
    logger.info("Wrote raw_positions.csv to %s", raw_positions_path)
    logger.info(
        "Position values in kilometers (km), speed in km/h, timestamp in minutes"
    )

    # 3. Export sonobuoy detections if buoys exist
    buoys_present = has_sonobuoys
    if buoys_present is None:
        sonobuoys_dir = run_output_dir / "input_data" / "sonobuoys"
        buoys_present = sonobuoys_dir.exists() and bool(list(sonobuoys_dir.glob("*.csv")))

    if buoys_present:
        sonobuoy_events = [
            event
            for replication_result in simulation_results
            for result in replication_result.values()
            for event in result.get("sonobuoy_detections", [])
        ]
        sonobuoy_columns = [
            "replication_id",
            "timestamp_minutes",
            "mode",
            "detecting_id",
            "target_platform_id",
        ]
        sonobuoy_df = (
            pd.DataFrame(sonobuoy_events)
            if sonobuoy_events
            else pd.DataFrame(columns=sonobuoy_columns)
        )
        sonobuoy_path = run_output_dir / "sonobuoy_detections.csv"
        sonobuoy_df[sonobuoy_columns].to_csv(sonobuoy_path, index=False)
        logger.info("Wrote sonobuoy_detections.csv to %s", sonobuoy_path)

    logger.info(
        "Aggregated results as summary_stats.csv and exported raw_positions.csv saved to %s",
        run_output_dir,
    )

