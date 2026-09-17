import re
from datetime import datetime
from pathlib import Path

DEFAULT_OUTPUTS_DIR = Path("outcomes")


def get_next_run_folder(base_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    """
    Generate the next available run folder with date prefix.

    Format: YYYY-MM-DD_run_NNN (e.g., 2026-03-02_run_001)

    Searches for existing folders matching today's date and increments
    the run number to avoid overwrites.

    Args:
        base_dir: Base output directory. Defaults to data/outputs.

    Returns:
        Path to the next available run folder.
    """
    # Get today's date in YYYY-MM-DD format
    today = datetime.now().strftime("%Y-%m-%d")

    # Create base directory if it doesn't exist
    base_dir.mkdir(parents=True, exist_ok=True)

    # Find all directories matching today's date pattern
    pattern = re.compile(rf"^{re.escape(today)}_run_(\d{{3}})$")
    existing_runs = []

    for folder in base_dir.iterdir():
        if folder.is_dir():
            match = pattern.match(folder.name)
            if match:
                run_num = int(match.group(1))
                existing_runs.append(run_num)

    # Determine next run number
    next_run = 1 if not existing_runs else max(existing_runs) + 1

    # Create folder name for the next run
    next_run_folder = base_dir / f"{today}_run_{next_run:03d}"
    next_run_folder.mkdir(parents=True, exist_ok=True)

    return next_run_folder
