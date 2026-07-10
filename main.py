"""
Streamlit UI frontend for the application.
"""

import streamlit as st
import logging

logging.basicConfig(
    level=logging.INFO, # Python defaults to warning
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
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    home_page = st.Page(
        page="src/ui/views/home.py",
        default=True,
    )

    create_platforms_page = st.Page(
        page="src/ui/views/create_platforms.py",
        default=False,
    )

    navigation = st.navigation([
        home_page, 
        create_platforms_page
        ])

    navigation.run()



def side_bar() -> None:
    """
    Creates the sidebar for the Streamlit application.
    """
    st.sidebar.header("Simulation Parameters")
    # Add more sidebar elements as needed
    st.session_state.number_of_replications = st.sidebar.number_input("Number of Simulations", min_value=1, value=1000, step=1)
    st.session_state.time_limit = st.sidebar.number_input("Time Limit (hours)", min_value=1, value=10, step=1)


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

    # Setup pages 
    establish_pages()

    # initialise session states
    from src.ui.session_states import establish_session_state
    establish_session_state()

    # Sidebar for user inputs
    side_bar()


if __name__ == "__main__":
    main()


