from __future__ import annotations

from pathlib import Path

import pandas as pd

from .audio_preprocess import MANIFEST_PATH
from .config import PROJECT_ROOT
from .models import TrialDefinition


MANIFEST_REQUIRED_COLUMNS = {
    "trial_index",
    "track_id",
    "phoneme",
    "session_type",
    "snr",
    "onset_label",
    "stimulus_file",
    "noise_file",
    "clean_file",
}


def attach_generated_stimulus_paths(
    trials: list[TrialDefinition],
    manifest_path: Path = MANIFEST_PATH,
    project_root: Path = PROJECT_ROOT,
) -> list[TrialDefinition]:
    """Attach pre-generated file paths to trial records when a manifest is available."""

    if not manifest_path.exists():
        return trials

    manifest_frame = pd.read_csv(manifest_path)
    missing_columns = MANIFEST_REQUIRED_COLUMNS.difference(manifest_frame.columns)
    if missing_columns:
        raise ValueError(f"Stimulus manifest missing columns: {sorted(missing_columns)}")

    manifest_rows = manifest_frame.to_dict("records")
    manifest_rows_by_trial_index = {
        int(manifest_row["trial_index"]): manifest_row for manifest_row in manifest_rows
    }
    manifest_rows_by_metadata = {
        _manifest_metadata_key(manifest_row): manifest_row for manifest_row in manifest_rows
    }
    for trial in trials:
        trial_metadata_key = _trial_metadata_key(trial)
        manifest_row = manifest_rows_by_trial_index.get(trial.trial_index)
        if manifest_row is not None and _manifest_metadata_key(manifest_row) != trial_metadata_key:
            manifest_row = None
        if manifest_row is None:
            manifest_row = manifest_rows_by_metadata.get(trial_metadata_key)
        if manifest_row is None:
            continue
        trial.stimulus_file = _resolve_manifest_path(manifest_row["stimulus_file"], manifest_path, project_root)
        trial.noise_file = _resolve_manifest_path(manifest_row["noise_file"], manifest_path, project_root)
    return trials


def find_trials_missing_stimuli(trials: list[TrialDefinition]) -> list[TrialDefinition]:
    """Return trials whose resolved stimulus file is still unavailable."""

    return [trial for trial in trials if trial.stimulus_file is None or not trial.stimulus_file.exists()]


def _trial_metadata_key(trial: TrialDefinition) -> tuple[str, str, str, str, float]:
    return (
        trial.track_id,
        trial.onset_label,
        trial.phoneme,
        trial.session_type,
        float(trial.snr),
    )


def _manifest_metadata_key(manifest_row: dict[str, object]) -> tuple[str, str, str, str, float]:
    return (
        str(manifest_row["track_id"]),
        str(manifest_row["onset_label"]),
        str(manifest_row["phoneme"]),
        str(manifest_row["session_type"]),
        float(manifest_row["snr"]),
    )


def _resolve_manifest_path(raw_path: object, manifest_path: Path, project_root: Path) -> Path | None:
    raw_path_text = str(raw_path).strip()
    if not raw_path_text or raw_path_text.lower() == "nan":
        return None

    parsed_path = Path(raw_path_text)
    if parsed_path.exists():
        return parsed_path

    candidate_paths: list[Path] = []
    if parsed_path.is_absolute():
        if "stimuli" in parsed_path.parts:
            stimuli_index = parsed_path.parts.index("stimuli")
            candidate_paths.append(project_root.joinpath(*parsed_path.parts[stimuli_index:]))
    else:
        candidate_paths.append((project_root / parsed_path).resolve())
        candidate_paths.append((manifest_path.parent / parsed_path).resolve())

    for candidate_path in candidate_paths:
        if candidate_path.exists():
            return candidate_path

    if candidate_paths:
        return candidate_paths[0]
    return parsed_path
