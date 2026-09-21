"""
Command-line interface for animating a saved simulation replication.

Renders an already-completed run (produced by simulate.py) as an animated
Plotly figure, without needing Streamlit.

Usage:
    python animate.py outcomes/2026-09-21_run_007
    python animate.py outcomes/2026-09-21_run_007 --replication 2
    python animate.py outcomes/2026-09-21_run_007 --replication 2 --output animation.html
"""

from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser
from pathlib import Path

from src.ui.plotting.platform_animation import build_animation
from src.ui.services.animation_data import load_replication_animation_data

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    parser = ArgumentParser(
        description="Render a saved simulation replication as an animated Plotly figure.",
        epilog="Example: python animate.py outcomes/2026-09-21_run_007 --replication 2",
    )
    parser.add_argument(
        "run_folder",
        type=Path,
        help="Path to a run folder produced by simulate.py "
        "(contains raw_positions.csv and an input_data/ snapshot).",
    )
    parser.add_argument(
        "-r",
        "--replication",
        type=int,
        default=0,
        help="Replication id to animate (default: 0).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write a static HTML file instead of opening a browser tab.",
    )

    args = parser.parse_args()

    if not args.run_folder.exists():
        logger.error("Run folder not found: %s", args.run_folder)
        sys.exit(1)

    try:
        platforms, timing = load_replication_animation_data(
            args.run_folder, args.replication
        )
    except (OSError, ValueError) as error:
        logger.error("Could not load animation inputs: %s", error)
        sys.exit(1)

    figure = build_animation(platforms, timing)

    if args.output is not None:
        figure.write_html(args.output)
        logger.info("Wrote animation to %s", args.output)
    else:
        figure.show()


if __name__ == "__main__":
    main()
