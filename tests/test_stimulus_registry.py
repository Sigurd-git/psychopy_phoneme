from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from phoneme_psychopy.models import TrialDefinition
from phoneme_psychopy.stimulus_registry import (
    attach_generated_stimulus_paths,
    find_trials_missing_stimuli,
)


class StimulusRegistryTests(unittest.TestCase):
    def test_attach_generated_stimulus_paths_rewrites_legacy_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            stimulus_path = project_root / "stimuli" / "mixed" / "white" / "snr_10" / "trial-001.wav"
            noise_path = project_root / "stimuli" / "noise" / "white.wav"
            stimulus_path.parent.mkdir(parents=True, exist_ok=True)
            noise_path.parent.mkdir(parents=True, exist_ok=True)
            stimulus_path.write_bytes(b"fake wav")
            noise_path.write_bytes(b"fake wav")

            manifest_path = project_root / "stimuli" / "mixed" / "manifest.csv"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with manifest_path.open("w", newline="", encoding="utf-8") as manifest_file:
                writer = csv.DictWriter(
                    manifest_file,
                    fieldnames=[
                        "trial_index",
                        "track_id",
                        "phoneme",
                        "session_type",
                        "snr",
                        "onset_label",
                        "stimulus_file",
                        "noise_file",
                        "clean_file",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "trial_index": 1,
                        "track_id": "1A",
                        "phoneme": "z",
                        "session_type": "white",
                        "snr": 10.0,
                        "onset_label": "07:00",
                        "stimulus_file": "/workspace/projects/psychopy_phoneme/stimuli/mixed/white/snr_10/trial-001.wav",
                        "noise_file": "/workspace/projects/psychopy_phoneme/stimuli/noise/white.wav",
                        "clean_file": "/workspace/projects/psychopy_phoneme/stimuli/phonemes/z.wav",
                    }
                )

            trial = TrialDefinition(
                track_id="1A",
                snr=10.0,
                onset_label="07:00",
                phoneme="z",
                session_type="white",
                trial_index=1,
                source_sheet="Template",
                source_row=1,
                source_column="D",
            )

            attach_generated_stimulus_paths([trial], manifest_path=manifest_path, project_root=project_root)

            self.assertEqual(trial.stimulus_file, stimulus_path)
            self.assertEqual(trial.noise_file, noise_path)
            self.assertEqual(find_trials_missing_stimuli([trial]), [])

    def test_attach_generated_stimulus_paths_matches_practice_trials_by_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            stimulus_path = project_root / "stimuli" / "mixed" / "babble" / "snr_5" / "trial-101.wav"
            noise_path = project_root / "stimuli" / "noise" / "babble.wav"
            stimulus_path.parent.mkdir(parents=True, exist_ok=True)
            noise_path.parent.mkdir(parents=True, exist_ok=True)
            stimulus_path.write_bytes(b"fake wav")
            noise_path.write_bytes(b"fake wav")

            manifest_path = project_root / "stimuli" / "mixed" / "manifest.csv"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with manifest_path.open("w", newline="", encoding="utf-8") as manifest_file:
                writer = csv.DictWriter(
                    manifest_file,
                    fieldnames=[
                        "trial_index",
                        "track_id",
                        "phoneme",
                        "session_type",
                        "snr",
                        "onset_label",
                        "stimulus_file",
                        "noise_file",
                        "clean_file",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "trial_index": 101,
                        "track_id": "2B",
                        "phoneme": "ʃ",
                        "session_type": "babble",
                        "snr": 5.0,
                        "onset_label": "31:00",
                        "stimulus_file": stimulus_path.as_posix(),
                        "noise_file": noise_path.as_posix(),
                        "clean_file": (project_root / "stimuli" / "phonemes" / "esh.wav").as_posix(),
                    }
                )

            practice_trial = TrialDefinition(
                track_id="2B",
                snr=5.0,
                onset_label="31:00",
                phoneme="ʃ",
                session_type="babble",
                trial_index=-1,
                source_sheet="Template",
                source_row=2,
                source_column="E",
                block_index=0,
                trial_in_block=1,
                is_practice=True,
            )

            attach_generated_stimulus_paths([practice_trial], manifest_path=manifest_path, project_root=project_root)

            self.assertEqual(practice_trial.stimulus_file, stimulus_path)
            self.assertEqual(practice_trial.noise_file, noise_path)


if __name__ == "__main__":
    unittest.main()
