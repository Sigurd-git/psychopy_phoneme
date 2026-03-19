from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import RunPaths


def create_run_paths(subject_id: str, data_dir: Path) -> RunPaths:
    """Create timestamped output folders for one experiment run."""

    timestamp_label = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = data_dir / f"sub-{subject_id}" / f"run-{timestamp_label}"
    logs_dir = run_dir / "logs"
    recordings_dir = run_dir / "recordings"

    logs_dir.mkdir(parents=True, exist_ok=True)
    recordings_dir.mkdir(parents=True, exist_ok=True)

    return RunPaths(
        run_dir=run_dir,
        logs_dir=logs_dir,
        recordings_dir=recordings_dir,
        trial_log_path=logs_dir / "trial_log.csv",
    )
