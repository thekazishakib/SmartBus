import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools.package_release import build
from tools.update_readme import generate


class ReleaseToolsTests(unittest.TestCase):
    def test_archive_excludes_accounts_backups_caches_and_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in (
                "README.md",
                "LICENSE",
                "app.py",
                "daily/.gitkeep",
                "reports/.gitkeep",
                "daily/real.xlsx",
                "reports/private.html",
                "portfolio_demo/daily/nested_private.xlsx",
                "portfolio_demo/reports/nested_private.json",
                "analysis/private_export.csv",
                "research/public.csv",
                "data/ledger.sqlite3",
                "backups/private.xlsx",
                ".env.local",
                "__pycache__/private.pyc",
                ".ruff_cache/private.cache",
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("example")
            output = build(root)
            with ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("SmartBus/LICENSE", names)
                self.assertIn("SmartBus/daily/.gitkeep", names)
                self.assertIn("SmartBus/RELEASE_MANIFEST.json", names)
                self.assertIn("SmartBus/research/public.csv", names)
                for suffix in (
                    "real.xlsx",
                    "private.html",
                    "ledger.sqlite3",
                    "private.xlsx",
                    ".env.local",
                    "private.pyc",
                    "private.cache",
                    "nested_private.xlsx",
                    "nested_private.json",
                    "private_export.csv",
                ):
                    self.assertFalse(any(name.endswith(suffix) for name in names))
            self.assertTrue(output.with_suffix(".sha256").exists())

    def test_readme_regeneration_uses_editable_template_and_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "project.json").write_text(
                '{"author":"Example Author","project_name":"Example Bus"}'
            )
            (root / "docs/README.template.md").write_text(
                "# {{PROJECT_NAME}}\nBy {{AUTHOR}}\n{{PROFILE_JSON}}"
            )
            output = generate(root)
            content = output.read_text()
            self.assertIn("# Example Bus", content)
            self.assertIn("By Example Author", content)
            self.assertNotIn("{{", content)


if __name__ == "__main__":
    unittest.main()
