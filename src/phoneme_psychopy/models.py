from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TrialDefinition:
    """Single trial definition parsed from the schedule workbook."""

    track_id: str
    snr: float
    onset_label: str
    phoneme: str
    session_type: str
    trial_index: int
    source_sheet: str
    source_row: int
    source_column: str
    block_index: int = 0
    trial_in_block: int = 0
    is_practice: bool = False
    stimulus_file: Path | None = None
    noise_file: Path | None = None


@dataclass(slots=True)
class RunPaths:
    """Filesystem outputs created for an experiment run."""

    run_dir: Path
    logs_dir: Path
    recordings_dir: Path
    trial_log_path: Path


@dataclass(slots=True)
class TrialEventTimes:
    """Timestamps collected during one trial for downstream logging."""

    stimulus_onset_time: str
    response_prompt_time: str
    recording_start_reaction_time_seconds: float
    recording_prompt_display_time: str


@dataclass(slots=True)
class RunSummary:
    """High-level run outcome for dry-run reporting and experiment control."""

    completed_trials: int
    aborted: bool
    aborted_after_trial_index: int | None
