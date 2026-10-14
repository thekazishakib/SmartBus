"""Regenerate README branding from project.json and the editable template."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from project_profile import APP_VERSION, load_profile  # noqa: E402 -- root added above


def generate(root=ROOT):
    root = Path(root)
    profile = load_profile(root)
    content = (root / "docs/README.template.md").read_text(encoding="utf-8")
    values = {key.upper(): value for key, value in profile.items()}
    values["VERSION"] = APP_VERSION
    content = content.replace(
        "{{PROFILE_JSON}}", json.dumps(profile, indent=2, ensure_ascii=False)
    )
    # Metadata is plain text in Markdown; HTML attributes must remain escaped.
    import html

    for key, value in values.items():
        content = content.replace("{{" + key + "}}", html.escape(value, quote=True))
    unresolved = re.findall(r"\{\{[A-Z_]+\}\}", content)
    if unresolved:
        raise ValueError(
            "Unknown README template fields: " + ", ".join(sorted(set(unresolved)))
        )
    (root / "README.md").write_text(content, encoding="utf-8")
    return root / "README.md"


if __name__ == "__main__":
    print(generate())
