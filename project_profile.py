"""Editable project identity and report defaults; no financial rule overrides."""

import json
import os
import re
import tempfile
from pathlib import Path

APP_VERSION = "1.3.0"
DEFAULTS = {
    "project_name": "SmartBus",
    "tagline": "Daily trips, counter collections and revenue reconciliation",
    "author": "Kazi Shakib",
    "github_username": "thekazishakib",
    "repository_name": "SmartBus",
    "company_name": "SmartBus",
    "default_operator": "Local operator",
    "accent_color": "#22675f",
}


def load_profile(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    path = root / "project.json"
    profile = DEFAULTS.copy()
    if path.is_file():
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                "Could not read project.json. Use a valid JSON object."
            ) from error
        if not isinstance(values, dict):
            raise ValueError("project.json must contain a JSON object.")
        unknown = set(values) - set(DEFAULTS)
        if unknown:
            raise ValueError(
                "Unknown project.json settings: " + ", ".join(sorted(unknown))
            )
        profile.update(values)
    return validate_profile(profile)


def validate_profile(values):
    """Use the same branding rules for file loading and the local editor."""
    if not isinstance(values, dict):
        raise ValueError("project.json must contain a JSON object.")
    unknown = set(values) - set(DEFAULTS)
    if unknown:
        raise ValueError("Unknown project.json settings: " + ", ".join(sorted(unknown)))
    profile = DEFAULTS | values
    for name, value in profile.items():
        limit = {"company_name": 120, "default_operator": 80}.get(name, 160)
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > limit
            or any(ord(c) < 32 for c in value)
        ):
            raise ValueError(
                f"project.json {name} must contain 1–{limit} printable characters."
            )
        profile[name] = value.strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", profile["accent_color"]):
        raise ValueError(
            "project.json accent_color must be a six-digit hex color, such as #22675f."
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", profile["github_username"]):
        raise ValueError("project.json github_username must be a GitHub username.")
    if profile["repository_name"] in {".", ".."} or not re.fullmatch(
        r"[A-Za-z0-9_.-]+", profile["repository_name"]
    ):
        raise ValueError(
            "project.json repository_name must be a repository name, not a URL."
        )
    return profile


def save_profile(values, root=None):
    """Validate before atomically replacing branding; never accept money rules."""
    profile = validate_profile(values)
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    descriptor, temporary = tempfile.mkstemp(
        prefix=".project_", suffix=".json", dir=root
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(profile, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, root / "project.json")
    finally:
        Path(temporary).unlink(missing_ok=True)
    return profile
