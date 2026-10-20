"""Schemas for sonobuoy multistatic acoustic receivers and field configuration."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, model_validator

SonobuoyEvaluationMode = Literal["single", "multi", "single_cycle"]
ALL_SONOBUOY_MODES: tuple[SonobuoyEvaluationMode, ...] = ("single", "multi", "single_cycle")


class SonobuoyConfig(BaseModel):
    """Configuration for an individual sonobuoy receiver.

    Attributes:
        display_name: Unique human-readable name of the buoy.
        x_m: X position in metres.
        y_m: Y position in metres.
        k: Minimum required detection hits in sliding window of size n.
        n: Capacity of the sliding window for single-buoy detection.
        distance_m: Strictly increasing equivalent range distances in metres.
        pod: Probability of detection corresponding to each distance in distance_m.
        evaluation_modes: Active evaluation modes participating in fusion.
    """

    display_name: str = Field(..., description="The display name of the sonobuoy.")
    x_m: float = Field(..., description="The x position in metres.")
    y_m: float = Field(..., description="The y position in metres.")
    k: int = Field(gt=0, description="Minimum hits required for single-buoy detection.")
    n: int = Field(gt=0, description="Window size for single-buoy detection.")
    distance_m: list[float] = Field(
        default_factory=list, description="Equivalent range distances in metres."
    )
    pod: list[float] = Field(
        default_factory=list, description="Probability of detection corresponding to distance_m."
    )
    evaluation_modes: list[SonobuoyEvaluationMode] = Field(
        default_factory=lambda: list(ALL_SONOBUOY_MODES),
        description="Active evaluation modes for this buoy.",
    )

    @model_validator(mode="after")
    def validate_sonobuoy(self) -> SonobuoyConfig:
        if self.k > self.n:
            raise ValueError(f"k ({self.k}) must be less than or equal to n ({self.n})")
        if not self.distance_m:
            raise ValueError("distance_m cannot be empty")
        if len(self.distance_m) != len(self.pod):
            raise ValueError(
                f"distance_m and pod must have the same length (got {len(self.distance_m)} and {len(self.pod)})"
            )
        for d in self.distance_m:
            if d < 0.0:
                raise ValueError(f"distance_m values must be non-negative, got {d}")
        for d1, d2 in zip(self.distance_m, self.distance_m[1:]):
            if d2 <= d1:
                raise ValueError(
                    f"distance_m must be strictly increasing, got {d1} followed by {d2}"
                )
        for p in self.pod:
            if not (0.0 <= p <= 1.0):
                raise ValueError(f"Probability of detection must be between 0.0 and 1.0, got {p}")
        if not self.evaluation_modes:
            raise ValueError("evaluation_modes must not be empty")

        distinct_modes: list[SonobuoyEvaluationMode] = []
        for m in self.evaluation_modes:
            if m not in ALL_SONOBUOY_MODES:
                raise ValueError(f"Invalid evaluation mode: {m}")
            if m not in distinct_modes:
                distinct_modes.append(m)
        self.evaluation_modes = distinct_modes
        return self


class SonobuoyFieldConfig(BaseModel):
    """Configuration for field-level sonobuoy multistatic data fusion."""

    data_fusion_requirement: int = Field(
        default=1,
        ge=1,
        description="Number of hits required across buoys for multi/single_cycle detection.",
    )
