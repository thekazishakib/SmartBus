"""Financial control regressions using real packaged workbook input."""

import json
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import daily_system as daily
from ledger_store import LedgerStore, collect_closed, deserialize, serialize
from period_export import make_period_excel
from report_layout import summary
from test_counter import change


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "daily").mkdir()
        self.path = self.root / "daily/Daily_2026-10-12_en.xlsx"
        shutil.copy2(daily.ROOT / "Demo_2026-10-12_en.xlsx", self.path)
        change(self.path, {"Settings": {"B9": "LIVE"}, "Collections": {"M10": 0}})
        self.store = LedgerStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def close_fixture(self):
        self.store.import_workbook(self.path, "Test operator")
        self.store.review_day("2026-10-12", "Test reviewer")
        self.store.close_day("2026-10-12", "Test reviewer")
        return self.store.published_books("2026-10-12", "2026-10-12")[0]

    def test_exact_decimal_and_datetime_snapshot_roundtrip(self):
        book = daily.calculate(self.path)
        self.assertEqual(book, deserialize(serialize(book)))
        self.assertIsInstance(
            deserialize(serialize(book))["trips"][0]["gross"], Decimal
        )

    def test_import_freezes_ids_fares_routes_drivers_and_counter_kinds(self):
        before = daily.calculate(self.path)
        self.store.import_workbook(self.path)
        raw = daily.read_book(self.path)
        self.assertEqual(raw["Trips"]["A6"], "218")
        self.assertEqual(raw["Collections"]["H6"], 900)
        self.assertEqual(raw["Settings"]["B18"], "SMARTBUS_FROZEN_V1")
        change(
            self.path,
            {
                "Route List": {"G6": 950},
                "Buses": {"B6": "Other driver"},
                "Counters": {"B6": "Commission"},
            },
        )
        after = daily.calculate(self.path)
        self.assertEqual(before["trips"][0]["gross"], after["trips"][0]["gross"])
        self.assertEqual(before["trips"][0]["driver"], after["trips"][0]["driver"])
        self.assertEqual(before["lines"][0]["kind"], after["lines"][0]["kind"])
        self.assertTrue(list((self.root / "backups/workbooks").glob("*.xlsx")))

    def test_duplicate_import_is_idempotent(self):
        first = self.store.import_workbook(self.path)
        second = self.store.import_workbook(self.path)
        self.assertEqual(first["revision"], second["revision"])
        self.assertTrue(second["unchanged"])
        self.assertEqual([e["action"] for e in self.store.audit()].count("import"), 1)

    def test_close_requires_review(self):
        self.store.import_workbook(self.path)
        with self.assertRaisesRegex(ValueError, "Review"):
            self.store.close_day("2026-10-12")

    def test_blank_deposits_block_review_but_known_zero_is_allowed(self):
        change(self.path, {"Collections": {"M10": None}})
        self.store.import_workbook(self.path)
        with self.assertRaisesRegex(ValueError, "blank"):
            self.store.review_day("2026-10-12")
        change(self.path, {"Collections": {"M10": 0}})
        self.store.import_workbook(self.path)
        self.assertEqual(self.store.review_day("2026-10-12")["status"], "reviewed")

    def test_changed_source_invalidates_review_and_close(self):
        self.store.import_workbook(self.path)
        self.store.review_day("2026-10-12")
        change(self.path, {"Collections": {"M6": 2700}})
        with self.assertRaisesRegex(ValueError, "changed"):
            self.store.close_day("2026-10-12")
        imported = self.store.import_workbook(self.path)
        self.assertEqual(imported["status"], "draft")
        self.assertEqual(imported["revision"], 2)

    def test_closed_reports_survive_master_edit_and_source_deletion(self):
        original = self.close_fixture()
        change(self.path, {"Route List": {"G6": 999}, "Collections": {"M6": 9999}})
        books, missing, _ = collect_closed(
            self.root / "daily", "2026-10-12", "2026-10-13"
        )
        self.assertEqual(books[0]["trips"], original["trips"])
        self.assertEqual(missing, ["2026-10-13"])
        self.assertTrue(self.store.status()[0]["stale"])
        self.path.unlink()
        self.assertEqual(
            collect_closed(self.root / "daily", "2026-10-12", "2026-10-12")[0][0][
                "trips"
            ],
            original["trips"],
        )

    def test_closed_changes_require_reasoned_correction(self):
        self.close_fixture()
        change(self.path, {"Collections": {"M6": 2700}})
        with self.assertRaisesRegex(ValueError, "closed"):
            self.store.import_workbook(self.path)
        with self.assertRaisesRegex(ValueError, "reason"):
            self.store.begin_correction("2026-10-12", reason="")

    def test_correction_keeps_previous_publication_until_review_and_close(self):
        original = self.close_fixture()
        self.store.begin_correction(
            "2026-10-12", "Test operator", "Deposit transcription correction"
        )
        with self.assertRaisesRegex(ValueError, "Import"):
            self.store.review_day("2026-10-12")
        change(self.path, {"Collections": {"M6": 2700}})
        self.store.import_workbook(self.path)
        pending = self.store.published_books("2026-10-12", "2026-10-12")[0]
        self.assertEqual(pending["trips"], original["trips"])
        self.assertTrue(pending["ledger"]["correction_pending"])
        report = daily.report_html([pending], [], [], "2026-10-12", "2026-10-12", "en")
        self.assertIn("Corrections are pending", report)
        self.assertIn(original["trips"][0]["record_id"], report)
        self.store.review_day("2026-10-12")
        self.store.close_day("2026-10-12")
        corrected = self.store.published_books("2026-10-12", "2026-10-12")[0]
        self.assertEqual(corrected["ledger"]["revision"], 2)
        self.assertEqual(
            corrected["trips"][0]["record_id"], original["trips"][0]["record_id"]
        )
        self.assertEqual(
            corrected["trips"][0]["actual"], original["trips"][0]["actual"] + 100
        )
        self.assertEqual(
            corrected["trips"][0]["outstanding"],
            original["trips"][0]["outstanding"] - 100,
        )

    def test_bad_accounts_never_enter_ledger(self):
        change(self.path, {"Collections": {"G6": -5}})
        with self.assertRaises(ValueError):
            self.store.import_workbook(self.path)
        self.assertEqual(self.store.status(), [])

    def test_non_english_filename_cannot_enter_ledger(self):
        self.store.import_workbook(self.path)
        other = self.path.with_name("Daily_2026-10-12_bn.xlsx")
        shutil.copy2(self.path, other)
        with self.assertRaisesRegex(ValueError, "Daily_YYYY-MM-DD_en"):
            self.store.import_workbook(other)
        self.assertEqual(len(self.store.status()), 1)

    def test_backup_restore_balances_and_preserves_recovery_history(self):
        original = self.close_fixture()
        saved = self.store.backup()
        self.store.begin_correction("2026-10-12", reason="Receipt adjustment")
        change(self.path, {"Collections": {"M6": 2700}})
        self.store.import_workbook(self.path)
        self.store.review_day("2026-10-12")
        self.store.close_day("2026-10-12")
        self.store.restore_backup(saved.name, "Recovery operator")
        restored = self.store.published_books("2026-10-12", "2026-10-12")[0]
        self.assertEqual(restored["trips"], original["trips"])
        actions = [e["action"] for e in self.store.audit()]
        self.assertIn("restore", actions)
        self.assertIn("begin_correction", actions)
        self.assertEqual(self.store.status()[0]["status"], "closed")

    def test_damaged_backup_rejected_without_changing_current_ledger(self):
        original = self.close_fixture()
        bad = self.root / "backups/broken.sqlite3"
        bad.write_text("not a database")
        with self.assertRaisesRegex(ValueError, "damaged"):
            self.store.restore_backup(bad.name)
        self.assertEqual(
            self.store.published_books("2026-10-12", "2026-10-12")[0]["trips"],
            original["trips"],
        )
        with self.assertRaises(ValueError):
            self.store.restore_backup("../data/ledger.sqlite3")

    def test_snapshot_integrity_failure_is_explicit(self):
        self.close_fixture()
        with closing(sqlite3.connect(self.store.path)) as connection, connection:
            connection.execute("UPDATE revisions SET snapshot_json='{}'")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.store.published_books("2026-10-12", "2026-10-12")

    def test_audit_records_cannot_be_updated_or_deleted(self):
        self.store.import_workbook(self.path)
        with closing(sqlite3.connect(self.store.path)) as connection, connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM audit_events")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE audit_events SET actor='Other'")

    def test_final_excel_report_uses_closed_amounts(self):
        book = self.close_fixture()
        expected = summary([book])[1]
        change(self.path, {"Collections": {"M6": 9999}})
        output = make_period_excel(
            self.root / "daily",
            "2026-10-12",
            "2026-10-12",
            "en",
            report_folder=self.root / "reports",
        )
        raw = daily.read_book(output)
        self.assertEqual(raw["Dashboard"]["F8"], expected["gross"])
        self.assertEqual(raw["Dashboard"]["F14"], expected["actual"])
        self.assertEqual(raw["Trips"]["U6"], book["trips"][0]["record_id"])
        manifest = json.loads(
            output.with_suffix(".sources.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["sources"][0]["ledger"]["revision"], 1)
        self.assertEqual(
            manifest["sources"][0]["ledger"]["snapshot_sha256"],
            book["ledger"]["snapshot_sha256"],
        )

    def test_pdf_engine_failure_retains_printable_source_with_clear_error(self):
        self.close_fixture()
        with (
            patch("daily_system.edge_path", return_value="edge"),
            patch(
                "daily_system.subprocess.run",
                return_value=SimpleNamespace(returncode=1),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "printable HTML"):
                daily.make_report(
                    self.root / "daily",
                    "2026-10-12",
                    "2026-10-12",
                    "en",
                    report_folder=self.root / "reports",
                )
        self.assertEqual(len(list((self.root / "reports").glob("*.html"))), 1)
        self.assertEqual(list((self.root / "reports").glob("*.pdf")), [])

    def test_pdf_timeout_has_an_actionable_error(self):
        self.close_fixture()
        with (
            patch("daily_system.edge_path", return_value="edge"),
            patch(
                "daily_system.subprocess.run",
                side_effect=subprocess.TimeoutExpired("edge", 90),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "timed out"):
                daily.make_report(
                    self.root / "daily",
                    "2026-10-12",
                    "2026-10-12",
                    "en",
                    report_folder=self.root / "reports",
                )

    def test_printable_report_uses_closed_amounts_without_edge(self):
        book = self.close_fixture()
        change(self.path, {"Collections": {"M6": 99999}})
        with patch(
            "daily_system.edge_path",
            side_effect=AssertionError("No Edge should be launched"),
        ):
            path = daily.make_printable_report(
                self.root / "daily",
                "2026-10-12",
                "2026-10-12",
                report_folder=self.root / "reports",
                company="Example Transport",
            )
        html = path.read_text(encoding="utf-8")
        self.assertIn("Example Transport", html)
        self.assertIn("49,450.00", html)
        self.assertNotIn("99,999", html)
        self.assertIn("Print / Save as PDF", html)
        self.assertIn("window.print()", html)
        self.assertIn("@media print{.print-toolbar{display:none!important}", html)
        self.assertIn(book["trips"][0]["record_id"], html)
        self.assertTrue(path.with_name(path.stem + "_sources.json").exists())

    def test_printable_report_rejects_unclosed_days(self):
        with self.assertRaisesRegex(ValueError, "closed"):
            daily.make_printable_report(
                self.root / "daily",
                "2026-10-12",
                "2026-10-12",
                report_folder=self.root / "reports",
            )

    def test_report_company_text_cannot_inject_html(self):
        book = self.close_fixture()
        html = daily.report_html(
            [book],
            [],
            [],
            "2026-10-12",
            "2026-10-12",
            company="<script>alert(1)</script>",
        )
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_final_report_blocks_unclosed_file(self):
        with self.assertRaisesRegex(ValueError, "closed"):
            collect_closed(self.root / "daily", "2026-10-12", "2026-10-12")

    def test_known_draft_is_not_treated_as_missing_when_source_is_deleted(self):
        self.store.import_workbook(self.path)
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "closed"):
            collect_closed(self.root / "daily", "2026-10-12", "2026-10-12")

    def test_verified_backup_can_recover_a_damaged_current_database(self):
        original = self.close_fixture()
        saved = self.store.backup()
        self.store.path.write_bytes(b"damaged database")
        recovery = LedgerStore(self.root)
        self.assertIsNotNone(recovery.recovery_error)
        self.assertEqual(recovery.status()[0]["status"], "recovery_required")
        result = self.store.restore_backup(saved.name)
        self.assertTrue(result["safety_backup"].endswith(".damaged"))
        self.assertEqual(
            self.store.published_books("2026-10-12", "2026-10-12")[0]["trips"],
            original["trips"],
        )

    def test_open_excel_workbook_is_not_modified(self):
        self.path.with_name("~$" + self.path.name).touch()
        with self.assertRaisesRegex(ValueError, "Excel"):
            self.store.import_workbook(self.path)
        self.assertEqual(self.store.status(), [])

    def test_no_trip_day_can_be_explicitly_closed(self):
        self.path.unlink()
        path = daily.create_daily("2026-10-12", "en", self.root / "daily")
        self.store.import_workbook(path)
        self.store.review_day("2026-10-12")
        self.store.close_day("2026-10-12")
        books, missing, _ = collect_closed(
            self.root / "daily", "2026-10-12", "2026-10-12"
        )
        self.assertEqual(books[0]["trips"], [])
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
