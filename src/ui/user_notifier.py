import streamlit as st
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def success(key: str, msg: str) -> None:
    """Store a success flag in session state and show a transient toast."""
    st.session_state[key] = True
    st.toast(msg, icon="✅")
    logger.info("%s", msg)
    