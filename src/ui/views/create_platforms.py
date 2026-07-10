
"""
Creates platform 
"""
import streamlit as st
import logging

from src.ui.user_notifier import success

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
    


def render_platform_creation() -> None:
    """
    Renders the platform creation interface in the Streamlit application.
    """
    st.write("Create a new platform for simulation.")
    st.text_input("Platform Name", key="platform_name")
    st.text_area("Platform Description", key="platform_description")


def main() -> None:
    """
    Main function to run the platform creation view.
    """
    st.title("📊 Create Platforms")
    render_platform_creation()

    st.button(
        "Create Platform",
        on_click=lambda: success(
            "platform_created",
            "Platform created successfully!",
        ),
    )

    if st.session_state.get("platform_created", False):
        logger.info("Platform created successfully!")
        st.session_state["platform_created"] = False


main()
