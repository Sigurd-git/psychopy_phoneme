from __future__ import annotations

from pathlib import Path

import pandas as pd

from .audio_preprocess import MANIFEST_PATH
from .models import TrialDefinition


MANIFEST_REQUIRED_COLUMNS = {
    "trial_index",
    "stimulus_file",
    "noise_file",
    "clean_file",
}


def attach_generated_stimulus_paths(
    trials: list[TrialDefinition], manifest_path: Path = MANIFEST_PATH
) -> list[TrialDefinition]:
    """Attach pre-generated file paths to trial records when a manifest is available."""

    if not manifest_path.exists():
        return trials

    manifest_frame = pd.read_csv(manifest_path)
    missing_columns = MANIFEST_REQUIRED_COLUMNS.difference(manifest_frame.columns)
    if missing_columns:
        raise ValueError(f"Stimulus manifest missing columns: {sorted(missing_columns)}")

    manifest_rows = manifest_frame.set_index("trial_index").to_dict("index")
    for trial in trials:
        manifest_row = manifest_rows.get(trial.trial_index)
        if manifest_row is None:
            continue
        trial.stimulus_file = Path(str(manifest_row["stimulus_file"]))
        trial.noise_file = Path(str(manifest_row["noise_file"]))
    return trials
