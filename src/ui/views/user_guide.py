"""
Streamlit view for rendering the MAKO User Guide.
"""

from __future__ import annotations

import logging
from pathlib import Path
import re

import streamlit as st

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GUIDE_DIR = Path("docs/05-user_guide")
GUIDE_PATH = GUIDE_DIR / "user_guide.md"
IMAGE_REGEX = re.compile(r"!\[(.*?)\]\((.*?)\)")


def render_markdown_with_image_fallbacks(content: str, base_dir: Path) -> None:
    """
    Renders markdown content, gracefully handling local image references.
    If the referenced image file exists, it displays the image using st.image.
    If the image file is missing, it displays a neat placeholder with the alt text.
    """
    last_idx = 0
    for match in IMAGE_REGEX.finditer(content):
        # Render markdown content prior to this image match
        pre_text = content[last_idx : match.start()].strip()
        if pre_text:
            st.markdown(pre_text)

        alt_text = match.group(1)
        rel_path = match.group(2)
        full_image_path = (base_dir / rel_path).resolve()

        if full_image_path.exists() and full_image_path.is_file():
            st.image(str(full_image_path), caption=alt_text, use_container_width=True)
        else:
            with st.container(border=True):
                st.caption(f"🖼️ **Screenshot Placeholder**: {alt_text}")
                st.info(
                    f"**Static Image Reference:** `{rel_path}`\n\n"
                    f"*Capture this screen in the app and save it to: `docs/05-user_guide/{rel_path}`.*"
                )

        last_idx = match.end()

    # Render any remaining trailing markdown
    remaining_text = content[last_idx:].strip()
    if remaining_text:
        st.markdown(remaining_text)


def main() -> None:
    """Render the MAKO User Guide view."""
    st.title("🦈 MAKO User Guide")
    st.caption("Monte-Carlo Agent Kinematics and Observation — Rapid Maritime Simulation Manual")

    if not GUIDE_PATH.exists():
        st.error(f"User guide file not found at `{GUIDE_PATH.resolve()}`.")
        return

    try:
        content = GUIDE_PATH.read_text(encoding="utf-8")
    except Exception as exc:
        logger.exception("Error loading user guide markdown: %s", exc)
        st.error(f"Failed to load user guide: {exc}")
        return

    # Add quick download button for offline reading
    st.sidebar.markdown("---")
    st.sidebar.download_button(
        label="📥 Download User Guide (.md)",
        data=content,
        file_name="MAKO_User_Guide.md",
        mime="text/markdown",
        help="Download the complete user guide markdown for offline viewing or printing.",
    )

    render_markdown_with_image_fallbacks(content, GUIDE_DIR)


main()
