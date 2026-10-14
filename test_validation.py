"""Regression tests for workbook data loss and incomplete report prevention."""

import shutil
import tempfile
import unittest
from pathlib import Path

import daily_system as daily
from test_counter import change


class WorkbookValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.path = self.folder / "Daily_2026-10-12_en.xlsx"
        self.reset_book()

    def tearDown(self):
        self.temporary.cleanup()

    def reset_book(self):
        shutil.copy2(daily.ROOT / "Demo_2026-10-12_en.xlsx", self.path)
        change(self.path, {"Settings": {"B9": "LIVE"}})

    def collect(self, start="2026-10-12", end="2026-10-12"):
        return daily.collect(self.folder, start, end)

    def test_unsupported_workbook_marker_has_actionable_error(self):
        change(self.path, {"Settings": {"B12": "OTHER_FORMAT"}})
        with self.assertRaisesRegex(
            ValueError,
            r"Settings!B12: workbook format marker does not match; expected AUTO_V6",
        ):
            daily.calculate(self.path)

    def test_trip_overflow_is_not_silently_omitted(self):
        values = {
            "A106": 500,
            "B106": 701,
            "C106": "2026-10-12T12:00:00",
            "D106": "Dhaka - Chattogram",
            "E106": "Going",
            "F106": "Demo Bus 1",
            "G106": "Demo Driver 1",
            "I106": "Demo Guide 1",
            "K106": "Demo Conductor 1",
            "N106": 1,
        }
        change(self.path, {"Trips": values})
        with self.assertRaises(ValueError) as caught:
            daily.calculate(self.path)
        for reference in values:
            self.assertIn(f"Trips!{reference}", str(caught.exception))
        self.assertIn("6–105", str(caught.exception))

    def test_collection_overflow_is_not_silently_omitted(self):
        change(
            self.path,
            {
                "Collections": {
                    "D506": 218,
                    "E506": "Gabtoli AC",
                    "G506": 1,
                    "M506": 900,
                }
            },
        )
        with self.assertRaisesRegex(ValueError, "Collections!D506"):
            self.collect()

    def test_master_overflow_is_rejected(self):
        updates = {
            "Buses": {"A106": "New bus"},
            "Crew": {"A106": "New person"},
            "Counters": {"A106": "New counter"},
            "Route List": {"A306": 9999, "F206": "New route"},
        }
        change(self.path, updates)
        with self.assertRaises(ValueError) as caught:
            daily.calculate(self.path)
        for sheet, cells in updates.items():
            for reference in cells:
                self.assertIn(f"{sheet}!{reference}", str(caught.exception))

    def test_duplicate_master_keys_are_rejected(self):
        raw = daily.read_book(self.path)
        for sheet, reference in [
            ("Buses", "A6"),
            ("Crew", "A6"),
            ("Counters", "A6"),
            ("Route List", "A6"),
            ("Route List", "F6"),
        ]:
            with self.subTest(sheet=sheet, reference=reference):
                self.reset_book()
                target = reference[0] + ("205" if reference[0] == "F" else "105")
                change(self.path, {sheet: {target: raw[sheet][reference]}})
                with self.assertRaisesRegex(ValueError, "duplicate master key"):
                    daily.calculate(self.path)

    def test_populated_master_row_without_key_is_rejected(self):
        change(
            self.path, {"Buses": {"B20": "Demo Driver 1"}, "Route List": {"G20": 500}}
        )
        with self.assertRaises(ValueError) as caught:
            daily.calculate(self.path)
        self.assertIn("Buses!A20", str(caught.exception))
        self.assertIn("Route List!F20", str(caught.exception))

    def test_partial_trip_without_coach_is_rejected(self):
        change(self.path, {"Trips": {"C20": "2026-10-12T12:00:00"}})
        with self.assertRaisesRegex(ValueError, "Trips!B20"):
            self.collect()

    def test_partial_collection_is_retained_and_report_rejected(self):
        change(self.path, {"Collections": {"D20": 218}})
        book = daily.calculate(self.path)
        self.assertEqual(len(book["lines"]), 7)
        with self.assertRaisesRegex(ValueError, "Invalid seats sold"):
            self.collect()

    def test_collection_without_trip_cannot_disappear(self):
        change(self.path, {"Collections": {"E20": "Gabtoli AC", "G20": 1}})
        book = daily.calculate(self.path)
        self.assertEqual(len(book["orphan"]), 1)
        with self.assertRaisesRegex(ValueError, "missing or duplicate trip"):
            daily.validate_book(book)

    def test_invalid_rows_block_reports_but_remain_inspectable(self):
        change(self.path, {"Collections": {"G7": 80}})
        book = daily.calculate(self.path)
        self.assertIn("Sold seats exceed bus capacity", book["trips"][0]["issues"])
        with self.assertRaisesRegex(ValueError, "Sold seats exceed bus capacity"):
            self.collect()

    def test_missing_fare_blocks_report(self):
        change(self.path, {"Route List": {"G6": None}})
        with self.assertRaisesRegex(ValueError, "Invalid ticket fare"):
            self.collect()

    def test_duplicate_trip_number_blocks_report(self):
        change(self.path, {"Trips": {"A7": 218}})
        with self.assertRaisesRegex(ValueError, "Duplicate trip number"):
            self.collect()

    def test_pending_and_short_or_extra_deposits_are_valid(self):
        change(self.path, {"Collections": {"M6": 3100}})
        books, missing, excluded = self.collect()
        self.assertEqual((missing, excluded), ([], []))
        self.assertTrue(
            any(trip["status"] == "Deposit pending" for trip in books[0]["trips"])
        )
        self.assertTrue(
            any(trip["status"] == "Short / extra" for trip in books[0]["trips"])
        )

    def test_corrupt_workbook_outside_range_is_ignored(self):
        (self.folder / "Daily_2026-01-01_en.xlsx").write_bytes(b"broken spreadsheet")
        books, missing, _ = self.collect()
        self.assertEqual([book["day"] for book in books], ["2026-10-12"])
        self.assertEqual(missing, [])

    def test_all_in_range_corrupt_files_are_named(self):
        bad_names = ["Daily_2026-10-11_en.xlsx", "Daily_2026-10-13_en.xlsx"]
        for name in bad_names:
            (self.folder / name).write_bytes(b"broken spreadsheet")
        with self.assertRaises(ValueError) as caught:
            self.collect("2026-10-11", "2026-10-13")
        for name in bad_names:
            self.assertIn(name, str(caught.exception))
        self.assertIn("Report cancelled", str(caught.exception))

    def test_filename_and_saved_date_must_match(self):
        change(self.path, {"Settings": {"B6": "2026-10-13T00:00:00"}})
        with self.assertRaisesRegex(ValueError, "File date and filename differ"):
            self.collect()

    def test_non_english_workbook_filename_in_range_is_rejected(self):
        shutil.copy2(self.path, self.folder / "Daily_2026-10-12_bn.xlsx")
        with self.assertRaisesRegex(ValueError, "English"):
            self.collect()

    def test_non_english_workbook_outside_range_is_ignored(self):
        (self.folder / "Daily_2026-01-01_bn.xlsx").write_bytes(b"unsupported workbook")
        books, missing, _ = self.collect()
        self.assertEqual([book["day"] for book in books], ["2026-10-12"])
        self.assertEqual(missing, [])

    def test_non_english_saved_language_is_rejected(self):
        change(self.path, {"Settings": {"B11": "bn"}})
        with self.assertRaisesRegex(ValueError, "Settings!B11"):
            daily.calculate(self.path)

    def test_missing_dates_and_excluded_demo_are_preserved(self):
        demo = daily.create_daily("2026-10-13", "en", self.folder)
        change(demo, {"Settings": {"B9": "DEMO"}})
        books, missing, excluded = self.collect("2026-10-11", "2026-10-13")
        self.assertEqual([book["day"] for book in books], ["2026-10-12"])
        self.assertEqual(missing, ["2026-10-11", "2026-10-13"])
        self.assertEqual(excluded, [demo.name])

    def test_starting_trip_number_must_be_a_bounded_positive_integer(self):
        for value in ("not a number", 1.5, 0, -1, "NaN", "1000000000000000"):
            with self.subTest(value=value):
                change(self.path, {"Settings": {"B17": value}})
                with self.assertRaisesRegex(ValueError, "Settings!B17"):
                    daily.calculate(self.path)

    def test_manual_trip_number_must_be_an_integer(self):
        change(self.path, {"Trips": {"A6": 218.5}})
        with self.assertRaisesRegex(ValueError, "Trips!A6"):
            daily.calculate(self.path)

    def test_malformed_tolerance_and_date_have_clear_errors(self):
        for reference, value in [("B7", "NaN"), ("B7", -1), ("B6", "tomorrow")]:
            with self.subTest(reference=reference, value=value):
                self.reset_book()
                change(self.path, {"Settings": {reference: value}})
                with self.assertRaisesRegex(ValueError, f"Settings!{reference}"):
                    daily.calculate(self.path)

    def test_unsupported_manual_formula_override_is_rejected(self):
        change(self.path, {"Collections": {"H6": 1}, "Trips": {"M6": 500}})
        with self.assertRaises(ValueError) as caught:
            daily.calculate(self.path)
        self.assertIn("Collections!H6", str(caught.exception))
        self.assertIn("Trips!M6", str(caught.exception))

    def test_frozen_transaction_fare_and_type_survive_master_edits(self):
        change(
            self.path,
            {
                "Settings": {"B18": "SMARTBUS_FROZEN_V1"},
                "Trips": {"A6": 218, "D6": "Dhaka - Chattogram", "G6": "Demo Driver 1"},
                "Collections": {"H6": 900, "F6": "Own"},
                "Route List": {"G6": 950},
                "Counters": {"B6": "Commission"},
            },
        )
        book = daily.calculate(self.path)
        frozen_line = next(
            line
            for line in book["lines"]
            if line["trip"] == "218" and line["counter"] == "Gabtoli AC"
        )
        self.assertEqual((frozen_line["gross"], frozen_line["commission"]), (2700, 0))
        # Newly entered lines retain formulas and continue using the current fare.
        new_line = next(
            line
            for line in book["lines"]
            if line["trip"] == "218" and line["counter"] != "Gabtoli AC"
        )
        self.assertEqual(new_line["fare"], 950)


if __name__ == "__main__":
    unittest.main()
