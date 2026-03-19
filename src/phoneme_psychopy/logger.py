from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .audio_recorder import RecordingResult
from .models import TrialDefinition, TrialEventTimes


TRIAL_LOG_COLUMNS = [
    "trial_index",
    "block_index",
    "trial_in_block",
    "is_practice",
    "track_id",
    "session_type",
    "snr",
    "onset_label",
    "phoneme",
    "source_sheet",
    "source_row",
    "source_column",
    "stimulus_file",
    "noise_file",
    "trial_status",
    "stimulus_onset_time",
    "response_prompt_time",
    "recording_prompt_display_time",
    "recording_start_reaction_time_seconds",
    "participant_started_recording",
    "participant_stopped_recording",
    "recording_duration_seconds",
    "recording_backend",
    "recording_file",
    "completed",
    "notes",
]


def initialize_trial_log(trial_log_path: Path, trials: list[TrialDefinition]) -> None:
    """Write an initial trial log with placeholders for future recording events."""

    trial_rows: list[dict[str, object]] = []
    for trial in trials:
        row = asdict(trial)
        row.update(
            {
                "stimulus_file": str(trial.stimulus_file) if trial.stimulus_file else "",
                "noise_file": str(trial.noise_file) if trial.noise_file else "",
                "trial_status": "pending",
                "stimulus_onset_time": "",
                "response_prompt_time": "",
                "recording_prompt_display_time": "",
                "recording_start_reaction_time_seconds": "",
                "participant_started_recording": "",
                "participant_stopped_recording": "",
                "recording_duration_seconds": "",
                "recording_backend": "",
                "recording_file": "",
                "completed": False,
                "notes": "",
            }
        )
        trial_rows.append(row)

    trial_log_frame = pd.DataFrame(trial_rows)
    trial_log_frame = trial_log_frame[TRIAL_LOG_COLUMNS]
    trial_log_frame.to_csv(trial_log_path, index=False)


def update_trial_log_after_recording(
    trial_log_path: Path,
    trial: TrialDefinition,
    recording_result: RecordingResult,
    event_times: TrialEventTimes,
    notes: str = "",
) -> None:
    """Update one trial row after the participant response recording is saved."""

    trial_log_frame = pd.read_csv(trial_log_path, dtype=str, keep_default_na=False)
    target_rows = trial_log_frame["trial_index"] == str(trial.trial_index)
    if not target_rows.any():
        raise ValueError(f"Trial index {trial.trial_index} not found in trial log: {trial_log_path}")

    trial_log_frame.loc[target_rows, "trial_status"] = "completed"
    trial_log_frame.loc[target_rows, "stimulus_onset_time"] = event_times.stimulus_onset_time
    trial_log_frame.loc[target_rows, "response_prompt_time"] = event_times.response_prompt_time
    trial_log_frame.loc[target_rows, "recording_prompt_display_time"] = event_times.recording_prompt_display_time
    trial_log_frame.loc[target_rows, "recording_start_reaction_time_seconds"] = (
        f"{event_times.recording_start_reaction_time_seconds:.6f}"
    )
    trial_log_frame.loc[target_rows, "participant_started_recording"] = recording_result.recording_started_at
    trial_log_frame.loc[target_rows, "participant_stopped_recording"] = recording_result.recording_stopped_at
    trial_log_frame.loc[target_rows, "recording_duration_seconds"] = f"{recording_result.recording_duration_seconds:.6f}"
    trial_log_frame.loc[target_rows, "recording_backend"] = recording_result.backend
    trial_log_frame.loc[target_rows, "recording_file"] = recording_result.recording_file.as_posix()
    trial_log_frame.loc[target_rows, "completed"] = "True"
    trial_log_frame.loc[target_rows, "notes"] = notes
    trial_log_frame.to_csv(trial_log_path, index=False)


def update_trial_status(
    trial_log_path: Path,
    trial: TrialDefinition,
    trial_status: str,
    notes: str,
) -> None:
    """Update a trial row when the run exits early or the trial is skipped."""

    trial_log_frame = pd.read_csv(trial_log_path, dtype=str, keep_default_na=False)
    target_rows = trial_log_frame["trial_index"] == str(trial.trial_index)
    if not target_rows.any():
        raise ValueError(f"Trial index {trial.trial_index} not found in trial log: {trial_log_path}")

    trial_log_frame.loc[target_rows, "trial_status"] = trial_status
    trial_log_frame.loc[target_rows, "notes"] = notes
    trial_log_frame.to_csv(trial_log_path, index=False)
