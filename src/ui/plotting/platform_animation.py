"""Pure Plotly figure-building for platform animations.

No Streamlit, no file/CSV I/O - this module only turns already-normalised
in-memory data (PlatformAnimationData, SimulationTiming) into a go.Figure, so
it can be reused by both a Streamlit page and a plain CLI script.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, TypedDict, cast

import numpy as np
import plotly.graph_objects as go

MAX_ANIMATION_FRAMES = 450
FRAME_DURATION_MS = 100


class SimulationTiming(TypedDict, total=False):
    time_limit_sec: float
    world_timestep_sec: float
    end_time_sec: Optional[float]


class PlatformPosition(TypedDict, total=False):
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
    detection_distance_km: Optional[float]
    heading: Optional[float]


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


class SonobuoyDefinition(TypedDict):
    name: str
    x_km: float
    y_km: float


class OperatingAreaDefinition(TypedDict):
    x_min_km: float
    x_max_km: float
    y_min_km: float
    y_max_km: float


class BarrierDefinition(TypedDict):
    platform_id: str
    name: str
    x_start_km: float
    x_end_km: float
    y_km: float


class PlatformAnimationData(TypedDict, total=False):
    display_name: str
    positions: list[PlatformPosition]
    sensors: list[SensorDefinition]
    detections: list[DetectionEvent]


def _platform_heading_deg(position: PlatformPosition) -> float:
    """Return the heading in degrees for a platform position."""
    heading = position.get("heading")
    if heading is not None and not (isinstance(heading, float) and np.isnan(heading)):
        return float(heading) % 360.0
    return 0.0


def _sector_points(
    centre_x: float,
    centre_y: float,
    start_deg: float,
    end_deg: float,
    radius_km: float,
    heading_deg: float = 0.0,
) -> tuple[list[float], list[float]]:
    diff = end_deg - start_deg
    if diff == 360.0 or (start_deg == 0.0 and end_deg == 360.0):
        span = 360.0
    else:
        span = diff % 360.0

    rotated_start = heading_deg + start_deg
    rotated_end = rotated_start + span
    angles = np.deg2rad(np.linspace(rotated_start, rotated_end, 48))
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
            fraction = (
                (timestamp_sec - left["timestamp_sec"]) / duration
                if duration > 0.0
                else 0.0
            )
            interpolated = dict(left)
            for field in ("pos_x_km", "pos_y_km"):
                interpolated[field] = left[field] + fraction * (
                    right[field] - left[field]
                )
            left_heading = left.get("heading")
            if left_heading is not None and not (
                isinstance(left_heading, float) and np.isnan(left_heading)
            ):
                interpolated["heading"] = float(left_heading) % 360.0
            else:
                interpolated["heading"] = 0.0
            return cast(PlatformPosition, interpolated)
    return positions[-1]


def _seconds_to_minutes(timestamp_sec: float) -> float:
    return timestamp_sec / 60.0


def _team_color(team: str) -> str:
    return {"blue": "#2563eb", "red": "#dc2626"}.get(team.lower(), "#475569")


def _rgba_color(hex_color: str, alpha: float) -> str:
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def build_animation(
    platforms: Mapping[str, PlatformAnimationData],
    timing: SimulationTiming,
    sonobuoys: Optional[list[SonobuoyDefinition]] = None,
    sonobuoy_detections: Optional[list[dict[str, Any]]] = None,
    operating_area: Optional[OperatingAreaDefinition] = None,
    barriers: Optional[list[BarrierDefinition]] = None,
) -> go.Figure:
    """Build an animated Plotly figure for one replication's already-loaded platform data."""
    detection_events = [
        event for platform in platforms.values() for event in platform["detections"]
    ]
    if sonobuoy_detections:
        for sb_det in sonobuoy_detections:
            timestamp_sec = float(sb_det["timestamp_minutes"]) * 60.0
            mode = sb_det.get("mode", "single_cycle")
            detecting_id = sb_det.get("detecting_id", "sonobuoy")
            target_id = str(sb_det["target_platform_id"])
            detection_events.append(
                {
                    "timestamp_sec": timestamp_sec,
                    "detecting_platform_id": f"{detecting_id} ({mode})",
                    "target_platform_id": target_id,
                    "sensor_name": mode,
                    "distance_m": None,
                }
            )
    detection_events.sort(key=lambda event: event["timestamp_sec"])
    end_time_sec = float(timing.get("end_time_sec") or timing["time_limit_sec"])

    regular_frame_times = np.arange(
        0.0,
        end_time_sec + timing["world_timestep_sec"] * 0.5,
        timing["world_timestep_sec"],
    )
    if len(regular_frame_times) <= MAX_ANIMATION_FRAMES:
        frame_times = regular_frame_times
    else:
        frame_times = np.linspace(
            0.0,
            end_time_sec,
            MAX_ANIMATION_FRAMES,
        )

    detection_times = np.array(
        [
            event["timestamp_sec"]
            for event in detection_events
            if 0.0 <= event["timestamp_sec"] <= end_time_sec
        ],
        dtype=float,
    )
    frame_times = np.unique(
        np.concatenate(
            (frame_times, detection_times, np.array([0.0, end_time_sec]))
        )
    )

    figure = go.Figure()
    trace_specs: list[tuple[str, str, Any]] = []
    detection_targets = {
        event["target_platform_id"] for event in detection_events
    }

    # Add operating area as a static closed rectangle
    if operating_area:
        trace_specs.append(("operating_area", "Operating area", operating_area))
        figure.add_trace(
            go.Scatter(
                x=[
                    operating_area["x_min_km"],
                    operating_area["x_max_km"],
                    operating_area["x_max_km"],
                    operating_area["x_min_km"],
                    operating_area["x_min_km"],
                ],
                y=[
                    operating_area["y_min_km"],
                    operating_area["y_min_km"],
                    operating_area["y_max_km"],
                    operating_area["y_max_km"],
                    operating_area["y_min_km"],
                ],
                mode="lines",
                name="Operating area",
                line={"color": "#000000", "width": 4},
                fill=None,
                hoverinfo="skip",
            )
        )

    # Add barriers as static thick lines beneath platform trails
    if barriers:
        import plotly.colors as pc

        n_barriers = len(barriers)
        if n_barriers == 1:
            barrier_colors = ["rgb(0, 0, 0)"]
        else:
            barrier_colors = pc.sample_colorscale(
                "Greys", n_barriers, low=0.3, high=1.0
            )

        for barrier, b_color in zip(barriers, barrier_colors):
            trace_specs.append(("barrier", barrier["platform_id"], barrier))
            figure.add_trace(
                go.Scatter(
                    x=[barrier["x_start_km"], barrier["x_end_km"]],
                    y=[barrier["y_km"], barrier["y_km"]],
                    mode="lines",
                    name=f"{barrier['name']} barrier",
                    line={"color": b_color, "width": 10},
                    hoverinfo="skip",
                )
            )

    # Add sonobuoys as static blue squares
    if sonobuoys:
        for buoy in sonobuoys:
            trace_specs.append(("sonobuoy", buoy["name"], buoy))
            figure.add_trace(
                go.Scatter(
                    x=[buoy["x_km"]],
                    y=[buoy["y_km"]],
                    mode="markers",
                    name=buoy["name"],
                    marker={"color": "#08306b", "size": 12, "symbol": "square"},
                    hoverinfo="text",
                    hovertext=buoy["name"],
                )
            )

    for platform_id, platform in platforms.items():
        initial = _position_at_time(platform, 0.0)
        color = _team_color(initial["team"])
        disp_name = platform.get("display_name", platform_id)

        trace_specs.append(("trail", platform_id, None))
        figure.add_trace(
            go.Scatter(
                x=[initial["pos_x_km"]],
                y=[initial["pos_y_km"]],
                mode="lines",
                name=f"{disp_name} trail",
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
                name=f"{disp_name} ({initial['team']})",
                marker={"color": color, "size": 12},
            )
        )
        initial_heading = _platform_heading_deg(initial)
        for sensor in platform["sensors"]:
            sector_x, sector_y = _sector_points(
                initial["pos_x_km"],
                initial["pos_y_km"],
                sensor["fov_start_deg"],
                sensor["fov_end_deg"],
                sensor["range_km"],
                heading_deg=initial_heading,
            )
            trace_specs.append(("sensor", platform_id, sensor))
            figure.add_trace(
                go.Scatter(
                    x=sector_x,
                    y=sector_y,
                    mode="lines",
                    fill="toself",
                    name=f"{disp_name} {sensor['name']}",
                    line={"color": color, "width": 1},
                    fillcolor=_rgba_color(color, 0.2),
                    hoverinfo="skip",
                )
            )
        if platform_id in detection_targets or disp_name in detection_targets:
            trace_specs.append(("detection", platform_id, None))
            figure.add_trace(
                go.Scatter(
                    x=[],
                    y=[],
                    mode="markers",
                    name=f"{disp_name} detection",
                    marker={
                        "color": "#f59e0b",
                        "size": 18,
                        "symbol": "star",
                        "line": {"color": "#7c2d12", "width": 1},
                    },
                    hovertemplate=f"Detection target: {disp_name}<extra></extra>",
                )
            )

    frames = []
    for timestamp_sec in frame_times:
        frame_data = []
        for trace_type, platform_id, sensor_or_extra in trace_specs:
            if trace_type == "operating_area":
                frame_data.append(
                    go.Scatter(
                        x=[
                            sensor_or_extra["x_min_km"],
                            sensor_or_extra["x_max_km"],
                            sensor_or_extra["x_max_km"],
                            sensor_or_extra["x_min_km"],
                            sensor_or_extra["x_min_km"],
                        ],
                        y=[
                            sensor_or_extra["y_min_km"],
                            sensor_or_extra["y_min_km"],
                            sensor_or_extra["y_max_km"],
                            sensor_or_extra["y_max_km"],
                            sensor_or_extra["y_min_km"],
                        ],
                    )
                )
                continue
            elif trace_type == "barrier":
                frame_data.append(
                    go.Scatter(
                        x=[sensor_or_extra["x_start_km"], sensor_or_extra["x_end_km"]],
                        y=[sensor_or_extra["y_km"], sensor_or_extra["y_km"]],
                    )
                )
                continue
            elif trace_type == "sonobuoy":
                frame_data.append(
                    go.Scatter(
                        x=[sensor_or_extra["x_km"]],
                        y=[sensor_or_extra["y_km"]],
                    )
                )
                continue

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
                assert sensor_or_extra is not None
                sector_x, sector_y = _sector_points(
                    current["pos_x_km"],
                    current["pos_y_km"],
                    sensor_or_extra["fov_start_deg"],
                    sensor_or_extra["fov_end_deg"],
                    sensor_or_extra["range_km"],
                    heading_deg=_platform_heading_deg(current),
                )
                frame_data.append(go.Scatter(x=sector_x, y=sector_y))
            else:
                matching_events = [
                    event
                    for event in detection_events
                    if event["target_platform_id"] in (platform_id, platform.get("display_name", platform_id))
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
    buoy_x = [b["x_km"] for b in (sonobuoys or [])]
    buoy_y = [b["y_km"] for b in (sonobuoys or [])]

    box_x: list[float] = []
    box_y: list[float] = []
    if operating_area:
        box_x = [operating_area["x_min_km"], operating_area["x_max_km"]]
        box_y = [operating_area["y_min_km"], operating_area["y_max_km"]]

    barrier_x: list[float] = []
    barrier_y: list[float] = []
    if barriers:
        for b in barriers:
            barrier_x.extend([b["x_start_km"], b["x_end_km"]])
            barrier_y.append(b["y_km"])

    all_x = (
        [position["pos_x_km"] for position in all_positions]
        + buoy_x
        + box_x
        + barrier_x
    )
    all_y = (
        [position["pos_y_km"] for position in all_positions]
        + buoy_y
        + box_y
        + barrier_y
    )

    all_sensors = [
        sensor for platform in platforms.values() for sensor in platform["sensors"]
    ]
    maximum_range = max([sensor["range_km"] for sensor in all_sensors] + [0.0])
    x_min = (min(all_x) if all_x else 0.0) - maximum_range
    x_max = (max(all_x) if all_x else 100.0) + maximum_range
    y_min = (min(all_y) if all_y else 0.0) - maximum_range
    y_max = (max(all_y) if all_y else 100.0) + maximum_range
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0

    def _resolve_name(pid: str) -> str:
        return platforms.get(pid, {}).get("display_name", pid)

    detection_buttons = [
        {
            "label": (
                f"Jump to detection ({_seconds_to_minutes(event['timestamp_sec']):.2f} min): "
                f"{_resolve_name(event['detecting_platform_id'])} -> "
                f"{_resolve_name(event['target_platform_id'])}"
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
        if event["timestamp_sec"] <= end_time_sec
    ]
    detection_note = "Detections: "
    if detection_events:
        detection_note += " | ".join(
            (
                f"{_seconds_to_minutes(event['timestamp_sec']):.2f} min: "
                f"{_resolve_name(event['detecting_platform_id'])} -> "
                f"{_resolve_name(event['target_platform_id'])}"
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
                        "label": f"{_seconds_to_minutes(timestamp):.2f}",
                    }
                    for timestamp in frame_times
                ],
                "currentvalue": {"prefix": "Time (min): "},
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
