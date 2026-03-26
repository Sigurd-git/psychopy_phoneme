from __future__ import annotations

import math
import unittest

import numpy as np

from phoneme_psychopy.audio_preprocess import mix_at_snr, rms


class AudioPreprocessTests(unittest.TestCase):
    def test_mix_at_snr_scales_clean_relative_to_fixed_noise(self) -> None:
        clean_samples = np.array([0.01, -0.01] * 256, dtype=np.float32)
        noise_samples = np.array([0.02, -0.02] * 256, dtype=np.float32)

        mixed_samples, clean_scale = mix_at_snr(clean_samples, noise_samples, snr_db=6.0)

        expected_clean_scale = rms(noise_samples) * (10 ** (6.0 / 20.0)) / rms(clean_samples)
        self.assertAlmostEqual(clean_scale, expected_clean_scale, places=6)
        self.assertEqual(mixed_samples.dtype, np.float32)

        scaled_clean_rms = rms(clean_samples * clean_scale)
        realized_snr = 20.0 * math.log10(scaled_clean_rms / rms(noise_samples))
        self.assertAlmostEqual(realized_snr, 6.0, places=5)


if __name__ == "__main__":
    unittest.main()
