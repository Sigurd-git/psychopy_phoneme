from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time
from typing import Any

from .audio_playback import play_audio_file
from .audio_recorder import BaseRecorder
from .logger import update_trial_log_after_recording, update_trial_status
from .models import RunSummary, TrialDefinition, TrialEventTimes


INSTRUCTION_TEXT = (
    "You will hear speech sounds in background noise.\n\n"
    "Listen carefully.\n"
    "After each sound, recording will start automatically for your verbal response.\n"
    "Press SPACE when you finish speaking.\n"
    "Press SPACE again to begin the next sound.\n\n"
    "Press SPACE to begin or ESC to quit."
)


BLOCK_LABELS = {
    "white": "White noise block",
    "babble": "Babble noise block",
}


def _build_response_prompt_text(trial: TrialDefinition, show_phoneme_label: bool = False) -> str:
    """Build the participant-facing response prompt, hiding the target phoneme by default."""

    phase_label = "Practice" if trial.is_practice else f"Block {trial.block_index}"
    prompt_lines = [
        f"{phase_label} · Trial {trial.trial_in_block}",
    ]
    if show_phoneme_label:
        prompt_lines.append(f"Phoneme label: {trial.phoneme}")
    prompt_lines.extend(
        [
            "",
            "Please repeat what you heard.",
            "Recording has started automatically.",
            "Press SPACE when you finish speaking, or ESC to quit.",
        ]
    )
    return "\n".join(prompt_lines)


def run_placeholder_trials(
    window: Any,
    trials: list[TrialDefinition],
    recorder: BaseRecorder,
    trial_log_path: Path,
    show_phoneme_label: bool = False,
) -> RunSummary:
    """Run a conservative PsychoPy trial flow with playable stimuli and saved response audio."""

    from psychopy import core, event, visual

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
    for trial_position, trial in enumerate(trials):
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
        if trial.stimulus_file is None:
            raise FileNotFoundError(
                f"Trial {trial.trial_index} ({trial.track_id}, {trial.phoneme}) has no resolved stimulus file."
            )

        stimulus_path = Path(trial.stimulus_file)
        if not stimulus_path.exists():
            raise FileNotFoundError(
                f"Trial {trial.trial_index} ({trial.track_id}, {trial.phoneme}) stimulus file does not exist: "
                f"{stimulus_path}"
            )

        play_audio_file(stimulus_path)

        response_prompt_time = datetime.now().isoformat(timespec="seconds")
        response_prompt_monotonic = time.perf_counter()
        recorder.start_trial_recording(trial)
        recording_start_reaction_time_seconds = time.perf_counter() - response_prompt_monotonic
        recording_prompt_display_time = datetime.now().isoformat(timespec="seconds")
        text_stimulus.text = _build_response_prompt_text(trial, show_phoneme_label=show_phoneme_label)
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

        if trial_position < len(trials) - 1:
            text_stimulus.text = "Response saved.\nPress SPACE to start the next sound."
            text_stimulus.draw()
            window.flip()
            keys = event.waitKeys(keyList=["space", "escape"])
            if keys and "escape" in keys:
                next_trial = trials[trial_position + 1]
                update_trial_status(trial_log_path, next_trial, "aborted_before_start", "Run aborted before next stimulus")
                aborted_after_trial_index = trial.trial_index
                break

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


def run_headless_trials(
    trials: list[TrialDefinition],
    recorder: BaseRecorder,
    trial_log_path: Path,
    abort_after_trial_count: int | None = None,
) -> RunSummary:
    """Run a non-GUI validation path that still records real audio and finalizes the trial log."""

    completed_trials = 0
    aborted_after_trial_index: int | None = None
    for completed_count_before_trial, trial in enumerate(trials):
        if abort_after_trial_count is not None and completed_count_before_trial >= abort_after_trial_count:
            update_trial_status(trial_log_path, trial, "aborted_before_start", "Dry-run early stop")
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
            notes="dry-run headless recording",
        )
        completed_trials += 1

    return RunSummary(
        completed_trials=completed_trials,
        aborted=aborted_after_trial_index is not None,
        aborted_after_trial_index=aborted_after_trial_index,
    )
