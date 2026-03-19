from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import time
import wave

import numpy as np

from .models import TrialDefinition


@dataclass(slots=True)
class RecordingResult:
    """Metadata returned after one recording segment is written to disk."""

    recording_file: Path
    recording_started_at: str
    recording_stopped_at: str
    recording_duration_seconds: float
    backend: str


class BaseRecorder:
    """Shared interface for experiment recording backends."""

    backend_name = "base"

    def __init__(self, recordings_dir: Path, sample_rate: int = 44100, channels: int = 1) -> None:
        self.recordings_dir = recordings_dir
        self.sample_rate = sample_rate
        self.channels = channels
        self._active_trial: TrialDefinition | None = None
        self._started_at_monotonic: float | None = None
        self._started_at_iso: str | None = None

    def start_trial_recording(self, trial: TrialDefinition) -> Path:
        self._active_trial = trial
        self._started_at_monotonic = time.perf_counter()
        self._started_at_iso = datetime.now().isoformat(timespec="seconds")
        return self.build_recording_path(trial)

    def stop_trial_recording(self) -> RecordingResult:
        raise NotImplementedError

    def build_recording_path(self, trial: TrialDefinition) -> Path:
        safe_phoneme_label = phoneme_to_filename_label(trial.phoneme)
        practice_prefix = "practice__" if trial.is_practice else ""
        file_name = (
            f"{practice_prefix}trial-{format_trial_index_label(trial.trial_index)}__track-{trial.track_id}"
            f"__phoneme-{safe_phoneme_label}__noise-{trial.session_type}__snr-{format_snr_label(trial.snr)}.wav"
        )
        return self.recordings_dir / file_name


class SoundDeviceRecorder(BaseRecorder):
    """Microphone recorder backed by sounddevice input streams."""

    backend_name = "sounddevice"

    def __init__(self, recordings_dir: Path, sample_rate: int = 44100, channels: int = 1) -> None:
        super().__init__(recordings_dir=recordings_dir, sample_rate=sample_rate, channels=channels)
        import sounddevice as sd

        self._sd = sd
        self._stream = None
        self._captured_chunks: list[np.ndarray] = []

    def start_trial_recording(self, trial: TrialDefinition) -> Path:
        recording_path = super().start_trial_recording(trial)
        self._captured_chunks = []

        def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
            del frames, time_info
            if status:
                print(f"Recording status warning: {status}")
            self._captured_chunks.append(indata.copy())

        self._stream = self._sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()
        return recording_path

    def stop_trial_recording(self) -> RecordingResult:
        if self._active_trial is None or self._started_at_monotonic is None or self._started_at_iso is None:
            raise RuntimeError("No active trial recording to stop.")

        recording_path = self.build_recording_path(self._active_trial)
        if self._stream is None:
            raise RuntimeError("Recording stream was not started.")

        self._stream.stop()
        self._stream.close()
        self._stream = None

        if self._captured_chunks:
            captured_audio = np.concatenate(self._captured_chunks, axis=0)
        else:
            captured_audio = np.zeros((1, self.channels), dtype=np.float32)

        write_wav_file(recording_path, captured_audio, self.sample_rate)

        stopped_at_iso = datetime.now().isoformat(timespec="seconds")
        duration_seconds = time.perf_counter() - self._started_at_monotonic
        return RecordingResult(
            recording_file=recording_path,
            recording_started_at=self._started_at_iso,
            recording_stopped_at=stopped_at_iso,
            recording_duration_seconds=duration_seconds,
            backend=self.backend_name,
        )


class SimulatedRecorder(BaseRecorder):
    """Test-friendly recorder that writes silent placeholder WAV files."""

    backend_name = "simulated"

    def stop_trial_recording(self) -> RecordingResult:
        if self._active_trial is None or self._started_at_monotonic is None or self._started_at_iso is None:
            raise RuntimeError("No active trial recording to stop.")

        recording_path = self.build_recording_path(self._active_trial)
        duration_seconds = max(time.perf_counter() - self._started_at_monotonic, 0.25)
        sample_count = max(int(round(duration_seconds * self.sample_rate)), 1)
        silent_audio = np.zeros((sample_count, self.channels), dtype=np.float32)
        write_wav_file(recording_path, silent_audio, self.sample_rate)

        stopped_at_iso = datetime.now().isoformat(timespec="seconds")
        return RecordingResult(
            recording_file=recording_path,
            recording_started_at=self._started_at_iso,
            recording_stopped_at=stopped_at_iso,
            recording_duration_seconds=duration_seconds,
            backend=self.backend_name,
        )


def create_recorder(recordings_dir: Path, simulate_recording: bool, sample_rate: int, channels: int) -> BaseRecorder:
    """Create the preferred recorder backend for the current environment."""

    if simulate_recording:
        return SimulatedRecorder(recordings_dir=recordings_dir, sample_rate=sample_rate, channels=channels)

    try:
        return SoundDeviceRecorder(recordings_dir=recordings_dir, sample_rate=sample_rate, channels=channels)
    except Exception as exc:  # pragma: no cover - depends on host audio stack
        raise RuntimeError(
            "Real microphone recording requires a working PortAudio backend. "
            "Install PortAudio on the target machine or rerun with --simulate-recording."
        ) from exc


def write_wav_file(output_path: Path, audio_samples: np.ndarray, sample_rate: int) -> None:
    """Write float audio in [-1, 1] to a PCM16 mono/stereo WAV file."""

    clipped_samples = np.clip(audio_samples, -1.0, 1.0)
    int16_samples = (clipped_samples * 32767.0).astype(np.int16)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(int16_samples.shape[1] if int16_samples.ndim > 1 else 1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(int16_samples.tobytes())


def phoneme_to_filename_label(phoneme: str) -> str:
    phoneme_map = {
        "θ": "theta",
        "ð": "eth",
        "ʃ": "esh",
    }
    return phoneme_map.get(phoneme, phoneme)


def format_snr_label(snr_value: float) -> str:
    if float(snr_value).is_integer():
        return str(int(snr_value))
    return str(snr_value).replace(".", "p")


def format_trial_index_label(trial_index: int) -> str:
    if trial_index < 0:
        return f"practice-{abs(trial_index):03d}"
    return f"{trial_index:03d}"
