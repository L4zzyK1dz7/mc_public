"""Pure Plotly figure-building for Monte Carlo detection analytics.

Generates Tier 1 (Fleet convergence), Tier 2 (Many-to-Many interaction heatmap),
and Tier 3 (Pairwise drill-down convergence & histograms) visualisations from
simulation summary statistics.

No Streamlit dependencies - purely transforms DataFrames into Plotly go.Figure.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def compute_running_probability(
    outcomes_df: pd.DataFrame,
    total_replications: Optional[int] = None,
) -> pd.DataFrame:
    """Compute the running cumulative detection probability and 95% confidence bounds.

    Args:
        outcomes_df: DataFrame with 'replication_id' and 'detection_outcome' columns.
        total_replications: Optional expected total replications count for full reindexing.

    Returns:
        DataFrame with columns: replication_num, detected, p_det, ci_lower, ci_upper.
    """
    if outcomes_df.empty:
        return pd.DataFrame(
            columns=["replication_num", "detected", "p_det", "ci_lower", "ci_upper"]
        )

    # Determine per-replication detection outcome (True if any detection in that replication)
    per_rep = (
        outcomes_df.groupby("replication_id")["detection_outcome"]
        .any()
        .reset_index(name="detected")
        .sort_values("replication_id")
    )

    if total_replications is not None and total_replications > len(per_rep):
        full_index = pd.DataFrame({"replication_id": list(range(total_replications))})
        per_rep = full_index.merge(per_rep, on="replication_id", how="left")
        per_rep["detected"] = per_rep["detected"].fillna(False)

    per_rep["replication_num"] = per_rep.index + 1
    per_rep["cum_hits"] = per_rep["detected"].astype(int).cumsum()
    per_rep["p_det"] = per_rep["cum_hits"] / per_rep["replication_num"]

    # Calculate 95% confidence interval via normal approximation
    # SE = sqrt(p * (1 - p) / N)
    std_err = np.sqrt(
        per_rep["p_det"] * (1.0 - per_rep["p_det"]) / per_rep["replication_num"]
    )
    per_rep["ci_lower"] = np.clip(per_rep["p_det"] - 1.96 * std_err, 0.0, 1.0)
    per_rep["ci_upper"] = np.clip(per_rep["p_det"] + 1.96 * std_err, 0.0, 1.0)

    return per_rep


def build_fleet_convergence_chart(
    outcomes_df: pd.DataFrame,
    palette: Optional[list[str]] = None,
) -> go.Figure:
    """Build Tier 1 Multi-line Monte Carlo convergence chart across all targets.

    Plots each hostile target platform as an individual curve, plus an overall
    fleet-wide detection curve.
    """
    fig = go.Figure()

    if outcomes_df.empty or "replication_id" not in outcomes_df.columns:
        fig.update_layout(title="No detection data available for convergence analysis")
        return fig

    colors = palette or [
        "#1f77b4",  # Blue
        "#ff7f0e",  # Orange
        "#2ca02c",  # Green
        "#d62728",  # Red
        "#9467bd",  # Purple
        "#8c564b",  # Brown
        "#e377c2",  # Pink
        "#7f7f7f",  # Grey
        "#bcbd22",  # Yellow-green
        "#17becf",  # Cyan
    ]

    total_reps = outcomes_df["replication_id"].nunique()

    # 1. Overall fleet curve (any platform detects any target)
    fleet_rep = compute_running_probability(outcomes_df, total_reps)
    if not fleet_rep.empty:
        final_fleet_p = fleet_rep["p_det"].iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=fleet_rep["replication_num"],
                y=fleet_rep["p_det"],
                mode="lines",
                name=f"Overall Fleet (P={final_fleet_p:.3f})",
                line=dict(color="#000000", width=3, dash="solid"),
                hovertemplate="Replication: %{x}<br>Overall P_det: %{y:.3f}<extra></extra>",
            )
        )

    # 2. Individual target curves
    targets = sorted(outcomes_df["target_platform_id"].dropna().unique())
    for idx, target in enumerate(targets):
        target_df = outcomes_df[outcomes_df["target_platform_id"] == target]
        target_rep = compute_running_probability(target_df, total_reps)
        if target_rep.empty:
            continue

        color = colors[idx % len(colors)]
        final_p = target_rep["p_det"].iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=target_rep["replication_num"],
                y=target_rep["p_det"],
                mode="lines",
                name=f"Target: {target} (P={final_p:.3f})",
                line=dict(color=color, width=2, dash="dash" if idx > 0 else "solid"),
                hovertemplate=f"Target {target}<br>Replication: %{{x}}<br>P_det: %{{y:.3f}}<extra></extra>",
            )
        )

    fig.update_layout(
        title="Monte Carlo Convergence: Cumulative Detection Probability (P<sub>det</sub>)",
        xaxis_title="Replication Number (Sample Size N)",
        yaxis_title="Cumulative Detection Probability",
        yaxis_range=[-0.02, 1.05],
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
        ),
        margin=dict(l=60, r=40, t=80, b=60),
    )

    return fig


def build_interaction_heatmap(table_1_df: pd.DataFrame) -> Optional[go.Figure]:
    """Build Tier 2 Many-to-Many Interaction Heatmap ($M \\times N$ grid).

    Args:
        table_1_df: Table 1 DataFrame from summary_stats with columns:
            detecting_platform_id, target_platform_id, average_detections.

    Returns:
        Plotly Figure showing the detection matrix, or None if data is insufficient.
    """
    req_cols = {"detecting_platform_id", "target_platform_id", "average_detections"}
    if table_1_df.empty or not req_cols.issubset(table_1_df.columns):
        return None

    # Pivot into M x N matrix
    matrix = table_1_df.pivot(
        index="detecting_platform_id",
        columns="target_platform_id",
        values="average_detections",
    ).fillna(0.0)

    observers = list(matrix.index)
    targets = list(matrix.columns)
    z_values = matrix.values

    # Format annotations inside cells
    text_values = [
        [f"{val:.1%}<br>({val:.3f})" for val in row] for row in z_values
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=targets,
            y=observers,
            text=text_values,
            texttemplate="%{text}",
            textfont={"size": 13, "color": "white"},
            colorscale="Viridis",
            zmin=0.0,
            zmax=1.0,
            colorbar=dict(
                title=dict(text="P<sub>det</sub>", side="top"),
                tickvals=[0.0, 0.25, 0.5, 0.75, 1.0],
                ticktext=["0%", "25%", "50%", "75%", "100%"],
            ),
            hovertemplate=(
                "Observer: %{y}<br>"
                "Target: %{x}<br>"
                "Detection Probability: %{z:.3f}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title="Interaction Matrix: Detection Probability (Observer vs Target)",
        xaxis_title="Target Platforms (Red Team)",
        yaxis_title="Detecting Platforms (Blue Team)",
        template="plotly_white",
        margin=dict(l=80, r=40, t=60, b=60),
    )

    return fig


def build_pairwise_convergence_chart(
    outcomes_df: pd.DataFrame,
    observer_name: str,
    target_name: str,
    total_replications: Optional[int] = None,
) -> go.Figure:
    """Build Tier 3 Pairwise Convergence chart with 95% Confidence Interval ribbon."""
    fig = go.Figure()

    rep_data = compute_running_probability(outcomes_df, total_replications)
    if rep_data.empty:
        fig.update_layout(title=f"No data for {observer_name} vs {target_name}")
        return fig

    # 1. Confidence interval ribbon (Shaded band)
    fig.add_trace(
        go.Scatter(
            x=rep_data["replication_num"],
            y=rep_data["ci_upper"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=rep_data["replication_num"],
            y=rep_data["ci_lower"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(31, 119, 180, 0.15)",
            line=dict(width=0),
            name="95% Confidence Interval",
            hoverinfo="skip",
        )
    )

    # 2. Running probability line
    final_p = rep_data["p_det"].iloc[-1]
    fig.add_trace(
        go.Scatter(
            x=rep_data["replication_num"],
            y=rep_data["p_det"],
            mode="lines",
            name="Cumulative P<sub>det</sub>",
            line=dict(color="#1f77b4", width=2.5),
            hovertemplate="Replication %{x}<br>P_det: %{y:.3f}<extra></extra>",
        )
    )

    # 3. Horizontal asymptote reference line
    fig.add_hline(
        y=final_p,
        line_dash="dash",
        line_color="#d62728",
        line_width=1.5,
        annotation_text=f"Final Asymptote: {final_p:.3f}",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title=f"Convergence Analysis: {observer_name} vs {target_name}",
        xaxis_title="Replication Number (N)",
        yaxis_title="Cumulative Detection Probability",
        yaxis_range=[-0.02, 1.05],
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        margin=dict(l=60, r=40, t=70, b=60),
    )

    return fig


def build_detection_histogram(
    outcomes_df: pd.DataFrame,
    metric_col: str,
    title: str,
    xlabel: str,
    color: str = "#2ca02c",
    nbins: int = 30,
) -> Optional[go.Figure]:
    """Build Tier 3 Histogram for positive detection events (e.g. time or distance)."""
    if outcomes_df.empty or metric_col not in outcomes_df.columns:
        return None

    # Filter strictly positive detections with valid numeric metric
    detected_subset = outcomes_df[outcomes_df["detection_outcome"] == True]
    series = pd.to_numeric(detected_subset[metric_col], errors="coerce").dropna()

    if series.empty:
        return None

    mean_val = series.mean()
    median_val = series.median()

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=series,
            nbinsx=nbins,
            marker_color=color,
            opacity=0.8,
            name="Detections",
            hovertemplate=f"{xlabel}: %{{x:.2f}}<br>Count: %{{y}}<extra></extra>",
        )
    )

    # Vertical reference lines for mean and median
    fig.add_vline(
        x=mean_val,
        line_dash="solid",
        line_color="#d62728",
        line_width=2,
        annotation_text=f"Mean: {mean_val:.2f}",
        annotation_position="top left",
    )
    fig.add_vline(
        x=median_val,
        line_dash="dash",
        line_color="#ff7f0e",
        line_width=2,
        annotation_text=f"Median: {median_val:.2f}",
        annotation_position="top right",
    )

    fig.update_layout(
        title=f"{title} (N = {len(series)} confirmed detections)",
        xaxis_title=xlabel,
        yaxis_title="Replication Count (Frequency)",
        template="plotly_white",
        margin=dict(l=60, r=40, t=60, b=60),
    )

    return fig
