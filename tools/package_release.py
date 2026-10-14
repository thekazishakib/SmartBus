"""Build a GitHub release ZIP containing project files, never working accounts."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from project_profile import APP_VERSION, load_profile  # noqa: E402 -- root added above

BLOCKED = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "data",
    "backups",
    "demo_workspace",
    "dist",
    ".pytest_cache",
    ".ruff_cache",
}


def included(path, root):
    relative = path.relative_to(root)
    if any(part in BLOCKED for part in relative.parts):
        return False
    if relative.parts[0] in {"daily", "reports"}:
        return path.name == ".gitkeep"
    return not (
        path.name.startswith((".env", "~$"))
        or path.suffix in {".pyc", ".pyo", ".sqlite3", ".db"}
        or path.name.endswith((".inspect.ndjson", ".sqlite3.damaged"))
        or path.name == "RELEASE_MANIFEST.json"
    )


def build(root=ROOT, destination=None):
    root = Path(root).resolve()
    destination = Path(destination or root / "dist").resolve()
    if destination == root:
        raise ValueError("Use a separate output folder, such as dist/.")
    profile = load_profile(root)
    name = profile["repository_name"]
    destination.mkdir(parents=True, exist_ok=True)
    files = [
        p
        for p in sorted(root.rglob("*"))
        if p.is_file() and included(p, root) and destination not in p.parents
    ]
    hashes = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in files
    }
    manifest = dict(
        project=profile["project_name"],
        version=APP_VERSION,
        language="English",
        files=hashes,
    )
    archive = destination / f"{name}_v{APP_VERSION}_GitHub_Ready.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, name + "/" + p.relative_to(root).as_posix())
        z.writestr(
            name + "/RELEASE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n"
        )
    with ZipFile(archive) as z:
        if z.testzip():
            raise ValueError("Archive integrity check failed.")
        for filename, checksum in hashes.items():
            if hashlib.sha256(z.read(name + "/" + filename)).hexdigest() != checksum:
                raise ValueError("Archive checksum check failed: " + filename)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".sha256").write_text(
        checksum + "  " + archive.name + "\n", encoding="ascii"
    )
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    print(build(destination=args.destination))
