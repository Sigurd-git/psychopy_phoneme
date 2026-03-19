from __future__ import annotations

import csv
import math
import random
import shutil
import wave
from dataclasses import dataclass
from pathlib import Path

import miniaudio
import numpy as np

from .config import DEFAULT_AUDIO_DIR, DEFAULT_NOISE_DIR, PROJECT_ROOT
from .schedule_loader import load_trials_from_workbook


PHONEME_FILE_MAP = {
    "a": "a.wav",
    "f": "f.wav",
    "i": "i.wav",
    "s": "s.wav",
    "u": "u.wav",
    "v": "v.wav",
    "z": "z.wav",
    "θ": "theta.wav",
    "ð": "backwards b with a cross.wav",
    "ʃ": "integralsign.wav",
}

NOISE_FILE_MAP = {
    "white": "white_noise.mp3",
    "babble": "babble.mp3",
}

DEFAULT_SAMPLE_RATE = 44_100
TARGET_RMS = 0.08
PEAK_LIMIT = 0.95
PREGENERATED_ROOT = PROJECT_ROOT / "stimuli"
MANIFEST_PATH = PREGENERATED_ROOT / "mixed" / "manifest.csv"


@dataclass(slots=True)
class AudioAsset:
    """Normalized mono waveform plus metadata."""

    samples: np.ndarray
    sample_rate: int


def decode_audio_file(audio_path: Path) -> AudioAsset:
    """Decode an audio file into mono float32 samples in the range [-1, 1]."""

    decoded = miniaudio.decode_file(str(audio_path))
    int_samples = np.asarray(decoded.samples, dtype=np.int16)
    if decoded.nchannels > 1:
        int_samples = int_samples.reshape(-1, decoded.nchannels).mean(axis=1)
    float_samples = int_samples.astype(np.float32) / 32768.0
    return AudioAsset(samples=float_samples, sample_rate=decoded.sample_rate)


def rms(samples: np.ndarray) -> float:
    """Return the root-mean-square amplitude of a waveform."""

    return float(np.sqrt(np.mean(np.square(samples), dtype=np.float64)))


def normalize_rms(samples: np.ndarray, target_rms: float = TARGET_RMS) -> np.ndarray:
    """Scale a waveform to a target RMS while preserving shape."""

    current_rms = rms(samples)
    if current_rms == 0:
        return samples.copy()
    return samples * (target_rms / current_rms)


def resample_if_needed(samples: np.ndarray, original_sample_rate: int, target_sample_rate: int) -> np.ndarray:
    """Resample with linear interpolation when sample rates differ."""

    if original_sample_rate == target_sample_rate:
        return samples
    original_positions = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
    target_length = int(round(len(samples) * target_sample_rate / original_sample_rate))
    target_positions = np.linspace(0.0, 1.0, num=target_length, endpoint=False)
    return np.interp(target_positions, original_positions, samples).astype(np.float32)


