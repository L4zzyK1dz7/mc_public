"""
Home for streamlit application
"""

import logging 
import streamlit as st 

from src.monte_carlo.monte_carlo import run_simulation

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main() -> None:
    """Render the home page."""
    st.title("🏠 Home Page")
    st.write("Welcome to the application dashboard.")

    st.button("Run Simulation", on_click=lambda: st.session_state.update({"run_simulation": True}))

    if st.session_state.get("run_simulation", False):
        logger.info("Running simulation...")
        run_simulation()


main()