"""Browse run folders and load their output CSVs for display as Streamlit tables."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Dict

import pandas as pd

OUTCOMES_DIR = Path("outcomes")
_SECTION_HEADER = re.compile(
    r"\n(?=# \d+\. )"
)  # Matches the start of each section in summary_stats.csv based on the "# n. Title" pattern


def list_run_folders(outcomes_dir: Path = OUTCOMES_DIR) -> list[Path]:
    """List available run folders under outcomes/, most recent first."""
    if not outcomes_dir.exists():
        return []
    return sorted((p for p in outcomes_dir.iterdir() if p.is_dir()), reverse=True)


def load_raw_positions(run_folder: Path) -> pd.DataFrame:
    """Load raw_positions.csv for a run folder as-is, for tabular display."""
    return pd.read_csv(run_folder / "raw_positions.csv", skipinitialspace=True)


def load_summary_stats_tables(run_folder: Path) -> Dict[str, pd.DataFrame]:
    """Split summary_stats.csv's "# n. Title" sections back into separate DataFrames."""
    text = (run_folder / "summary_stats.csv").read_text(encoding="utf-8").strip()

    tables: Dict[str, pd.DataFrame] = {}
    for section in _SECTION_HEADER.split(text):
        title, _, body = section.partition("\n")
        title = title.lstrip("#").strip()
        body = body.strip()
        tables[title] = (
            pd.read_csv(io.StringIO(body), skipinitialspace=True)
            if body
            else pd.DataFrame()
        )
    return tables
