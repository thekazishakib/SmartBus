"""Research schema, chronological holdout and provenance regression checks."""

import csv
import hashlib
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from ridership import analyze, checked_range, load_rows, summarize


class RidershipTests(unittest.TestCase):
    def rows(self):
        return [
            dict(
                date=str(date(2025, 10, 1) + timedelta(days=i)),
                route=route,
                daytype="W",
                rides=(20 if route == "1" else 10) + i,
            )
            for i in range(21)
            for route in ("1", "2")
        ]

    def test_holdout_does_not_train_on_future_rides(self):
        rows = self.rows()
        first = summarize(rows)
        changed = [
            dict(row, rides=row["rides"] + 10000)
            if row["date"] >= "2025-10-15"
            else row
            for row in rows
        ]
        second = summarize(changed)
        self.assertEqual(first["forecast"]["train_end"], "2025-10-14")
        self.assertEqual(first["forecast"]["test_start"], "2025-10-15")
        self.assertEqual(first["forecast"]["evaluated_rows"], 14)
        self.assertEqual(
            [row["predicted"] for row in first["forecast"]["predictions"]],
            [row["predicted"] for row in second["forecast"]["predictions"]],
        )
        self.assertEqual(
            [row["baseline"] for row in first["forecast"]["predictions"]],
            [row["baseline"] for row in second["forecast"]["predictions"]],
        )
        self.assertGreater(second["forecast"]["mae"], first["forecast"]["mae"])
        self.assertEqual(first, summarize(list(reversed(rows))))

    def test_new_routes_are_excluded_from_both_models(self):
        rows = self.rows() + [
            dict(date="2025-10-21", route="new", daytype="W", rides=900)
        ]
        result = summarize(rows)
        self.assertEqual(result["forecast"]["excluded_rows"], 1)
        self.assertEqual(result["forecast"]["evaluated_rows"], 14)
        self.assertEqual(result["totals"]["rides"], sum(row["rides"] for row in rows))

    def test_missing_days_not_filled_with_zero(self):
        result = summarize([row for row in self.rows() if row["date"] != "2025-10-04"])
        self.assertEqual(result["totals"]["observed_days"], 20)
        self.assertNotIn("2025-10-04", {row["day"] for row in result["daily"]})

    def test_schema_duplicates_and_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "cta_ridership.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=("date", "route", "daytype", "rides")
                )
                writer.writeheader()
                writer.writerows(self.rows())
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            (root / "source.json").write_text(json.dumps({"sha256": digest}))
            result = analyze(root)
            self.assertEqual(result["data_sha256"], digest)
            self.assertTrue((root / "forecast_predictions.csv").is_file())
            with path.open("a") as handle:
                handle.write("2025-10-01,1,W,20\n")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_rows(path)
            with self.assertRaisesRegex(ValueError, "checksum"):
                analyze(root)
            path.write_text("date,route,daytype,rides\n2025-10-01,1,W,-1\n")
            with self.assertRaisesRegex(ValueError, "non-negative integer"):
                load_rows(path)
            path.write_text(
                "date,route,route,daytype,rides\n2025-10-01,discarded,1,W,20\n"
            )
            with self.assertRaisesRegex(ValueError, "requires"):
                load_rows(path)

    def test_period_and_small_dataset_validation(self):
        for start, end in (
            ("2025-01-02", "2025-01-01"),
            ("2025-1-1", "2025-01-02"),
            ("2024-01-01", "2025-01-01"),
        ):
            with self.assertRaises(ValueError):
                checked_range(start, end)
        with self.assertRaisesRegex(ValueError, "14 observed dates"):
            summarize(self.rows()[:10])


if __name__ == "__main__":
    unittest.main()
