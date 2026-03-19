from __future__ import annotations

import unittest

from phoneme_psychopy.models import TrialDefinition
from phoneme_psychopy.trial_runner import _build_response_prompt_text


class TrialRunnerPromptTests(unittest.TestCase):
    def test_response_prompt_hides_phoneme_label_by_default(self) -> None:
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
            block_index=1,
            trial_in_block=1,
        )

        prompt_text = _build_response_prompt_text(trial)

        self.assertNotIn("Phoneme label:", prompt_text)
        self.assertNotIn("Track:", prompt_text)
        self.assertNotIn("Condition:", prompt_text)
        self.assertNotIn("SNR:", prompt_text)
        self.assertNotIn("z", prompt_text)
        self.assertIn("Please repeat what you heard.", prompt_text)

    def test_response_prompt_can_show_phoneme_label_for_debugging(self) -> None:
        trial = TrialDefinition(
            track_id="2B",
            snr=5.0,
            onset_label="31:00",
            phoneme="ʃ",
            session_type="babble",
            trial_index=101,
            source_sheet="Template",
            source_row=2,
            source_column="E",
            block_index=2,
            trial_in_block=4,
        )

        prompt_text = _build_response_prompt_text(trial, show_phoneme_label=True)

        self.assertIn("Phoneme label: ʃ", prompt_text)


if __name__ == "__main__":
    unittest.main()
