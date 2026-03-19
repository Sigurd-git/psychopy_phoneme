from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time
from typing import Any

from .audio_recorder import BaseRecorder
from .logger import update_trial_log_after_recording, update_trial_status
from .models import RunSummary, TrialDefinition, TrialEventTimes


INSTRUCTION_TEXT = (
    "You will hear speech sounds in background noise.\n\n"
    "Listen carefully.\n"
    "After each sound, press SPACE to start recording your verbal response.\n"
    "Press SPACE again when you finish speaking.\n\n"
    "Press SPACE to begin or ESC to quit."
)


BLOCK_LABELS = {
    "white": "White noise block",
    "babble": "Babble noise block",
}


def run_placeholder_trials(
    window: Any,
    trials: list[TrialDefinition],
    recorder: BaseRecorder,
    trial_log_path: Path,
) -> RunSummary:
    """Run a conservative PsychoPy trial flow with playable stimuli and saved response audio."""

    from psychopy import core, event, sound, visual

    text_stimulus = visual.TextStim(window, color="white", height=0.05, wrapWidth=1.5, text="")
    fixation_stimulus = visual.TextStim(window, color="white", height=0.08, text="+")

    text_stimulus.text = INSTRUCTION_TEXT
    text_stimulus.draw()
    window.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if keys and "escape" in keys:
        return RunSummary(completed_trials=0, aborted=True, aborted_after_trial_index=None)

    current_block_index: int | None = None
    completed_trials = 0
    aborted_after_trial_index: int | None = None
    for trial in trials:
        if trial.block_index == 0 and trial.trial_in_block == 1:
            text_stimulus.text = (
                "Practice block\n\n"
                "These are short practice trials so the participant can learn the response rhythm.\n"
                "Press SPACE to continue."
            )
            text_stimulus.draw()
            window.flip()
            keys = event.waitKeys(keyList=["space", "escape"])
            if keys and "escape" in keys:
                update_trial_status(trial_log_path, trial, "aborted_before_start", "Run aborted at practice block entry")
                return RunSummary(completed_trials=completed_trials, aborted=True, aborted_after_trial_index=aborted_after_trial_index)

        if trial.block_index != 0 and trial.block_index != current_block_index:
            if current_block_index is not None:
                text_stimulus.text = "Take a short break.\n\nPress SPACE when you are ready for the next block."
                text_stimulus.draw()
                window.flip()
                keys = event.waitKeys(keyList=["space", "escape"])
                if keys and "escape" in keys:
                    update_trial_status(trial_log_path, trial, "aborted_before_start", "Run aborted during break screen")
                    return RunSummary(completed_trials=completed_trials, aborted=True, aborted_after_trial_index=aborted_after_trial_index)

            current_block_index = trial.block_index
            text_stimulus.text = (
                f"Block {trial.block_index}\n"
                f"{BLOCK_LABELS.get(trial.session_type, trial.session_type.title())}\n\n"
                "Press SPACE to continue."
            )
            text_stimulus.draw()
            window.flip()
            keys = event.waitKeys(keyList=["space", "escape"])
            if keys and "escape" in keys:
                update_trial_status(trial_log_path, trial, "aborted_before_start", "Run aborted at block entry")
                return RunSummary(completed_trials=completed_trials, aborted=True, aborted_after_trial_index=aborted_after_trial_index)

        fixation_stimulus.draw()
        window.flip()
        core.wait(0.5)

        stimulus_onset_time = datetime.now().isoformat(timespec="seconds")
        if trial.stimulus_file and Path(trial.stimulus_file).exists():
            sound_stimulus = sound.Sound(str(trial.stimulus_file))
            sound_stimulus.play()
            core.wait(sound_stimulus.getDuration())

        phase_label = "Practice" if trial.is_practice else f"Block {trial.block_index}"
        text_stimulus.text = (
            f"{phase_label} · Trial {trial.trial_in_block}\n"
            f"Track: {trial.track_id}\n"
            f"Condition: {trial.session_type}\n"
            f"SNR: {trial.snr}\n"
            f"Phoneme label: {trial.phoneme}\n\n"
            "Please repeat what you heard.\n"
            "Press SPACE to start recording, or ESC to quit."
        )
        text_stimulus.draw()
        window.flip()
        response_prompt_time = datetime.now().isoformat(timespec="seconds")
        response_prompt_monotonic = time.perf_counter()
        keys = event.waitKeys(keyList=["space", "escape"])
        if keys and "escape" in keys:
            update_trial_status(trial_log_path, trial, "aborted_before_recording", "Run aborted at response prompt")
            aborted_after_trial_index = trial.trial_index
            break

        recording_start_reaction_time_seconds = time.perf_counter() - response_prompt_monotonic
        recording_prompt_display_time = datetime.now().isoformat(timespec="seconds")
        recorder.start_trial_recording(trial)
        text_stimulus.text = "Recording...\nPress SPACE when finished speaking."
        text_stimulus.draw()
        window.flip()
        keys = event.waitKeys(keyList=["space", "escape"])
        if keys and "escape" in keys:
            update_trial_status(trial_log_path, trial, "aborted_during_recording", "Run aborted while recording response")
            aborted_after_trial_index = trial.trial_index
            break

        recording_result = recorder.stop_trial_recording()
        event_times = TrialEventTimes(
            stimulus_onset_time=stimulus_onset_time,
            response_prompt_time=response_prompt_time,
            recording_start_reaction_time_seconds=recording_start_reaction_time_seconds,
            recording_prompt_display_time=recording_prompt_display_time,
        )
        update_trial_log_after_recording(trial_log_path, trial, recording_result, event_times)
        completed_trials += 1

        text_stimulus.text = "Response saved.\nPreparing next trial..."
        text_stimulus.draw()
        window.flip()
        core.wait(0.4)

    if aborted_after_trial_index is None and completed_trials == len(trials):
        text_stimulus.text = "This session is complete.\n\nThank you."
        text_stimulus.draw()
        window.flip()
        core.wait(1.0)
        return RunSummary(completed_trials=completed_trials, aborted=False, aborted_after_trial_index=None)

    return RunSummary(
        completed_trials=completed_trials,
        aborted=aborted_after_trial_index is not None,
        aborted_after_trial_index=aborted_after_trial_index,
    )


