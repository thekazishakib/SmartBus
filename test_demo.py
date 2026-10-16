"""Disposable demo generation must remain reproducible and preserve existing work."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from zipfile import ZipFile

from daily_system import ROOT, calculate, validate_book
from demo import DEMO_END, prepare_demo
from insights import build_insights
from ledger_store import LedgerStore
from report_layout import summary


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_call_keeps_original_day_totals_and_return_tuple(self):
        folder, printable, excel = prepare_demo(self.root / "default")
        self.assertEqual(folder, self.root / "default")
        self.assertTrue(printable.is_file())
        self.assertTrue(excel.is_file())
        self.assertTrue((folder / ".smartbus-demo").is_file())
        books = LedgerStore(folder).published_books("2026-10-12", "2026-10-12")
        _, totals = summary(books)
        self.assertEqual(len(books), 1)
        self.assertEqual(
            tuple(
                totals[key]
                for key in (
                    "seats",
                    "gross",
                    "commission",
                    "due",
                    "actual",
                    "outstanding",
                )
            ),
            (74, 70600, 2250, 68350, 49450, 18900),
        )

    def test_multiday_ledger_dates_departures_variation_and_reports_are_consistent(
        self,
    ):
        folder, printable, excel = prepare_demo(self.root / "multiple", days=3)
        books = LedgerStore(folder).published_books("2026-10-10", "2026-10-12")
        self.assertEqual(
            [book["day"] for book in books], ["2026-10-10", "2026-10-11", "2026-10-12"]
        )
        self.assertEqual(len(list((folder / "daily").glob("*.xlsx"))), 3)
        for book in books:
            self.assertTrue(
                all(
                    trip["start"].date().isoformat() == book["day"]
                    for trip in book["trips"]
                )
            )
            self.assertTrue(all(trip["seats"] <= 62 for trip in book["trips"]))
            self.assertTrue(all(line["actual"] is not None for line in book["lines"]))
            validate_book(calculate(Path(book["path"])))
        chart = build_insights(folder, "2026-10-10", "2026-10-12")
        self.assertEqual(len(chart["daily"]), 3)
        self.assertGreater(len({day["gross"] for day in chart["daily"]}), 1)
        self.assertEqual(chart["missing_days"], [])
        html = printable.read_text(encoding="utf-8")
        self.assertIn("10-10-2026", html)
        self.assertIn("12-10-2026", html)
        self.assertIn("2026-10-10_2026-10-12", excel.name)

    def test_multiday_financial_results_are_deterministic(self):
        first, _, _ = prepare_demo(self.root / "first", days=2)
        second, _, _ = prepare_demo(self.root / "second", days=2)
        a = build_insights(first, "2026-10-11", "2026-10-12")
        b = build_insights(second, "2026-10-11", "2026-10-12")
        self.assertEqual(a["daily"], b["daily"])
        self.assertEqual(a["totals"], b["totals"])

    def test_invalid_day_counts_create_no_workspace(self):
        for days in (0, -1, 32, True, 1.5, "2", None):
            with self.subTest(days=days):
                folder = self.root / "invalid"
                with self.assertRaisesRegex(ValueError, "1 to 31"):
                    prepare_demo(folder, days=days)
                self.assertFalse(folder.exists())

    def test_existing_later_workbook_is_preserved_before_any_first_day_write(self):
        folder = self.root / "existing"
        daily = folder / "daily"
        daily.mkdir(parents=True)
        saved = daily / f"Daily_{DEMO_END}_en.xlsx"
        saved.write_bytes(b"Existing user workbook")
        with self.assertRaisesRegex(ValueError, "preserve"):
            prepare_demo(folder, days=3)
        self.assertEqual(saved.read_bytes(), b"Existing user workbook")
        self.assertEqual(list(daily.iterdir()), [saved])
        self.assertFalse((folder / "data").exists())

    def test_existing_generated_areas_are_preserved(self):
        for area in ("data", "reports", "backups"):
            with self.subTest(area=area):
                folder = self.root / area
                target = folder / area / "existing.txt"
                target.parent.mkdir(parents=True)
                target.write_text("Keep this record", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "preserve"):
                    prepare_demo(folder, days=2)
                self.assertEqual(target.read_text(encoding="utf-8"), "Keep this record")
                self.assertFalse((folder / "daily").exists())

    def test_fixture_assets_and_styles_are_preserved(self):
        folder, _, _ = prepare_demo(self.root / "styles", days=2)
        first_day = DEMO_END - timedelta(days=1)
        target = folder / "daily" / f"Daily_{first_day}_en.xlsx"
        with (
            ZipFile(ROOT / "Demo_2026-10-12_en.xlsx") as original,
            ZipFile(target) as generated,
        ):
            self.assertEqual(
                original.read("xl/styles.xml"), generated.read("xl/styles.xml")
            )
            for name in original.namelist():
                if name.startswith(("xl/charts/", "xl/media/")):
                    self.assertEqual(original.read(name), generated.read(name))
        self.assertEqual(date.fromisoformat(calculate(target)["day"]), first_day)


if __name__ == "__main__":
    unittest.main()
