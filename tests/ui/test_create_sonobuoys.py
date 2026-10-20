"""
Unit tests for src/ui/views/create_sonobuoys.py.
"""

from __future__ import annotations

import streamlit as st

from src.schemas.movement import RandomWalkMovement
from src.schemas.platform import PlatformConfig, Team
from src.schemas.sensor import GenericSensorConfig
from src.schemas.sonobuoy import SonobuoyConfig
from src.ui.views.create_sonobuoys import (
    _build_sonobuoy_summary,
    _has_active_blue_source,
    _is_duplicate_buoy_name,
)


def test_has_active_blue_source_empty():
    st.session_state["platform_draft_list"] = []
    assert not _has_active_blue_source()


def test_has_active_blue_source_no_active():
    passive_sensor = GenericSensorConfig(
        display_name="Passive Sensor",
        interval_time_sec=1.0,
        x_values=[0.0, 100.0],
        pod=[1.0, 0.5],
        k=1,
        n=1,
        active_source=False,
    )
    blue_platform = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        sensors=[passive_sensor],
    )
    st.session_state["platform_draft_list"] = [blue_platform]
    assert not _has_active_blue_source()


def test_has_active_blue_source_with_active():
    active_sensor = GenericSensorConfig(
        display_name="Active Pinger",
        interval_time_sec=1.0,
        x_values=[0.0, 100.0],
        pod=[1.0, 0.5],
        k=1,
        n=1,
        active_source=True,
    )
    blue_platform = PlatformConfig(
        platform_config_folder="blue_1",
        display_name="Blue 1",
        team=Team.BLUE,
        speed_mps=10.0,
        movement_type=RandomWalkMovement(),
        sensors=[active_sensor],
    )
    st.session_state["platform_draft_list"] = [blue_platform]
    assert _has_active_blue_source()


def test_is_duplicate_buoy_name():
    buoy = SonobuoyConfig(
        display_name="Alpha",
        x_m=10.0,
        y_m=20.0,
        k=1,
        n=1,
        distance_m=[0.0, 100.0],
        pod=[1.0, 0.5],
    )
    st.session_state["sonobuoy_draft_list"] = [buoy]
    assert _is_duplicate_buoy_name("Alpha")
    assert _is_duplicate_buoy_name("alpha")
    assert not _is_duplicate_buoy_name("Beta")


def test_build_sonobuoy_summary():
    assert _build_sonobuoy_summary([]).empty

    buoy = SonobuoyConfig(
        display_name="Buoy 1",
        x_m=5.0,
        y_m=10.0,
        k=2,
        n=3,
        evaluation_modes=["single", "multi"],
        distance_m=[0.0, 500.0, 1000.0],
        pod=[1.0, 0.8, 0.0],
    )
    df = _build_sonobuoy_summary([buoy])
    assert len(df) == 1
    assert df.iloc[0]["Name"] == "Buoy 1"
    assert df.iloc[0]["X (km)"] == 5.0
    assert df.iloc[0]["Y (km)"] == 10.0
    assert df.iloc[0]["K"] == 2
    assert df.iloc[0]["N"] == 3
    assert df.iloc[0]["Modes"] == "single, multi"
    assert df.iloc[0]["PoD Points"] == 3
