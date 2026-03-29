# PsychoPy Phoneme Experiment

Minimal, research-oriented scaffold for a PsychoPy experiment on phoneme perception under different background noise conditions.

## Current scaffold features

- Offline stimulus generation from `original_stimuli/`
- Random noise cropping matched to each phoneme duration
- RMS normalization and per-trial SNR mixing
- Stimulus manifest generation for traceability
- Stimulus schedule parsing from `Speech_on_the_Brain_stimuli_tracking.xlsx`
- Session builder for `babble`, `white`, or `both`
- Trial metadata logging to CSV, including block indices and trial event timestamps
- PsychoPy entry point with playable pre-generated stimuli and a recording backend hook
- Dry-run validation mode that runs headlessly while still saving real microphone recordings, practice trials, and finalized/aborted trial logs

## Planned next steps

- Add validated stimulus path mapping for IPA audio files
- Add microphone recording workflow
- Add noise playback / mixing strategy
- Add instruction screens and break screens
- Add practice trials and counterbalancing

## Run

Generate normalized mixed stimuli first:

```bash
uv run phoneme-preprocess
```

Validate the non-GUI scaffold while still writing real microphone recordings:

```bash
uv run python -m phoneme_psychopy.main --dry-run --session-type both --max-trials 5
```

Validate early-stop logging:

```bash
uv run python -m phoneme_psychopy.main --dry-run --session-type white --max-trials 5 --abort-after-trials 2
```

Run the PsychoPy interface after installing the optional dependency set:

```bash
uv sync --extra psychopy
uv run phoneme-psychopy --prompt-config
```

The participant response screen hides the target phoneme by default. Use `--show-phoneme-label` only for debugging or operator checks.

The PsychoPy dependency set is currently locked for Python 3.11-3.13 on 64-bit desktop platforms.

`--prompt-config` now uses terminal prompts instead of a Tk window, which avoids X11/xcb crashes on some Linux setups.

For microphone capture, the target machine needs a working PortAudio installation and an available system input device.
