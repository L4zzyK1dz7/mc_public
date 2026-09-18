from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np

from src.monte_carlo.detection_pipeline.pipeline import detect
from src.monte_carlo.end_conditions import EndCondition, check_end_conditions
from src.monte_carlo.load_configuration import load_config_from_yaml, load_seeds
from src.monte_carlo.output.aggregate_results import aggregate_and_output_results
from src.monte_carlo.output.file_utils import get_next_run_folder
from src.monte_carlo.output.outcome_position_manager import OutcomePositionManager
from src.monte_carlo.states.movement_manager import MovementManager
from src.monte_carlo.states.platform_states import initialise_platform_states
from src.schemas.output import SimulationResult, SimulationResults

if TYPE_CHECKING:
    from src.monte_carlo.states.platform_states import (
        PlatformState,  # Ignore at runtime to prevent circular imports
    )
    from src.schemas.simulation import (
        ConfigData,  # Ignore at runtime to prevent circular imports
    )

# Initialise logging
logger = logging.getLogger(__name__)


def _execute_single_replication(
    config_data: ConfigData,
    movement_manager: MovementManager,
    outcome_manager: OutcomePositionManager,
    seed: Optional[int] = None,
) -> SimulationResult:
    """
    Run a single replication of the Monte Carlo simulation.

    Args:
        config_data: ConfigData,
        movement_manager: MovementManager,
        outcome_manager: OutcomePositionManager,
        seed: Optional seed for reproducibility.

    Returns:
        The result of the replication.
    """

    # Set the random seed if provided
    random_gen = np.random.default_rng(seed)

    # Initialise platform states and  MovementManager
    platform_states: list[PlatformState] = initialise_platform_states(
        config_data, random_gen, movement_manager
    )
    outcome_manager.record_initial_positions(platform_states)

    # Initialise

    # Calculate nummber of total timesteps
    movement_manager.current_simulation_time = 0.0
    max_steps = int(
        round(
            config_data.simulation.time_limit_sec / config_data.simulation.timestep_sec
        )
    )

    sim_time_sec: float = 0.0
    end_condition: Optional[EndCondition] = None

    # Main timestepping loop
    for step in range(max_steps):
        sim_time_sec += config_data.simulation.timestep_sec

        # Update MovementManager with the current simulation time
        movement_manager.current_simulation_time += config_data.simulation.timestep_sec

        # Move Platforms
        waypoint_platforms = movement_manager.move_platforms(
            platform_states, sim_time_sec, config_data, random_gen
        )

        # Record platform positional snapshot for all platforms that generated waypoints
        for platform in waypoint_platforms:
            outcome_manager.record_waypoint_generated(platform, sim_time_sec)

        # Perform detection based on the current platform states.
        detection = detect(
            platform_states=platform_states,
            current_time_sec=sim_time_sec,
        )

        end_condition = check_end_conditions(
            current_time_sec=sim_time_sec,
            current_step=step,
            max_steps=max_steps,
            detection=detection,
        )

        if end_condition is None:
            continue  # Everything below is skipped if no end condition is met, noting to record, move to next timestep

        if end_condition.condition == "detection":
            assert end_condition.detection is not None

            # Iterate through platform states to find the detecting platform.
            detecting_platform = next(
                platform
                for platform in platform_states
                if platform.id == end_condition.detection.detecting_platform_id
            )
            outcome_manager.record_detection(
                platform=detecting_platform,
                timestamp=end_condition.timestamp_sec,
                target_platform_id=end_condition.detection.target_platform_id,
                sensor_name=end_condition.detection.sensor_name,
                distance_m=end_condition.detection.distance_m,
            )
        elif end_condition.condition == "time_limit":
            outcome_manager.record_time_limit(
                platform_states,
                end_condition.timestamp_sec,
            )

        break  # Exit the main timestepping loop once an end condition is reached

    assert end_condition is not None

    simulation_result: SimulationResult = {
        "result": end_condition.result,
        "end_condition": end_condition.condition,
        "platform_position_events": outcome_manager.events,
    }
    logger.info("Simulation Result: %s", simulation_result)
    return simulation_result


def _execute_monte_carlo(
    number_of_replications: int,
    config_data: ConfigData,
    seeds: Optional[list[int]] = None,
) -> SimulationResults:
    """
    Execute the complete Monte Carlo simulation until an end condition is met.
    """

    simulation_results: SimulationResults = []

    movement_manager = MovementManager()  # initialise the movement manager

    # Main replication loop
    for replication_id in range(number_of_replications):
        logger.info("Starting replication %d", replication_id)

        # Get seeds if available
        seed = seeds[replication_id] if seeds is not None else None
        outcome_manager = OutcomePositionManager(replication_id)

        replication_result = _execute_single_replication(
            config_data, movement_manager, outcome_manager, seed
        )
        # Process the replication result as needed
        logger.info("Finished replication %d", replication_id)

        # Store the replication result
        simulation_results.append({replication_id: replication_result})

    return simulation_results  # Replace with actual aggregation of results


def run_simulation(
    config_path: Path, output_dir: Optional[Path] = None, verbose: bool = False
) -> int:
    """
    Orchestrate the Monte Carlo simulation by performing the following steps:
    1. Load configuration
    2. Initialise Seeds
    3. Run Main Monte Carlo simulation.
    4. Aggregate and Output the simulation results.

    Args:
        config_path: Path to the config.yaml file.
        output_dir: Optional directory for output files. Defaults to data/outputs.
        verbose: If True, print DEBUG level logs.

    Returns:
        0 if successful, 1 if error occurred.
    """

    # === 1. Validate and load configuration ===
    # Validate config file exists
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        return 1

    logger.info(f"Loading configuration from: {config_path}")
    config_data: ConfigData = load_config_from_yaml(config_path)

    # === 2. Initialise Seeds ===
    if config_data.simulation.seeds_file:
        seeds_path = config_path.parent / "seeds.txt"
        try:
            seeds = load_seeds(
                seeds_path, replications=config_data.simulation.replications
            )
        except Exception as e:
            logger.error(f"Failed to load seeds: {e}")
        return 1

    # If no seeds were loaded from a file, generate them now. This makes the run reproducible later by saving these generated seeds.
    seed_generator = np.random.default_rng()
    seeds: list[int] = seed_generator.integers(
        low=0, high=2**32 - 1, size=config_data.simulation.replications
    ).tolist()
    logger.info(
        "Generated %d new random seeds for this run.",
        config_data.simulation.replications,
    )

    # Determine output directory if not already specified, to save seeds.
    if output_dir is None:
        run_output_dir = get_next_run_folder()
    else:
        run_output_dir = output_dir

    # Always save the generated seeds for reproducibility
    run_output_dir.mkdir(parents=True, exist_ok=True)
    seeds_output_path = run_output_dir / "seeds.txt"
    with open(seeds_output_path, "w", encoding="utf-8") as f:
        for seed in seeds:
            f.write(f"{seed}\n")
    logger.info("Saved generated seeds to %s", seeds_output_path)

    # === 3. Run Main Monte Carlo simulation ===
    simulation_results = _execute_monte_carlo(
        config_data.simulation.replications, seeds=seeds, config_data=config_data
    )

    # === 4. Aggregate and Output the simulation results ===
    aggregate_and_output_results(simulation_results, run_output_dir)

    logger.info("Monte Carlo completed successfully.")

    return 0
