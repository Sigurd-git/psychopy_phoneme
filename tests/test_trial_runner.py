from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from phoneme_psychopy.audio_recorder import RecordingResult
from phoneme_psychopy.models import TrialDefinition
from phoneme_psychopy.trial_runner import _build_response_prompt_text, run_placeholder_trials


class _FakeWindow:
    def flip(self) -> None:
        pass


class _FakeTextStim:
    def __init__(self, window: _FakeWindow, color: str, height: float, text: str, wrapWidth: float | None = None) -> None:
        del window, color, height, wrapWidth
        self.text = text

    def draw(self) -> None:
        pass


class _FakeEventModule:
    def __init__(self, key_batches: list[list[str]]) -> None:
        self._key_batches = list(key_batches)
        self.calls: list[list[str]] = []

    def waitKeys(self, keyList: list[str]) -> list[str]:
        self.calls.append(list(keyList))
        if not self._key_batches:
            raise AssertionError("waitKeys called more times than expected")
        return self._key_batches.pop(0)


class _FakeRecorder:
    def __init__(self) -> None:
        self.started_trials: list[int] = []
        self.stopped_trials: list[int] = []
        self._active_trial: TrialDefinition | None = None

    def start_trial_recording(self, trial: TrialDefinition) -> None:
        self._active_trial = trial
        self.started_trials.append(trial.trial_index)

    def stop_trial_recording(self) -> RecordingResult:
        if self._active_trial is None:
            raise AssertionError("stop_trial_recording called before start_trial_recording")

        trial = self._active_trial
        self.stopped_trials.append(trial.trial_index)
        self._active_trial = None
        return RecordingResult(
            recording_file=Path(f"/tmp/trial-{trial.trial_index:03d}.wav"),
            recording_started_at="2026-03-26T10:00:00",
            recording_stopped_at="2026-03-26T10:00:01",
            recording_duration_seconds=1.0,
            backend="fake",
        )


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
        self.assertIn("Recording has started automatically.", prompt_text)

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

    def test_run_placeholder_trials_starts_recording_automatically_and_waits_for_next_trial_space(self) -> None:
        trials = [
            TrialDefinition(
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
            ),
            TrialDefinition(
                track_id="1A",
                snr=10.0,
                onset_label="09:00",
                phoneme="s",
                session_type="white",
                trial_index=2,
                source_sheet="Template",
                source_row=2,
                source_column="E",
                block_index=1,
                trial_in_block=2,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            stimulus_paths = []
            for trial in trials:
                stimulus_path = Path(temp_dir) / f"stimulus-{trial.trial_index}.wav"
                stimulus_path.write_bytes(b"stub")
                trial.stimulus_file = stimulus_path
                stimulus_paths.append(stimulus_path)

            fake_event = _FakeEventModule(
                [
                    ["space"],
                    ["space"],
                    ["space"],
                    ["space"],
                    ["space"],
                ]
            )
            fake_core = types.SimpleNamespace(wait=lambda seconds: None)
            fake_visual = types.SimpleNamespace(TextStim=_FakeTextStim)
            fake_psychopy = types.ModuleType("psychopy")
            fake_psychopy.core = fake_core
            fake_psychopy.event = fake_event
            fake_psychopy.visual = fake_visual
            recorder = _FakeRecorder()
            playback_calls: list[Path] = []
            log_calls: list[int] = []

            with (
                mock.patch.dict(
                    sys.modules,
                    {
                        "psychopy": fake_psychopy,
                        "psychopy.core": fake_core,
                        "psychopy.event": fake_event,
                        "psychopy.visual": fake_visual,
                    },
                ),
                mock.patch(
                    "phoneme_psychopy.trial_runner.play_audio_file",
                    side_effect=lambda path: playback_calls.append(path),
                ),
                mock.patch(
                    "phoneme_psychopy.trial_runner.update_trial_log_after_recording",
                    side_effect=lambda *args, **kwargs: log_calls.append(args[1].trial_index),
                ),
                mock.patch("phoneme_psychopy.trial_runner.update_trial_status") as mock_update_status,
            ):
                summary = run_placeholder_trials(
                    _FakeWindow(),
                    trials,
                    recorder,
                    Path(temp_dir) / "trial_log.csv",
                )

        self.assertFalse(summary.aborted)
        self.assertEqual(summary.completed_trials, 2)
        self.assertEqual(playback_calls, stimulus_paths)
        self.assertEqual(recorder.started_trials, [1, 2])
        self.assertEqual(recorder.stopped_trials, [1, 2])
        self.assertEqual(log_calls, [1, 2])
        self.assertEqual(len(fake_event.calls), 5)
        mock_update_status.assert_not_called()


if __name__ == "__main__":
    unittest.main()
