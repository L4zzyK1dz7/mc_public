"""
Manage session states
"""

from __future__ import annotations

import logging

import streamlit as st

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# =================================
# Session State Management
# =================================


def establish_session_state() -> None:
    """
    Establishes the session state for the Streamlit application.
    """
    session_defaults = {
        # Config data state
        "origin_x": 0,
        "origin_y": 0,
        "length": 100,
        "height": 100,
        "number_of_replications": 10,
        "time_limit_sec": 10,
        "detection_end_condition": "initial_detection",
        "seeds_file": False,
        "world_timestep_sec": 1,
        "cfg_data": {},
        "yaml_file_created": False,
        "run_simulation": False,
        # Platform creation state
        "platform_created": False,
        "platform_draft": {},  # Current platform draft
        "platform_draft_list": [],  # List of the saved platforms
        # Sensor creation state
        "number_of_sensors": 0,
        "sensor_draft_list": [],  # List of the saved sensors that are in its object form
        "sensor_draft_list_final": [],  # Current sensor draft
        "sensor_edit_index": 0,
        "sensor_save_message": "",
    }

    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
