"""Pure Plotly figure-building for platform animations.

No Streamlit, no file/CSV I/O - this module only turns already-normalised
in-memory data (PlatformAnimationData, SimulationTiming) into a go.Figure, so
it can be reused by both a Streamlit page and a plain CLI script.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, TypedDict, cast

import numpy as np
import plotly.graph_objects as go

MAX_ANIMATION_FRAMES = 450
FRAME_DURATION_MS = 100


class SimulationTiming(TypedDict):
    time_limit_sec: float
    world_timestep_sec: float


class PlatformPosition(TypedDict):
    platform_id: str
    team: str
    timestamp_sec: float
    pos_x_km: float
    pos_y_km: float
    waypoint_x_km: float
    waypoint_y_km: float
    detection_made: bool
    target_platform_id: Optional[str]
    detection_sensor_name: Optional[str]
    detection_distance_m: Optional[float]


class DetectionEvent(TypedDict):
    timestamp_sec: float
    detecting_platform_id: str
    target_platform_id: str
    sensor_name: Optional[str]
    distance_m: Optional[float]


class SensorDefinition(TypedDict):
    platform_id: str
    name: str
    fov_start_deg: float
    fov_end_deg: float
    range_km: float


class PlatformAnimationData(TypedDict):
    positions: List[PlatformPosition]
    sensors: List[SensorDefinition]
    detections: List[DetectionEvent]


def _sector_points(
    centre_x: float,
    centre_y: float,
    start_deg: float,
    end_deg: float,
    radius_km: float,
) -> Tuple[List[float], List[float]]:
    end_for_arc = end_deg if end_deg >= start_deg else end_deg + 360.0
    angles = np.deg2rad(np.linspace(start_deg, end_for_arc, 48))
    arc_x = centre_x + radius_km * np.cos(angles)
    arc_y = centre_y + radius_km * np.sin(angles)
    return (
        [centre_x] + arc_x.tolist() + [centre_x],
        [centre_y] + arc_y.tolist() + [centre_y],
    )


def _position_at_time(
    platform: PlatformAnimationData, timestamp_sec: float
) -> PlatformPosition:
    positions = platform["positions"]
    if timestamp_sec <= positions[0]["timestamp_sec"]:
        return positions[0]
    if timestamp_sec >= positions[-1]["timestamp_sec"]:
        return positions[-1]

    for left, right in zip(positions, positions[1:]):
        if left["timestamp_sec"] <= timestamp_sec <= right["timestamp_sec"]:
            duration = right["timestamp_sec"] - left["timestamp_sec"]
            fraction = (timestamp_sec - left["timestamp_sec"]) / duration
            interpolated = dict(left)
            for field in ("pos_x_km", "pos_y_km"):
                interpolated[field] = left[field] + fraction * (
                    right[field] - left[field]
                )
            return cast(PlatformPosition, interpolated)
    return positions[-1]


def _team_color(team: str) -> str:
    return {"blue": "#2563eb", "red": "#dc2626"}.get(team.lower(), "#475569")


def _rgba_color(hex_color: str, alpha: float) -> str:
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def build_animation(
    platforms: Dict[str, PlatformAnimationData],
    timing: SimulationTiming,
) -> go.Figure:
    """Build an animated Plotly figure for one replication's already-loaded platform data."""
    detection_events = sorted(
        [event for platform in platforms.values() for event in platform["detections"]],
        key=lambda event: event["timestamp_sec"],
    )
    regular_frame_times = np.arange(
        0.0,
        timing["time_limit_sec"] + timing["world_timestep_sec"] * 0.5,
        timing["world_timestep_sec"],
    )
    if len(regular_frame_times) <= MAX_ANIMATION_FRAMES:
        frame_times = regular_frame_times
    else:
        frame_times = np.linspace(
            0.0,
            timing["time_limit_sec"],
            MAX_ANIMATION_FRAMES,
        )

    detection_times = np.array(
        [
            event["timestamp_sec"]
            for event in detection_events
            if 0.0 <= event["timestamp_sec"] <= timing["time_limit_sec"]
        ],
        dtype=float,
    )
    frame_times = np.unique(
        np.concatenate(
            (frame_times, detection_times, np.array([0.0, timing["time_limit_sec"]]))
        )
    )

    figure = go.Figure()
    trace_specs: List[Tuple[str, str, Optional[SensorDefinition]]] = []
    detection_targets = {
        event["target_platform_id"]
        for platform in platforms.values()
        for event in platform["detections"]
    }

    for platform_id, platform in platforms.items():
        initial = _position_at_time(platform, 0.0)
        color = _team_color(initial["team"])
        trace_specs.append(("trail", platform_id, None))
        figure.add_trace(
            go.Scatter(
                x=[initial["pos_x_km"]],
                y=[initial["pos_y_km"]],
                mode="lines",
                name=f"{platform_id} trail",
                line={"color": color, "width": 3, "dash": "dot"},
                hoverinfo="skip",
            )
        )
        trace_specs.append(("platform", platform_id, None))
        figure.add_trace(
            go.Scatter(
                x=[initial["pos_x_km"]],
                y=[initial["pos_y_km"]],
                mode="markers",
                name=f"{platform_id} ({initial['team']})",
                marker={"color": color, "size": 12},
            )
        )
        for sensor in platform["sensors"]:
            sector_x, sector_y = _sector_points(
                initial["pos_x_km"],
                initial["pos_y_km"],
                sensor["fov_start_deg"],
                sensor["fov_end_deg"],
                sensor["range_km"],
            )
            trace_specs.append(("sensor", platform_id, sensor))
            figure.add_trace(
                go.Scatter(
                    x=sector_x,
                    y=sector_y,
                    mode="lines",
                    fill="toself",
                    name=f"{platform_id} {sensor['name']}",
                    line={"color": color, "width": 1},
                    fillcolor=_rgba_color(color, 0.2),
                    hoverinfo="skip",
                )
            )
        if platform_id in detection_targets:
            trace_specs.append(("detection", platform_id, None))
            figure.add_trace(
                go.Scatter(
                    x=[],
                    y=[],
                    mode="markers",
                    name=f"{platform_id} detection",
                    marker={
                        "color": "#f59e0b",
                        "size": 18,
                        "symbol": "star",
                        "line": {"color": "#7c2d12", "width": 1},
                    },
                    hovertemplate="Detection target: "
                    + f"{platform_id}<extra></extra>",
                )
            )

    frames = []
    for timestamp_sec in frame_times:
        frame_data = []
        for trace_type, platform_id, sensor in trace_specs:
            platform = platforms[platform_id]
            current = _position_at_time(platform, float(timestamp_sec))
            if trace_type == "trail":
                trail = [
                    position
                    for position in platform["positions"]
                    if position["timestamp_sec"] <= timestamp_sec
                ]
                if not trail or trail[-1]["timestamp_sec"] < timestamp_sec:
                    trail.append(current)
                frame_data.append(
                    go.Scatter(
                        x=[position["pos_x_km"] for position in trail],
                        y=[position["pos_y_km"] for position in trail],
                    )
                )
            elif trace_type == "platform":
                frame_data.append(
                    go.Scatter(x=[current["pos_x_km"]], y=[current["pos_y_km"]])
                )
            elif trace_type == "sensor":
                assert sensor is not None
                sector_x, sector_y = _sector_points(
                    current["pos_x_km"],
                    current["pos_y_km"],
                    sensor["fov_start_deg"],
                    sensor["fov_end_deg"],
                    sensor["range_km"],
                )
                frame_data.append(go.Scatter(x=sector_x, y=sector_y))
            else:
                matching_events = [
                    event
                    for source_platform in platforms.values()
                    for event in source_platform["detections"]
                    if event["target_platform_id"] == platform_id
                    and event["timestamp_sec"] <= timestamp_sec
                ]
                if matching_events:
                    target_position = _position_at_time(platform, float(timestamp_sec))
                    frame_data.append(
                        go.Scatter(
                            x=[target_position["pos_x_km"]],
                            y=[target_position["pos_y_km"]],
                        )
                    )
                else:
                    frame_data.append(go.Scatter(x=[], y=[]))

        frames.append(
            go.Frame(
                data=frame_data,
                name=str(float(timestamp_sec)),
            )
        )
    figure.frames = frames

    all_positions = [
        position
        for platform in platforms.values()
        for position in platform["positions"]
    ]
    all_sensors = [
        sensor for platform in platforms.values() for sensor in platform["sensors"]
    ]
    maximum_range = max([sensor["range_km"] for sensor in all_sensors] + [0.0])
    x_min = min(position["pos_x_km"] for position in all_positions) - maximum_range
    x_max = max(position["pos_x_km"] for position in all_positions) + maximum_range
    y_min = min(position["pos_y_km"] for position in all_positions) - maximum_range
    y_max = max(position["pos_y_km"] for position in all_positions) + maximum_range

    detection_buttons = [
        {
            "label": (
                f"Jump to detection ({event['timestamp_sec']:.0f} s): "
                f"{event['detecting_platform_id']} -> "
                f"{event['target_platform_id']}"
            ),
            "method": "animate",
            "args": [
                [str(float(event["timestamp_sec"]))],
                {
                    "mode": "immediate",
                    "frame": {"duration": 0, "redraw": True},
                    "transition": {"duration": 250},
                },
            ],
        }
        for event in detection_events
        if event["timestamp_sec"] <= timing["time_limit_sec"]
    ]
    detection_note = "Detections: "
    if detection_events:
        detection_note += " | ".join(
            (
                f"{event['timestamp_sec']:.0f} s: "
                f"{event['detecting_platform_id']} -> "
                f"{event['target_platform_id']}"
            )
            for event in detection_events
        )
    else:
        detection_note += "none recorded"

    figure.update_layout(
        xaxis={"title": "X position (km)", "range": [x_min, x_max]},
        yaxis={
            "title": "Y position (km)",
            "range": [y_min, y_max],
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {
                                    "duration": FRAME_DURATION_MS,
                                    "redraw": False,
                                },
                                "transition": {"duration": 0},
                                "fromcurrent": True,
                            },
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {"mode": "immediate"}],
                    },
                    *detection_buttons,
                ],
            }
        ],
        sliders=[
            {
                "steps": [
                    {
                        "method": "animate",
                        "args": [[str(float(timestamp))], {"mode": "immediate"}],
                        "label": f"{timestamp:.1f}",
                    }
                    for timestamp in frame_times
                ],
                "currentvalue": {"prefix": "Time (s): "},
            }
        ],
        legend={
            "orientation": "v",
            "x": 0.01,
            "y": 0.99,
            "xanchor": "left",
            "yanchor": "top",
            "bgcolor": "rgba(255, 255, 255, 0.75)",
        },
        annotations=[
            {
                "text": detection_note,
                "xref": "paper",
                "yref": "paper",
                "x": 0.99,
                "y": 1.08,
                "xanchor": "right",
                "yanchor": "bottom",
                "showarrow": False,
                "bgcolor": "rgba(254, 243, 199, 0.95)",
                "bordercolor": "#f59e0b",
                "borderwidth": 1,
                "font": {"color": "#78350f"},
            }
        ],
        height=750,
    )
    return figure
