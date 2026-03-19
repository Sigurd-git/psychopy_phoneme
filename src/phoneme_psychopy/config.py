from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent
DEFAULT_SCHEDULE_PATH = PROJECT_ROOT / "Speech_on_the_Brain_stimuli_tracking.xlsx"
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_AUDIO_DIR = PROJECT_ROOT / "stimuli" / "phonemes"
DEFAULT_NOISE_DIR = PROJECT_ROOT / "stimuli" / "noise"


@dataclass(slots=True)
class ExperimentConfig:
    """Top-level experiment options selected before the run starts."""

    subject_id: str
    session_type: str
    fullscreen: bool
    practice_enabled: bool
    simulate_recording: bool = False
    recording_sample_rate: int = 44100
    recording_channels: int = 1
    schedule_path: Path = DEFAULT_SCHEDULE_PATH
    data_dir: Path = DEFAULT_DATA_DIR
    audio_dir: Path = DEFAULT_AUDIO_DIR
    noise_dir: Path = DEFAULT_NOISE_DIR
