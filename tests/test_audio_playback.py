from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from phoneme_psychopy.audio_playback import play_audio_file


class AudioPlaybackTests(unittest.TestCase):
    @patch("phoneme_psychopy.audio_playback._load_audio_modules")
    def test_play_audio_file_reads_samples_and_waits_for_completion(self, mock_load_audio_modules) -> None:
        audio_samples = np.zeros((22050, 1), dtype=np.float32)
        mock_sd = MagicMock()
        mock_sf = MagicMock()
        mock_sf.read.return_value = (audio_samples, 44100)
        mock_load_audio_modules.return_value = (mock_sd, mock_sf)
        audio_path = Path("/tmp/stimulus.wav")

        play_audio_file(audio_path)

        mock_sf.read.assert_called_once_with(audio_path, always_2d=True, dtype="float32")
        mock_sd.play.assert_called_once()
        play_args, play_kwargs = mock_sd.play.call_args
        self.assertEqual(play_kwargs, {})
        self.assertTrue(np.array_equal(play_args[0], audio_samples))
        self.assertEqual(play_args[1], 44100)
        mock_sd.wait.assert_called_once_with()

    @patch("phoneme_psychopy.audio_playback._load_audio_modules")
    def test_play_audio_file_raises_clear_error_when_output_backend_fails(self, mock_load_audio_modules) -> None:
        mock_sd = MagicMock()
        mock_sf = MagicMock()
        mock_sf.read.return_value = (np.zeros((8, 1), dtype=np.float32), 44100)
        mock_sd.play.side_effect = RuntimeError("device unavailable")
        mock_load_audio_modules.return_value = (mock_sd, mock_sf)

        with self.assertRaisesRegex(RuntimeError, "Stimulus playback requires a working PortAudio output device"):
            play_audio_file(Path("/tmp/stimulus.wav"))

        mock_sd.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
