"""Portable launcher tests: never start a real desktop application."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import platform_open


class OpenPathTests(unittest.TestCase):
    def test_windows_uses_startfile(self):
        path = Path("Daily workbook.xlsx")
        with (
            patch.object(platform_open.sys, "platform", "win32"),
            patch.object(platform_open.os, "startfile", create=True) as startfile,
            patch.object(platform_open.subprocess, "run") as run,
        ):
            self.assertTrue(platform_open.open_path(path))
        startfile.assert_called_once_with(path)
        run.assert_not_called()

    def test_macos_and_linux_use_argument_lists(self):
        path = "reports/Report with spaces and $(literal).xlsx"
        for system, executable in (("darwin", "open"), ("linux", "xdg-open")):
            with (
                self.subTest(platform=system),
                patch.object(platform_open.sys, "platform", system),
                patch.object(platform_open.subprocess, "run") as run,
            ):
                self.assertTrue(platform_open.open_path(path))
                run.assert_called_once_with([executable, path], check=True)

    def test_windows_launch_error_returns_false(self):
        with (
            patch.object(platform_open.sys, "platform", "win32"),
            patch.object(
                platform_open.os, "startfile", create=True, side_effect=OSError
            ),
        ):
            self.assertFalse(platform_open.open_path(Path("saved.xlsx")))

    def test_missing_launcher_and_nonzero_exit_return_false(self):
        for system in ("darwin", "linux"):
            for error in (
                FileNotFoundError("Desktop launcher not found"),
                subprocess.CalledProcessError(1, "desktop-launcher"),
            ):
                with (
                    self.subTest(platform=system, error=type(error).__name__),
                    patch.object(platform_open.sys, "platform", system),
                    patch.object(platform_open.subprocess, "run", side_effect=error),
                ):
                    self.assertFalse(platform_open.open_path(Path("saved.xlsx")))


if __name__ == "__main__":
    unittest.main()
