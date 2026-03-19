from __future__ import annotations

import json

from .audio_recorder import create_recorder
from .io_utils import create_run_paths
from .logger import initialize_trial_log
from .schedule_loader import build_trial_preview_table, load_trials_from_workbook
from .session_builder import build_session_trials
from .stimulus_registry import attach_generated_stimulus_paths, find_trials_missing_stimuli
from .trial_runner import run_headless_trials, run_placeholder_trials
from .ui import build_config_from_cli, parse_cli_args, summarize_config


def main() -> None:
    """Entry point for the PsychoPy phoneme experiment scaffold."""

    args = parse_cli_args()
    config = build_config_from_cli(args)

    all_trials = load_trials_from_workbook(config.schedule_path)
    session_trials = build_session_trials(
        all_trials,
        config.session_type,
        include_practice=config.practice_enabled,
    )
    session_trials = attach_generated_stimulus_paths(session_trials)
    if args.max_trials is not None:
        session_trials = session_trials[: args.max_trials]
    if not args.dry_run:
        missing_stimulus_trials = find_trials_missing_stimuli(session_trials)
        if missing_stimulus_trials:
            preview_lines = [
                (
                    f"trial_index={trial.trial_index}, track={trial.track_id}, "
                    f"phoneme={trial.phoneme}, path={trial.stimulus_file}"
                )
                for trial in missing_stimulus_trials[:5]
            ]
            raise FileNotFoundError(
                "Resolved stimulus files are missing for one or more trials.\n"
                + "\n".join(preview_lines)
                + "\nRegenerate the stimuli manifest with `uv run phoneme-preprocess` if needed."
            )

    run_paths = create_run_paths(config.subject_id, config.data_dir)
    initialize_trial_log(run_paths.trial_log_path, session_trials)

    preview_frame = build_trial_preview_table(session_trials)
    preview_path = run_paths.logs_dir / "trial_preview.csv"
    preview_frame.to_csv(preview_path, index=False)

    recorder = create_recorder(
        recordings_dir=run_paths.recordings_dir,
        sample_rate=config.recording_sample_rate,
        channels=config.recording_channels,
    )

    if args.dry_run:
        run_summary = run_headless_trials(
            session_trials,
            recorder,
            run_paths.trial_log_path,
            abort_after_trial_count=args.abort_after_trials,
        )
        dry_run_summary = {
            "config": summarize_config(config),
            "n_all_trials": len(all_trials),
            "n_session_trials": len(session_trials),
            "trial_log_path": run_paths.trial_log_path.as_posix(),
            "trial_preview_path": preview_path.as_posix(),
            "recordings_dir": run_paths.recordings_dir.as_posix(),
            "recording_backend": recorder.backend_name,
            "completed_trials": run_summary.completed_trials,
            "aborted": run_summary.aborted,
            "aborted_after_trial_index": run_summary.aborted_after_trial_index,
        }
        print(json.dumps(dry_run_summary, indent=2))
        return

    from psychopy import visual

    window = visual.Window(fullscr=config.fullscreen, color="black", units="height")
    try:
        run_placeholder_trials(
            window,
            session_trials,
            recorder,
            run_paths.trial_log_path,
            show_phoneme_label=config.show_phoneme_label,
        )
    finally:
        window.close()


if __name__ == "__main__":
    main()
