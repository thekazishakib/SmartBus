"""Closed-snapshot analytics and isolated scenario calculation regressions."""

import copy
import json
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import daily_system as daily
from insights import build_insights, plan_scenario
from ledger_store import LedgerStore, digest
from test_counter import change


class InsightsTests(unittest.TestCase):
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
        self.store.import_workbook(self.path)
        self.store.review_day("2026-10-12")
        self.store.close_day("2026-10-12")

    def insights(self, start="2026-10-12", end="2026-10-12", route=None):
        return build_insights(self.root, start, end, route)

    def test_closed_values_are_json_safe_and_do_not_change_sources(self):
        self.close_fixture()
        before = (digest(self.path), digest(self.store.path), self.store.audit())
        result = self.insights()
        self.assertEqual(result["scope"], "closed revisions")
        self.assertEqual(result["days"], 1)
        totals = result["totals"]
        self.assertEqual(
            [
                totals[field]
                for field in (
                    "gross",
                    "commission",
                    "due",
                    "actual",
                    "outstanding",
                    "extra",
                )
            ],
            ["70600.00", "2250.00", "68350.00", "49450.00", "18900.00", "0.00"],
        )
        self.assertEqual(totals["capacity"], totals["trips"] * 62)
        self.assertEqual(result["daily"][0]["date"], "2026-10-12")
        self.assertEqual(result["daily"][0]["gross"], totals["gross"])
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)
        self.assertEqual(
            (digest(self.path), digest(self.store.path), self.store.audit()), before
        )

    def test_edited_and_deleted_workbooks_do_not_change_closed_insights(self):
        self.close_fixture()
        before = self.insights()
        change(self.path, {"Collections": {"M6": 999999}})
        self.assertEqual(self.insights(), before)
        self.path.unlink()
        self.assertEqual(self.insights(), before)

    def test_pending_correction_keeps_published_amounts_until_close(self):
        self.close_fixture()
        original = self.insights()
        self.store.begin_correction(
            "2026-10-12", reason="Correct deposit transcription"
        )
        change(self.path, {"Collections": {"M6": 2700}})
        self.store.import_workbook(self.path)
        pending = self.insights()
        self.assertEqual(pending["totals"], original["totals"])
        self.assertEqual(pending["daily"][0]["revision"], 1)
        self.assertTrue(pending["daily"][0]["correction_pending"])
        self.assertIn("correction_pending", {a["code"] for a in pending["alerts"]})
        self.store.review_day("2026-10-12")
        self.store.close_day("2026-10-12")
        updated = self.insights()
        self.assertEqual(updated["totals"]["actual"], "49550.00")
        self.assertEqual(updated["daily"][0]["revision"], 2)
        self.assertFalse(updated["daily"][0]["correction_pending"])

    def test_shortages_and_extra_receipts_never_offset(self):
        change(self.path, {"Collections": {"M6": 3100}})
        self.close_fixture()
        result = self.insights()
        totals = result["totals"]
        self.assertEqual(totals["outstanding"], "18800.00")
        self.assertEqual(totals["extra"], "400.00")
        self.assertGreater(
            Decimal(totals["outstanding"]),
            Decimal(totals["due"]) - Decimal(totals["actual"]),
        )
        for field in ("gross", "commission", "due", "actual", "outstanding", "extra"):
            self.assertEqual(
                sum(Decimal(counter[field]) for counter in result["counters"]),
                Decimal(totals[field]),
            )
        codes = {alert["code"] for alert in result["alerts"]}
        self.assertTrue({"outstanding", "extra"}.issubset(codes))

    def test_route_filter_selects_only_matching_trip_counter_groups(self):
        self.close_fixture()
        all_routes = self.insights()
        route = all_routes["available_routes"][0]
        selected = self.insights(route=route)
        self.assertEqual([row["route"] for row in selected["routes"]], [route])
        ranked = next(row for row in all_routes["routes"] if row["route"] == route)
        for field, value in selected["totals"].items():
            self.assertEqual(ranked[field], value)
        self.assertEqual(selected["available_routes"], all_routes["available_routes"])
        self.assertEqual(
            sum(Decimal(row["due"]) for row in selected["counters"]),
            Decimal(selected["totals"]["due"]),
        )
        for invalid in (route.lower(), route + " ", "Unknown route"):
            with self.subTest(route=invalid), self.assertRaises(ValueError):
                self.insights(route=invalid)

    def test_drafts_and_missing_days_are_not_zero_activity_days(self):
        self.store.import_workbook(self.path)
        draft = self.insights(end="2026-10-13")
        self.assertEqual(draft["days"], 0)
        self.assertEqual(draft["daily"], [])
        self.assertEqual(draft["missing_days"], ["2026-10-12", "2026-10-13"])
        self.store.review_day("2026-10-12")
        self.store.close_day("2026-10-12")
        result = self.insights(end="2026-10-13")
        self.assertEqual(result["days"], 1)
        self.assertEqual(len(result["daily"]), 1)
        self.assertEqual(result["missing_days"], ["2026-10-13"])

    def test_explicit_closed_empty_day_is_present(self):
        path = daily.create_daily("2026-10-13", "en", self.root / "daily")
        self.store.import_workbook(path)
        self.store.review_day("2026-10-13")
        self.store.close_day("2026-10-13")
        result = self.insights(start="2026-10-13", end="2026-10-13")
        self.assertEqual(result["days"], 1)
        self.assertEqual(result["missing_days"], [])
        self.assertEqual(result["daily"][0]["trips"], 0)
        self.assertEqual(result["totals"]["gross"], "0.00")

    def test_absent_ledger_returns_empty_without_creating_files(self):
        root = self.root / "unused-root"
        result = build_insights(root, "2026-10-12", "2026-10-12")
        self.assertFalse(root.exists())
        self.assertEqual(result["days"], 0)
        self.assertEqual(result["totals"]["gross"], "0.00")
        self.assertEqual(result["available_routes"], [])
        self.assertEqual(result["missing_days"], ["2026-10-12"])

    def test_date_range_and_route_validation(self):
        for start, end in (
            ("2026-10-13", "2026-10-12"),
            ("2026-02-30", "2026-03-01"),
            ("20261012", "2026-10-12"),
            ("2026-10-12T00:00:00", "2026-10-12"),
            ("2024-01-01", "2025-01-01"),
            (None, "2026-10-12"),
        ):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.insights(start, end)
        accepted = self.insights("2024-01-01", "2024-12-31")
        self.assertEqual(len(accepted["missing_days"]), 366)
        for route in ("x" * 161, " ", "A\nB", 4, ["A"]):
            with self.subTest(route=route), self.assertRaises(ValueError):
                self.insights(route=route)
        self.assertEqual(self.insights(route=""), self.insights())

    def test_weighted_occupancy_and_route_rankings(self):
        self.close_fixture()
        book = self.store.published_books("2026-10-12", "2026-10-12")[0]
        # Different capacities prove the calculation divides total sold seats by
        # total capacity rather than averaging trip occupancy percentages.
        for trip, seats, capacity in zip(book["trips"], (5, 45, 0), (10, 90, 62)):
            trip["seats"], trip["capacity"] = Decimal(seats), Decimal(capacity)
        expected = copy.deepcopy(book)
        with patch("insights.LedgerStore.published_books", return_value=[book]):
            result = self.insights()
        self.assertEqual(book, expected)
        self.assertEqual(result["totals"]["occupancy_pct"], "30.86")
        self.assertEqual(
            [Decimal(row["gross"]) for row in result["routes"]],
            sorted((Decimal(row["gross"]) for row in result["routes"]), reverse=True),
        )
        self.assertEqual(
            [row["rank"] for row in result["routes"]],
            list(range(1, len(result["routes"]) + 1)),
        )

    def test_same_counter_shortage_and_extra_on_different_trips_remain_separate(self):
        self.close_fixture()
        book = self.store.published_books("2026-10-12", "2026-10-12")[0]
        book["trips"] = book["trips"][:2]
        book["counter_groups"] = []
        for trip, actual in zip(book["trips"], ("80.00", "120.00")):
            amounts = dict(
                seats=Decimal(1),
                gross=Decimal(100),
                commission=Decimal(0),
                due=Decimal(100),
                actual=Decimal(actual),
                outstanding=max(Decimal(100) - Decimal(actual), Decimal(0)),
                extra_received=max(Decimal(actual) - Decimal(100), Decimal(0)),
            )
            trip.update(amounts)
            book["counter_groups"].append(
                dict(
                    trip=trip["trip"],
                    counter="Example Own Counter",
                    kind="Own",
                    **amounts,
                )
            )
        with patch("insights.LedgerStore.published_books", return_value=[book]):
            result = self.insights()
        self.assertEqual(result["totals"]["due"], result["totals"]["actual"])
        self.assertEqual(result["totals"]["outstanding"], "20.00")
        self.assertEqual(result["totals"]["extra"], "20.00")
        self.assertEqual(result["counters"][0]["outstanding"], "20.00")
        self.assertEqual(result["counters"][0]["extra"], "20.00")
        self.assertEqual(result["counters"][0]["trips"], 2)


