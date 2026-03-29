from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from phoneme_psychopy.audio_recorder import build_recording_path
from phoneme_psychopy.io_utils import create_run_paths, find_existing_recordings
from phoneme_psychopy.logger import initialize_trial_log
from phoneme_psychopy.models import TrialDefinition


def _build_trial(trial_index: int, phoneme: str, is_practice: bool = False) -> TrialDefinition:
    return TrialDefinition(
        track_id="1A",
        snr=10.0,
        onset_label="07:00",
        phoneme=phoneme,
        session_type="white",
        trial_index=trial_index,
        source_sheet="Template",
        source_row=1,
        source_column="D",
        block_index=0 if is_practice else 1,
        trial_in_block=1 if is_practice else trial_index,
        is_practice=is_practice,
    )


class ResumeRunTests(unittest.TestCase):
    def test_create_run_paths_reuses_requested_subfolder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            run_paths = create_run_paths(
                "ignored-subject",
                data_dir,
                run_subfolder="sub-Sasha/run-20260329_113244",
            )

            self.assertEqual(
                run_paths.run_dir,
                data_dir / "sub-Sasha" / "run-20260329_113244",
            )
            self.assertTrue(run_paths.logs_dir.exists())
            self.assertTrue(run_paths.recordings_dir.exists())

    def test_find_existing_recordings_detects_expected_trials(self) -> None:
        trial_one = _build_trial(1, "z")
        trial_two = _build_trial(2, "s")

        with tempfile.TemporaryDirectory() as temp_dir:
            recordings_dir = Path(temp_dir) / "recordings"
            recordings_dir.mkdir(parents=True, exist_ok=True)
            build_recording_path(recordings_dir, trial_one).write_bytes(b"stub")

            existing_recordings = find_existing_recordings(recordings_dir, [trial_one, trial_two])

        self.assertEqual(existing_recordings, {1: recordings_dir / build_recording_path(recordings_dir, trial_one).name})

    def test_initialize_trial_log_marks_existing_recordings_completed(self) -> None:
        practice_trial = _build_trial(-1, "v", is_practice=True)
        main_trial = _build_trial(1, "z")

        with tempfile.TemporaryDirectory() as temp_dir:
            trial_log_path = Path(temp_dir) / "trial_log.csv"
            recordings_dir = Path(temp_dir) / "recordings"
            recordings_dir.mkdir(parents=True, exist_ok=True)

            practice_recording = build_recording_path(recordings_dir, practice_trial)
            practice_recording.write_bytes(b"stub")

            initialize_trial_log(
                trial_log_path,
                [practice_trial, main_trial],
                existing_recordings={practice_trial.trial_index: practice_recording},
            )
            trial_log_frame = pd.read_csv(trial_log_path, dtype=str, keep_default_na=False)

        practice_row = trial_log_frame.loc[trial_log_frame["trial_index"] == "-1"].iloc[0]
        main_row = trial_log_frame.loc[trial_log_frame["trial_index"] == "1"].iloc[0]
        self.assertEqual(practice_row["trial_status"], "completed")
        self.assertEqual(practice_row["completed"], "True")
        self.assertEqual(practice_row["recording_file"], practice_recording.as_posix())
        self.assertEqual(main_row["trial_status"], "pending")
        self.assertEqual(main_row["completed"], "False")


if __name__ == "__main__":
    unittest.main()
