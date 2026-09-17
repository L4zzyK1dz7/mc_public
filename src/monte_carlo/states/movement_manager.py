"""
Movement Manager interface to handle platform state movement patterns and waypoint execution within the Monte Carlo simulation.

"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

import numpy as np

from src.schemas.movement import Waypoint

if TYPE_CHECKING:
    from src.monte_carlo.states.platform_states import PlatformState
    from src.schemas.platform import MovementType
    from src.schemas.simulation import ConfigData


class RecordWaypoint(TypedDict):
    """Records the waypoint reached data for raw_positions.csv"""

    platform_pos: Waypoint
    wp_pos: Waypoint
    heading: float  # Convert from vector to degrees using arctan2


@dataclass
class WpProperties:
    pos: Waypoint  # Current position of the Waypoint
    arrival_time: float  # Expected arrival time at the waypoint

    distance: float  # Total distance from initial position to waypoint
    heading: np.ndarray  # Vectorised heading to the waypoint e.g. [dx, dy]
    total_duration: float  # Total time required to reach the waypoint
    step_distance: (
        float  # Distance covered in one timestep based on speed_mps and timestep_sec
    )


@dataclass
class MovementManager:
    """Engine that updates PlatformState positions based on individual Movement Types"""

    current_simulation_time: float = 0.0

    def record_waypoint(
        self,
        platform_pos: Waypoint,
        wp_pos: Waypoint,
        heading: np.ndarray,
    ) -> RecordWaypoint:

        heading_deg: float = float(np.degrees(np.arctan2(heading[1], heading[0])) % 360)

        return RecordWaypoint(
            platform_pos=platform_pos,
            wp_pos=wp_pos,
            heading=heading_deg,
        )

    def calculate_wp_properties(
        self,
        current_pos: Waypoint,
        wp: Waypoint,
        speed_mps: float,
        timestep_sec: float,  # ConfigData timestep_sec
        sim_time: float,
    ) -> WpProperties:

        # return early is platform was decided not to move with speed as 0
        if speed_mps == 0.0:
            return WpProperties(
                pos=wp,
                arrival_time=sim_time,
                distance=0.0,
                heading=np.array([0.0, 0.0]),
                total_duration=0.0,
                step_distance=0.0,
            )

        dx = wp.x - current_pos.x
        dy = wp.y - current_pos.y
        distance = math.hypot(dx, dy)

        wp_heading = self.calculate_heading(current_pos, wp)

        total_duration: float = distance / speed_mps

        # Step towards WP is determined by speed and the timestep
        step_distance: float = speed_mps * timestep_sec

        arrival_time: np.float64 = self.calculate_wp_arrival_time(
            speed_mps=speed_mps,
            distance=distance,
            simulation_time=sim_time,
        )

        return WpProperties(
            pos=wp,
            arrival_time=float(arrival_time),
            distance=distance,
            heading=wp_heading,
            total_duration=total_duration,
            step_distance=step_distance,
        )

    def get_waypoint(
        self,
        movement_type: MovementType,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> Waypoint:
        """
        Get the next waypoint for the platform based on the given movement type.

        Args:
            movement_type: The type of movement to apply based on the PlatformState.
            config_data: The configuration data for the simulation based on user input. This provides information about the environment in which the platform is operating.
            random_gen: The random number generator to use for stochastic movement calculations.

        Returns:
            Waypoint: The new position of the platform.
        """

        new_pos = movement_type.get_next_position(
            config_data=config_data,
            random_gen=random_gen,
        )

        return new_pos

    def calculate_wp_arrival_time(
        self,
        speed_mps: float,
        distance: float,
        simulation_time: float = 0.0,
    ) -> np.float64:
        """
        Calculate the expected arrival time to reach the given waypoint from the current position.

        Args:
            speed_mps: The speed at which the platform is moving in meters per second.
            distance: The distance to the target waypoint.
            simulation_time: The current simulation time in seconds.

        Returns:
            float: The expected arrival time to reach the waypoint in seconds.
        """
        assert distance > 0, (
            "Distance must be greater than zero to calculate arrival time."
        )

        return simulation_time + (np.float64(distance) / speed_mps)

    def calculate_heading(
        self,
        current_position: Waypoint,
        next_position: Waypoint,
    ) -> np.ndarray:
        """Computes the vector heading from the current position to the next position.

        Returns:
            np.ndarray: The vector heading from the current position to the next position.
        """

        # Assert quickly if the current and next positions are the same
        assert (
            current_position.x != next_position.x
            or current_position.y != next_position.y
        ), "Current position and next position must not be the same."

        start = np.array([current_position.x, current_position.y])
        end = np.array([next_position.x, next_position.y])

        vector = end - start
        magnitude = np.linalg.norm(vector)  # Calculate the magnitude of the vector
        if magnitude > 0:
            normalised_vector = (
                vector / magnitude
            )  # Normalise the vector to get the direction
        else:
            normalised_vector = np.array([0.0, 0.0])

        return normalised_vector

    def update_position(
        self,
        current_pos: Waypoint,
        heading: np.ndarray,
        step_distance: float,
    ) -> Waypoint:
        """
        Updates the platform's position based on its current position, heading, and step distance.

        Args:
            current_pos: The current position of the platform.
            heading: The heading direction in which the platform should move.
            step_distance: The distance the platform should move along the heading direction.

        Returns:
            Waypoint: The updated position of the platform.
        """

        # Calculate the new position based on the current position, heading, and step distance
        new_x = current_pos.x + (heading[0] * step_distance)
        new_y = current_pos.y + (heading[1] * step_distance)

        new_pos = Waypoint(x=new_x, y=new_y)
        return new_pos

    def move_platforms(
        self,
        platform_states: list[PlatformState],
        sim_time_sec: float,
        config_data: ConfigData,
        random_gen: np.random.Generator,
    ) -> list[PlatformState]:
        """
        Using a time based approach to determine if the waypoint has been reached.

        args:
            platform_states: The list of all platform states.
            sim_time_sec: The current simulation time.

        returns:
            list[PlatformState]: Platforms that received a newly generated waypoint.

        """
        waypoint_generated_for: list[PlatformState] = []

        # Iterate through all platform states to check if any have reached their waypoint
        for p in platform_states:
            # Return early is platform has speed 0, meaning it should not move
            if p.speed_mps == 0.0:
                continue

            # Waypoint reached is determined by checking arrival time with simulation time
            if p.wp_properties.arrival_time <= sim_time_sec:
                # Waypoint reached then generate new waypoint, distance, direction and next_arrival_time
                new_wp: Waypoint = self.get_waypoint(
                    p.movement_type, config_data, random_gen
                )

                wp_properties: WpProperties = self.calculate_wp_properties(
                    current_pos=p.pos,
                    wp=new_wp,
                    speed_mps=p.speed_mps,
                    timestep_sec=config_data.simulation.timestep_sec,
                    sim_time=sim_time_sec,
                )

                # Update new waypoint information in the platform state
                p.wp_properties = wp_properties
                waypoint_generated_for.append(p)

            # Move platform towards the waypoint
            p.pos = self.update_position(
                current_pos=p.pos,
                heading=p.wp_properties.heading,
                step_distance=p.wp_properties.step_distance,
            )

        return waypoint_generated_for
