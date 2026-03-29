from __future__ import annotations

from dataclasses import asdict
import argparse

from .config import ExperimentConfig


SESSION_CHOICES = {"white", "babble", "both"}


def _parse_bool_choice(raw_value: str) -> bool:
    return str(raw_value).strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_cli_args() -> argparse.Namespace:
    """Parse optional command-line overrides for debugging and headless runs."""

    parser = argparse.ArgumentParser(description="PsychoPy phoneme experiment scaffold")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the session without opening PsychoPy windows, but still record from the real microphone backend",
    )
    parser.add_argument("--subject-id", default="pilot001", help="Override subject identifier")
    parser.add_argument(
        "--session-type",
        default="both",
        choices=["babble", "white", "both"],
        help="Select which session to build",
    )
    parser.add_argument("--fullscreen", action="store_true", help="Open PsychoPy in fullscreen mode")
    parser.add_argument(
        "--practice",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable practice trials (default: enabled; use --no-practice to disable)",
    )
    parser.add_argument(
        "--show-phoneme-label",
        action="store_true",
        help="Display the target phoneme on the response screen for debugging",
    )
    parser.add_argument(
        "--max-trials",
        type=int,
        default=None,
        help="Optionally limit the number of trials for validation or pilot runs",
    )
    parser.add_argument(
        "--prompt-config",
        action="store_true",
        help="Prompt for run configuration in the terminal before starting",
    )
    parser.add_argument(
        "--abort-after-trials",
        type=int,
        default=None,
        help="Dry-run only: stop early after N completed trials to validate abort logging",
    )
    return parser.parse_args()


def prompt_for_config(args: argparse.Namespace) -> dict[str, object]:
    """Collect basic run configuration from terminal prompts instead of a GUI dialog.

    This avoids X11 / Tkinter crashes on Linux experiment machines where GUI toolkits conflict
    with PsychoPy's windowing stack.
    """

    defaults = {
        "subject_id": args.subject_id,
        "session_type": args.session_type,
        "fullscreen": args.fullscreen,
        "practice_enabled": args.practice,
        "show_phoneme_label": args.show_phoneme_label,
    }

    print("\nPhoneme Experiment Setup")
    print("Press ENTER to keep the default shown in brackets.\n")

    subject_input = input(f"Subject ID [{defaults['subject_id']}]: ").strip()
    subject_id = subject_input or str(defaults["subject_id"])

    while True:
        session_input = input(f"Session type [{defaults['session_type']}] (white/babble/both): ").strip().lower()
        if not session_input:
            session_type = str(defaults["session_type"])
            break
        if session_input in SESSION_CHOICES:
            session_type = session_input
            break
        print("Please enter one of: white, babble, both")

    fullscreen_input = input(f"Fullscreen [{defaults['fullscreen']}]: ").strip()
    practice_input = input(f"Practice block [{defaults['practice_enabled']}]: ").strip()
    show_phoneme_input = input(f"Show phoneme label [{defaults['show_phoneme_label']}]: ").strip()

    return {
        "subject_id": subject_id,
        "session_type": session_type,
        "fullscreen": _parse_bool_choice(fullscreen_input) if fullscreen_input else bool(defaults["fullscreen"]),
        "practice_enabled": _parse_bool_choice(practice_input) if practice_input else bool(defaults["practice_enabled"]),
        "show_phoneme_label": _parse_bool_choice(show_phoneme_input)
        if show_phoneme_input
        else bool(defaults["show_phoneme_label"]),
    }


def build_config_from_cli(args: argparse.Namespace) -> ExperimentConfig:
    """Create the configuration object from CLI options or terminal prompts."""

    if getattr(args, "prompt_config", False):
        prompted_values = prompt_for_config(args)
        return ExperimentConfig(
            subject_id=str(prompted_values["subject_id"]),
            session_type=str(prompted_values["session_type"]),
            fullscreen=bool(prompted_values["fullscreen"]),
            practice_enabled=bool(prompted_values["practice_enabled"]),
            show_phoneme_label=bool(prompted_values["show_phoneme_label"]),
        )

    return ExperimentConfig(
        subject_id=args.subject_id,
        session_type=args.session_type,
        fullscreen=args.fullscreen,
        practice_enabled=bool(args.practice),
        show_phoneme_label=args.show_phoneme_label,
    )


def summarize_config(config: ExperimentConfig) -> dict[str, object]:
    """Return a printable config summary for logs and dry runs."""

    config_summary = asdict(config)
    for key, value in list(config_summary.items()):
        if hasattr(value, "as_posix"):
            config_summary[key] = value.as_posix()
    return config_summary