def write_wav_file(output_path: Path, samples: np.ndarray, sample_rate: int) -> None:
    """Write mono PCM16 WAV data."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clipped_samples = np.clip(samples, -1.0, 1.0)
    pcm16_samples = (clipped_samples * 32767.0).astype(np.int16)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm16_samples.tobytes())


def select_noise_segment(noise_samples: np.ndarray, segment_length: int, rng: random.Random) -> tuple[np.ndarray, int]:
    """Randomly crop a noise segment with the requested duration."""

    if len(noise_samples) < segment_length:
        repeats = int(math.ceil(segment_length / len(noise_samples)))
        noise_samples = np.tile(noise_samples, repeats)
    max_start = len(noise_samples) - segment_length
    start_index = rng.randint(0, max_start) if max_start > 0 else 0
    end_index = start_index + segment_length
    return noise_samples[start_index:end_index].copy(), start_index


def mix_at_snr(clean_samples: np.ndarray, noise_samples: np.ndarray, snr_db: float) -> tuple[np.ndarray, float]:
    """Mix clean and noise waveforms at the requested SNR in dB."""

    clean_rms = rms(clean_samples)
    noise_rms = rms(noise_samples)
    if noise_rms == 0:
        return clean_samples.copy(), 0.0
    target_noise_rms = clean_rms / (10 ** (snr_db / 20.0))
    noise_scale = target_noise_rms / noise_rms
    mixed_samples = clean_samples + noise_samples * noise_scale
    peak = float(np.max(np.abs(mixed_samples)))
    if peak > PEAK_LIMIT:
        mixed_samples = mixed_samples * (PEAK_LIMIT / peak)
    return mixed_samples.astype(np.float32), float(noise_scale)


def generate_stimuli(
    original_stimuli_dir: Path,
    schedule_path: Path,
    output_root: Path = PREGENERATED_ROOT,
    target_sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int = 20260319,
) -> Path:
    """Generate normalized clean/noise assets and per-trial mixed stimuli."""

    clean_output_dir = output_root / "phonemes"
    noise_output_dir = output_root / "noise"
    mixed_output_dir = output_root / "mixed"
    mixed_output_dir.mkdir(parents=True, exist_ok=True)

    decoded_noise_cache: dict[str, np.ndarray] = {}
    for noise_name, file_name in NOISE_FILE_MAP.items():
        decoded_noise = decode_audio_file(original_stimuli_dir / file_name)
        normalized_noise = normalize_rms(
            resample_if_needed(decoded_noise.samples, decoded_noise.sample_rate, target_sample_rate)
        )
        decoded_noise_cache[noise_name] = normalized_noise
        write_wav_file(noise_output_dir / f"{noise_name}.wav", normalized_noise, target_sample_rate)

    for phoneme_symbol, file_name in PHONEME_FILE_MAP.items():
        decoded_clean = decode_audio_file(original_stimuli_dir / file_name)
        normalized_clean = normalize_rms(
            resample_if_needed(decoded_clean.samples, decoded_clean.sample_rate, target_sample_rate)
        )
        safe_label = phoneme_safe_label(phoneme_symbol)
        write_wav_file(clean_output_dir / f"{safe_label}.wav", normalized_clean, target_sample_rate)

    trials = load_trials_from_workbook(schedule_path)
    manifest_rows: list[dict[str, object]] = []

    for trial in trials:
        clean_file_name = PHONEME_FILE_MAP[trial.phoneme]
        decoded_clean = decode_audio_file(original_stimuli_dir / clean_file_name)
        clean_samples = normalize_rms(
            resample_if_needed(decoded_clean.samples, decoded_clean.sample_rate, target_sample_rate)
        )

        rng = random.Random(seed + trial.trial_index)
        noise_pool = decoded_noise_cache[trial.session_type]
        noise_segment, noise_start_index = select_noise_segment(noise_pool, len(clean_samples), rng)
        mixed_samples, noise_scale = mix_at_snr(clean_samples, noise_segment, trial.snr)

        phoneme_label = phoneme_safe_label(trial.phoneme)
        mixed_file_name = (
            f"trial-{trial.trial_index:03d}"
            f"__track-{trial.track_id}"
            f"__phoneme-{phoneme_label}"
            f"__noise-{trial.session_type}"
            f"__snr-{int(trial.snr)}.wav"
        )
        mixed_path = mixed_output_dir / trial.session_type / f"snr_{int(trial.snr)}" / mixed_file_name
        write_wav_file(mixed_path, mixed_samples, target_sample_rate)

        manifest_rows.append(
            {
                "trial_index": trial.trial_index,
                "track_id": trial.track_id,
                "phoneme": trial.phoneme,
                "phoneme_label": phoneme_label,
                "session_type": trial.session_type,
                "snr": trial.snr,
                "onset_label": trial.onset_label,
                "stimulus_file": mixed_path.as_posix(),
                "clean_file": (clean_output_dir / f"{phoneme_label}.wav").as_posix(),
                "noise_file": (noise_output_dir / f"{trial.session_type}.wav").as_posix(),
                "sample_rate": target_sample_rate,
                "duration_seconds": len(clean_samples) / target_sample_rate,
                "noise_start_index": noise_start_index,
                "noise_scale": noise_scale,
                "clean_rms": rms(clean_samples),
                "mixed_rms": rms(mixed_samples),
            }
        )

    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.DictWriter(manifest_file, fieldnames=list(manifest_rows[0].keys()))
        writer.writeheader()
        writer.writerows(manifest_rows)

    return MANIFEST_PATH


def phoneme_safe_label(phoneme_symbol: str) -> str:
    """Convert IPA symbols into stable file labels."""

    return {
        "θ": "theta",
        "ð": "eth",
        "ʃ": "esh",
    }.get(phoneme_symbol, phoneme_symbol)


def main() -> None:
    """CLI entry point for offline stimulus generation."""

    original_stimuli_dir = PROJECT_ROOT / "original_stims"
    schedule_path = PROJECT_ROOT / "Speech_on_the_Brain_stimuli_tracking.xlsx"
    manifest_path = generate_stimuli(original_stimuli_dir=original_stimuli_dir, schedule_path=schedule_path)
    print(manifest_path.as_posix())


if __name__ == "__main__":
    main()
