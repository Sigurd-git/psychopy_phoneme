from __future__ import annotations

import unittest
from unittest import mock

from phoneme_psychopy.ui import build_config_from_cli, parse_cli_args


class UiTests(unittest.TestCase):
    def test_parse_cli_args_enables_practice_by_default(self) -> None:
        with mock.patch("sys.argv", ["phoneme-psychopy"]):
            args = parse_cli_args()

        self.assertTrue(args.practice)

    def test_parse_cli_args_can_disable_practice_explicitly(self) -> None:
        with mock.patch("sys.argv", ["phoneme-psychopy", "--no-practice"]):
            args = parse_cli_args()

        self.assertFalse(args.practice)

    def test_build_config_from_cli_keeps_practice_enabled_by_default(self) -> None:
        with mock.patch("sys.argv", ["phoneme-psychopy"]):
            args = parse_cli_args()

        config = build_config_from_cli(args)

        self.assertTrue(config.practice_enabled)

    def test_parse_cli_args_accepts_subfolder(self) -> None:
        with mock.patch(
            "sys.argv",
            ["phoneme-psychopy", "--subfolder", "sub-Sasha/run-20260329_113244"],
        ):
            args = parse_cli_args()

        self.assertEqual(args.subfolder, "sub-Sasha/run-20260329_113244")


if __name__ == "__main__":
    unittest.main()