def run_simulated_trials(
    trials: list[TrialDefinition],
    recorder: BaseRecorder,
    trial_log_path: Path,
    abort_after_trial_count: int | None = None,
) -> RunSummary:
    """Run a non-GUI validation path that still writes recordings and finalizes the trial log."""

    completed_trials = 0
    aborted_after_trial_index: int | None = None
    for completed_count_before_trial, trial in enumerate(trials):
        if abort_after_trial_count is not None and completed_count_before_trial >= abort_after_trial_count:
            update_trial_status(trial_log_path, trial, "aborted_before_start", "Dry-run simulated early stop")
            aborted_after_trial_index = trials[completed_count_before_trial - 1].trial_index if completed_count_before_trial > 0 else None
            break

        stimulus_onset_time = datetime.now().isoformat(timespec="seconds")
        time.sleep(0.01)
        response_prompt_time = datetime.now().isoformat(timespec="seconds")
        response_prompt_monotonic = time.perf_counter()
        time.sleep(0.01)
        recording_start_reaction_time_seconds = time.perf_counter() - response_prompt_monotonic
        recording_prompt_display_time = datetime.now().isoformat(timespec="seconds")
        recorder.start_trial_recording(trial)
        time.sleep(0.01)
        recording_result = recorder.stop_trial_recording()
        event_times = TrialEventTimes(
            stimulus_onset_time=stimulus_onset_time,
            response_prompt_time=response_prompt_time,
            recording_start_reaction_time_seconds=recording_start_reaction_time_seconds,
            recording_prompt_display_time=recording_prompt_display_time,
        )
        update_trial_log_after_recording(
            trial_log_path,
            trial,
            recording_result,
            event_times,
            notes="dry-run simulated recording",
        )
        completed_trials += 1

    return RunSummary(
        completed_trials=completed_trials,
        aborted=aborted_after_trial_index is not None,
        aborted_after_trial_index=aborted_after_trial_index,
    )
