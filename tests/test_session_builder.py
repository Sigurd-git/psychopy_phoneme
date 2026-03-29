from __future__ import annotations

import unittest

from phoneme_psychopy.models import TrialDefinition
from phoneme_psychopy.session_builder import build_session_trials


def _trial(
    *,
    track_id: str,
    snr: float,
    phoneme: str,
    session_type: str,
    trial_index: int,
    onset_label: str,
) -> TrialDefinition:
    return TrialDefinition(
        track_id=track_id,
        snr=snr,
        onset_label=onset_label,
        phoneme=phoneme,
        session_type=session_type,
        trial_index=trial_index,
        source_sheet="Template",
        source_row=trial_index,
        source_column="D",
    )


class SessionBuilderTests(unittest.TestCase):
    def test_build_session_trials_prepends_one_snr_zero_practice_trial_per_phoneme(self) -> None:
        all_trials = [
            _trial(track_id="1A", snr=10.0, phoneme="z", session_type="white", trial_index=1, onset_label="07:00"),
            _trial(track_id="1C", snr=0.0, phoneme="z", session_type="white", trial_index=2, onset_label="09:00"),
            _trial(track_id="1C", snr=0.0, phoneme="s", session_type="white", trial_index=3, onset_label="11:00"),
            _trial(track_id="1B", snr=5.0, phoneme="s", session_type="white", trial_index=4, onset_label="13:00"),
            _trial(track_id="1C", snr=0.0, phoneme="z", session_type="white", trial_index=5, onset_label="15:00"),
        ]

        session_trials = build_session_trials(all_trials, "white", include_practice=True)

        practice_trials = [trial for trial in session_trials if trial.is_practice]
        experiment_trials = [trial for trial in session_trials if not trial.is_practice]

        self.assertEqual([trial.phoneme for trial in practice_trials], ["z", "s"])
        self.assertEqual([trial.snr for trial in practice_trials], [0.0, 0.0])
        self.assertEqual([trial.track_id for trial in practice_trials], ["1C", "1C"])
        self.assertEqual([trial.trial_index for trial in practice_trials], [-1, -2])
        self.assertEqual([trial.trial_in_block for trial in practice_trials], [1, 2])
        self.assertTrue(all(trial.block_index == 0 for trial in practice_trials))
        self.assertEqual([trial.trial_index for trial in experiment_trials], [1, 2, 3, 4, 5])
        self.assertTrue(all(not trial.is_practice for trial in experiment_trials))
        self.assertEqual([trial.block_index for trial in experiment_trials], [1, 1, 1, 1, 1])

    def test_build_session_trials_uses_only_white_practice_in_both_mode(self) -> None:
        all_trials = [
            _trial(track_id="2C", snr=0.0, phoneme="u", session_type="babble", trial_index=1, onset_label="07:00"),
            _trial(track_id="1C", snr=0.0, phoneme="z", session_type="white", trial_index=2, onset_label="09:00"),
            _trial(track_id="2C", snr=0.0, phoneme="f", session_type="babble", trial_index=3, onset_label="11:00"),
            _trial(track_id="1C", snr=0.0, phoneme="s", session_type="white", trial_index=4, onset_label="13:00"),
            _trial(track_id="2A", snr=10.0, phoneme="u", session_type="babble", trial_index=5, onset_label="15:00"),
            _trial(track_id="1A", snr=10.0, phoneme="z", session_type="white", trial_index=6, onset_label="17:00"),
        ]

        session_trials = build_session_trials(all_trials, "both", include_practice=True)

        practice_trials = [trial for trial in session_trials if trial.is_practice]

        self.assertEqual(
            [(trial.session_type, trial.phoneme, trial.snr) for trial in practice_trials],
            [("white", "z", 0.0), ("white", "s", 0.0)],
        )
        self.assertEqual([trial.trial_index for trial in practice_trials], [-1, -2])

    def test_build_session_trials_uses_white_practice_even_in_babble_mode(self) -> None:
        all_trials = [
            _trial(track_id="1C", snr=0.0, phoneme="z", session_type="white", trial_index=1, onset_label="09:00"),
            _trial(track_id="1C", snr=0.0, phoneme="s", session_type="white", trial_index=2, onset_label="13:00"),
            _trial(track_id="2C", snr=0.0, phoneme="u", session_type="babble", trial_index=3, onset_label="07:00"),
            _trial(track_id="2C", snr=0.0, phoneme="f", session_type="babble", trial_index=4, onset_label="11:00"),
            _trial(track_id="2A", snr=10.0, phoneme="u", session_type="babble", trial_index=5, onset_label="15:00"),
        ]

        session_trials = build_session_trials(all_trials, "babble", include_practice=True)

        practice_trials = [trial for trial in session_trials if trial.is_practice]
        experiment_trials = [trial for trial in session_trials if not trial.is_practice]

        self.assertEqual(
            [(trial.session_type, trial.phoneme, trial.snr) for trial in practice_trials],
            [("white", "z", 0.0), ("white", "s", 0.0)],
        )
        self.assertTrue(all(trial.block_index == 0 for trial in practice_trials))
        self.assertEqual([trial.session_type for trial in experiment_trials], ["babble", "babble", "babble"])
        self.assertEqual([trial.block_index for trial in experiment_trials], [1, 1, 1])


if __name__ == "__main__":
    unittest.main()