class ScenarioTests(unittest.TestCase):
    def test_own_counter_scenario_is_exact_and_json_safe(self):
        result = plan_scenario("31", "900.25", "Own")
        self.assertEqual(result["capacity"], 62)
        self.assertEqual(result["occupancy_pct"], "50.00")
        self.assertEqual(result["gross"], "27907.75")
        self.assertEqual(result["commission"], "0.00")
        self.assertEqual(result["due"], result["gross"])
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)

    def test_commission_counter_uses_fixed_per_ticket_rule(self):
        result = plan_scenario(62, "900", "Commission")
        self.assertEqual(result["gross"], "55800.00")
        self.assertEqual(result["commission_per_ticket"], "50.00")
        self.assertEqual(result["commission"], "3100.00")
        self.assertEqual(result["due"], "52700.00")
        self.assertEqual(result["occupancy_pct"], "100.00")
        self.assertEqual(plan_scenario(0, 0, "Own")["due"], "0.00")
        self.assertEqual(plan_scenario(1, 50, "Commission")["due"], "0.00")

    def test_invalid_and_overflowing_scenario_inputs_are_rejected(self):
        for seats in (
            True,
            None,
            "",
            "NaN",
            Decimal("sNaN"),
            "Infinity",
            "1.5",
            -1,
            63,
            {},
        ):
            with self.subTest(seats=seats), self.assertRaises(ValueError):
                plan_scenario(seats, 900, "Own")
        for fare in (
            True,
            None,
            "",
            "NaN",
            Decimal("sNaN"),
            "Infinity",
            "-1",
            "900.001",
            "1e999999",
            {},
        ):
            with self.subTest(fare=fare), self.assertRaises(ValueError):
                plan_scenario(1, fare, "Own")
        with self.assertRaisesRegex(ValueError, "precision"):
            plan_scenario(62, "99999999999999999999999999", "Own")
        with self.assertRaisesRegex(ValueError, "commission"):
            plan_scenario(1, "49.99", "Commission")
        for counter_type in ("own", "Commission ", "", None, {}):
            with self.subTest(counter_type=counter_type), self.assertRaises(ValueError):
                plan_scenario(1, 900, counter_type)


if __name__ == "__main__":
    unittest.main()
