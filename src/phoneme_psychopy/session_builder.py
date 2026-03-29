from __future__ import annotations

from dataclasses import replace

from .models import TrialDefinition


PRACTICE_SNR = 0.0


def build_session_trials(all_trials: list[TrialDefinition], session_type: str, include_practice: bool = False) -> list[TrialDefinition]:
    """Filter the full trial table into the requested experimental session."""

    normalized_session_type = session_type.lower()
    if normalized_session_type == "both":
        selected_trials = list(all_trials)
    else:
        allowed_session_types = {"babble", "white"}
        if normalized_session_type not in allowed_session_types:
            raise ValueError(f"Unsupported session_type: {session_type}")
        selected_trials = [trial for trial in all_trials if trial.session_type == normalized_session_type]

    assign_block_structure(selected_trials)
    if include_practice:
        selected_trials = prepend_practice_trials(selected_trials, all_trials)
    return selected_trials


def assign_block_structure(trials: list[TrialDefinition]) -> None:
    """Annotate trials with block indices and within-block counters."""

    block_index_by_session = {"white": 1, "babble": 2}
    if {trial.session_type for trial in trials} == {"babble"}:
        block_index_by_session = {"babble": 1}
    if {trial.session_type for trial in trials} == {"white"}:
        block_index_by_session = {"white": 1}

    block_trial_counts: dict[int, int] = {}
    for trial in trials:
        trial.block_index = block_index_by_session[trial.session_type]
        block_trial_counts.setdefault(trial.block_index, 0)
        block_trial_counts[trial.block_index] += 1
        trial.trial_in_block = block_trial_counts[trial.block_index]
        trial.is_practice = False


def prepend_practice_trials(
    trials: list[TrialDefinition],
    practice_source_trials: list[TrialDefinition],
) -> list[TrialDefinition]:
    """Create a white-noise practice block that covers each phoneme once at a fixed SNR."""

    practice_trials: list[TrialDefinition] = []
    session_trials = select_practice_trials_for_session(practice_source_trials, session_type="white")
    for practice_counter, trial in enumerate(session_trials, start=1):
        practice_trial = replace(
            trial,
            trial_index=-(len(practice_trials) + 1),
            block_index=0,
            trial_in_block=practice_counter,
            is_practice=True,
        )
        practice_trials.append(practice_trial)
    return practice_trials + trials


def select_practice_trials_for_session(trials: list[TrialDefinition], session_type: str) -> list[TrialDefinition]:
    """Return one SNR=0 trial per phoneme for the requested session."""

    seen_phonemes: set[str] = set()
    practice_trials: list[TrialDefinition] = []
    for trial in trials:
        if trial.session_type != session_type or float(trial.snr) != PRACTICE_SNR:
            continue
        if trial.phoneme in seen_phonemes:
            continue
        seen_phonemes.add(trial.phoneme)
        practice_trials.append(trial)
    return practice_trials
