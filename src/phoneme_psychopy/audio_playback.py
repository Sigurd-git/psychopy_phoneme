from __future__ import annotations

from pathlib import Path

from typing import Any


def _load_audio_modules() -> tuple[Any, Any]:
    import sounddevice as sd
    import soundfile as sf

    return sd, sf


def play_audio_file(audio_path: Path) -> None:
    """Play a prerecorded stimulus file through the default system output."""

    sd, sf = _load_audio_modules()

    try:
        audio_samples, sample_rate = sf.read(audio_path, always_2d=True, dtype="float32")
    except Exception as exc:
        raise RuntimeError(f"Could not read stimulus audio file: {audio_path}") from exc

    try:
        sd.play(audio_samples, sample_rate)
        sd.wait()
    except Exception as exc:
        try:
            sd.stop()
        except Exception:
            pass
        raise RuntimeError(
            "Stimulus playback requires a working PortAudio output device. "
            "Check the system audio output or rerun with --dry-run for a non-GUI validation pass."
        ) from exc
