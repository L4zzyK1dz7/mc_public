"""
Streamlit UI frontend for the application.
"""

import logging

import streamlit as st

from src.ui.session_keys import establish_session_state

logging.basicConfig(
    level=logging.INFO,  # Python defaults to warning
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def establish_pages() -> None:
    """
    Establishes the pages for the Streamlit application.
    """
    st.set_page_config(
        page_title="Monte Carlo Simulation",
        page_icon=":game_die:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    home_page = st.Page(
        page="src/ui/views/home.py",
        default=True,
        title="Run Monte Carlo Simulation",
    )

    create_platforms_page = st.Page(
        page="src/ui/views/create_platforms.py",
        default=False,
        title="Create Platforms",
    )

    navigation = st.navigation([home_page, create_platforms_page])

    navigation.run()


def side_bar() -> None:
    """
    Creates the sidebar for the Streamlit application.
    """
    st.sidebar.header("World Parameters")
    st.session_state.origin_x = st.sidebar.number_input(
        "Origin X (km)", min_value=0, value=0, step=1
    )
    st.session_state.origin_y = st.sidebar.number_input(
        "Origin Y (km)", min_value=0, value=0, step=1
    )
    st.session_state.length = st.sidebar.number_input(
        "Length (km)", min_value=0, value=100, step=1
    )
    st.session_state.height = st.sidebar.number_input(
        "Height (km)", min_value=0, value=100, step=1
    )

    st.sidebar.header("Simulation Parameters")
    # Add more sidebar elements as needed
    st.session_state.number_of_replications = st.sidebar.number_input(
        "Number of Simulations", min_value=1, value=1000, step=1
    )
    st.session_state.time_limit_sec = st.sidebar.number_input(
        "Time Limit (hours)", min_value=1, value=1, step=1
    )
    st.session_state.world_timestep_sec = st.sidebar.number_input(
        "Time Step (seconds)", min_value=0.001, value=1.0, step=0.1
    )
    st.session_state.detection_end_condition = st.sidebar.selectbox(
        "Detection End Condition",
        options=["initial_detection", "team_detection"],
        index=0,
        help="Initial Detection: Stop when the first detection occurs. Team Detection: Stop when the team achieves detection.",
    )
    st.session_state.seeds_file = st.sidebar.checkbox("Use Seeds File", value=True)


def run_simulation() -> None:
    """
    runs the Monte Carlo simulation and displays the results in the Streamlit app.
    """

    from src.monte_carlo.monte_carlo import run_simulation

    run_simulation()


def main() -> None:
    """
    Main route for the Streamlit application.
    """

    # initialise session states
    establish_session_state()

    # Setup pages
    establish_pages()

    # Sidebar for user inputs
    side_bar()


if __name__ == "__main__":
    main()
