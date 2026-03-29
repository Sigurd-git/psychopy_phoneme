from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .audio_recorder import build_recording_path
from .models import RunPaths
from .models import TrialDefinition


def create_run_paths(subject_id: str, data_dir: Path, run_subfolder: str | None = None) -> RunPaths:
    """Create or reuse output folders for one experiment run."""

    run_dir = resolve_run_dir(subject_id, data_dir, run_subfolder=run_subfolder)
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


def resolve_run_dir(subject_id: str, data_dir: Path, run_subfolder: str | None = None) -> Path:
    """Resolve the run directory, defaulting to the legacy timestamped layout."""

    if run_subfolder:
        requested_path = Path(run_subfolder).expanduser()
        if requested_path.is_absolute():
            return requested_path
        return data_dir / requested_path

    timestamp_label = datetime.now().strftime("%Y%m%d_%H%M%S")
    return data_dir / f"sub-{subject_id}" / f"run-{timestamp_label}"


def find_existing_recordings(
    recordings_dir: Path, trials: list[TrialDefinition]
) -> dict[int, Path]:
    """Return the expected recording paths that already exist on disk."""

    existing_recordings: dict[int, Path] = {}
    for trial in trials:
        recording_path = build_recording_path(recordings_dir, trial)
        if recording_path.exists():
            existing_recordings[trial.trial_index] = recording_path
    return existing_recordings
