"""
Manage session states
"""

# ==========================
# session states
# ==========================

import streamlit as st
from typing import Optional 

def establish_session_state() -> None:
    """
    Establishes the session state for the Streamlit application.
    """
    if "number_of_replications" not in st.session_state:
        st.session_state.number_of_replications = 10  # Default value

    if "time_limit" not in st.session_state:
        st.session_state.time_limit = 10  # Default value in hours

    if "run_simulation" not in st.session_state:
        st.session_state.run_simulation = False  # Default value

    if "platform_created" not in st.session_state:
        st.session_state.platform_created = False  # Default value

    