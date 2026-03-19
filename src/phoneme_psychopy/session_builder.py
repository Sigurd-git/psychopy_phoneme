from __future__ import annotations

from dataclasses import replace

from .models import TrialDefinition


PRACTICE_TRIALS_PER_SESSION = 2


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
        selected_trials = prepend_practice_trials(selected_trials)
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


def prepend_practice_trials(trials: list[TrialDefinition]) -> list[TrialDefinition]:
    """Create small practice blocks by cloning the first few trials of each session."""

    practice_trials: list[TrialDefinition] = []
    sessions_in_order = sorted({trial.session_type for trial in trials}, key=lambda value: 0 if value == "white" else 1)
    for session_type in sessions_in_order:
        session_trials = [trial for trial in trials if trial.session_type == session_type][:PRACTICE_TRIALS_PER_SESSION]
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
