"""Open a saved file or folder with the operating system's default application."""

import os
import subprocess
import sys
from pathlib import Path


def open_path(path: Path | str) -> bool:
    """Return whether the platform accepted the launch request.

    Saving a workbook succeeds independently of launching its desktop viewer.
    A missing launcher or unavailable graphical session therefore returns False.
    """
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True
