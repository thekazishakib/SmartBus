"""Regression coverage for extracted value conversions and workbook inputs."""

import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import values
import xlsx_io

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "Demo_2026-10-12_en.xlsx"


class SharedValueTests(unittest.TestCase):
    def test_decimal_inputs_preserve_precision_and_reject_invalid_values(self):
        self.assertEqual(
            values.dec("0.100000000000000001"), Decimal("0.100000000000000001")
        )
        for value in (None, "", "not money", "NaN", "Infinity", float("-inf")):
            with self.subTest(value=value):
                self.assertIsNone(values.dec(value))

    def test_money_rounds_half_up_and_rejects_unsupported_precision(self):
        self.assertEqual(values.money("1.005"), Decimal("1.01"))
        self.assertEqual(values.money(Decimal("-1.005")), Decimal("-1.01"))
        self.assertIsNone(values.money("1E+1000"))
        self.assertIsNone(values.money("NaN"))

    def test_excel_serial_and_iso_dates_preserve_local_wall_time(self):
        self.assertEqual(values.dt(0), values.EPOCH)
        self.assertEqual(values.dt(2.5), datetime(1900, 1, 1, 12))
        self.assertEqual(
            values.dt("2026-10-12T09:30:00+06:00"), datetime(2026, 10, 12, 9, 30)
        )

    def test_invalid_or_unrepresentable_dates_return_none(self):
        for value in (None, "", "2026-02-30", "not a date", float("inf"), 10**20):
            with self.subTest(value=value):
                self.assertIsNone(values.dt(value))


class WorkbookIOTests(unittest.TestCase):
    def test_saved_inputs_include_rich_strings_but_skip_formula_caches(self):
        with ZipFile(DEMO) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
        relationships = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in ET.fromstring(parts["xl/_rels/workbook.xml.rels"])
        }
        sheet = ET.fromstring(parts["xl/workbook.xml"]).find(
            "s:sheets/s:sheet", xlsx_io.NS
        )
        target = relationships[sheet.attrib["{" + xlsx_io.NS["r"] + "}id"]]
        target = target.lstrip("/") if target.startswith("/") else "xl/" + target
        tree = ET.fromstring(parts[target])
        row = ET.SubElement(
            tree.find("s:sheetData", xlsx_io.NS), xlsx_io.tag("row"), {"r": "900"}
        )
        inline = ET.SubElement(row, xlsx_io.tag("c"), {"r": "A900", "t": "inlineStr"})
        inline_text = ET.SubElement(inline, xlsx_io.tag("is"))
        for text in ("Inline ", "value"):
            run = ET.SubElement(inline_text, xlsx_io.tag("r"))
            ET.SubElement(run, xlsx_io.tag("t")).text = text
        shared = (
            ET.fromstring(parts["xl/sharedStrings.xml"])
            if "xl/sharedStrings.xml" in parts
            else ET.Element(xlsx_io.tag("sst"))
        )
        index = len(shared.findall("s:si", xlsx_io.NS))
        item = ET.SubElement(shared, xlsx_io.tag("si"))
        for text in ("Shared ", "value"):
            run = ET.SubElement(item, xlsx_io.tag("r"))
            ET.SubElement(run, xlsx_io.tag("t")).text = text
        shared_cell = ET.SubElement(row, xlsx_io.tag("c"), {"r": "B900", "t": "s"})
        ET.SubElement(shared_cell, xlsx_io.tag("v")).text = str(index)
        formula = ET.SubElement(row, xlsx_io.tag("c"), {"r": "C900"})
        ET.SubElement(formula, xlsx_io.tag("f")).text = "1+1"
        ET.SubElement(formula, xlsx_io.tag("v")).text = "999999"
        parts[target] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
        parts["xl/sharedStrings.xml"] = ET.tostring(
            shared, encoding="utf-8", xml_declaration=True
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fictional.xlsx"
            with ZipFile(path, "w", ZIP_DEFLATED) as archive:
                for name, data in parts.items():
                    archive.writestr(name, data)
            cells = xlsx_io.read_book(path)[sheet.attrib["name"]]
        self.assertEqual(cells["A900"], "Inline value")
        self.assertEqual(cells["B900"], "Shared value")
        self.assertNotIn("C900", cells)

    def test_workbook_without_manual_marker_is_rejected(self):
        with ZipFile(DEMO) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
        tree = ET.fromstring(parts["xl/workbook.xml"])
        for sheet in tree.findall("s:sheets/s:sheet", xlsx_io.NS):
            if sheet.attrib["name"] == "Read the Manual":
                sheet.set("name", "Missing compatibility marker")
        parts["xl/workbook.xml"] = ET.tostring(
            tree, encoding="utf-8", xml_declaration=True
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "unsupported.xlsx"
            with ZipFile(path, "w", ZIP_DEFLATED) as archive:
                for name, data in parts.items():
                    archive.writestr(name, data)
            with self.assertRaisesRegex(ValueError, "Old workbook format"):
                xlsx_io.read_book(path)

    def test_sparse_rows_preserve_blanks_and_include_last_supported_row(self):
        cells = {
            "A6": 0,
            "B6": "first",
            "A7": "",
            "B7": "orphan",
            "A8": "last",
            "A9": "outside",
        }
        self.assertEqual(
            xlsx_io.rows(cells, ("A", "B"), 8), [[0, "first"], ["last", None]]
        )


class SharedImportTests(unittest.TestCase):
    def test_accounting_uses_helpers_without_importing_daily_system(self):
        script = """
import sys
import counter_accounting as accounting
assert "daily_system" not in sys.modules
assert accounting.positive_integer("3", "quantity") == 3
assert "daily_system" not in sys.modules
import values
import xlsx_io
assert accounting.dec is values.dec
assert accounting.read_book is xlsx_io.read_book
import daily_system as daily
assert daily.dec is values.dec
assert daily.money is values.money
assert daily.dt is values.dt
assert daily.read_book is xlsx_io.read_book
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
