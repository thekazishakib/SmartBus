"""Daily Excel files and immutable date-range PDF reports. Python standard library only.

Excel XML is read directly so the PDF recomputes from saved inputs rather than stale
formula caches. Edge's print engine is used for print-ready PDF output.
"""

import argparse
import csv
import html
import json
import os
import re
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from counter_accounting import calculate as counter_calculate
from project_profile import APP_VERSION, load_profile
from values import EPOCH as EPOCH
from values import dec as dec
from values import dt as dt
from values import money as money
from xlsx_io import MAIN as MAIN
from xlsx_io import NS as NS
from xlsx_io import read_book as read_book
from xlsx_io import rows as rows
from xlsx_io import tag as tag

ROOT = Path(__file__).resolve().parent


def esc(x):
    return html.escape("" if x is None else str(x))


def stamp(x):
    return x.strftime("%Y-%m-%d %H:%M") if isinstance(x, datetime) else x


def fmt(x):
    if x is None or x == "":
        return "-"
    if isinstance(x, Decimal):
        return f"{x:,.2f}"
    return esc(stamp(x))


def calculate(path):
    return counter_calculate(path)


def validate_book(book):
    """Reject invalid transaction data before a report or reviewed snapshot.

    Pending deposits, shortages and overpayments are normal reconciliation
    states. Invalid rows and unresolved references are data errors instead.
    ``calculate`` deliberately retains those rows so the operator can inspect
    and correct them before exporting.
    """
    problems = []
    for trip in book.get("trips", []):
        for issue in trip.get("issues", []):
            problems.append(f"Trip {trip['trip']}: {issue}")
    for line in book.get("orphan", []):
        problems.append(
            f"Collection for trip {line['trip']}, counter "
            f"{line.get('counter') or '(blank)'}: missing or duplicate trip"
        )
    # Include line errors even when a malformed line cannot join a trip.
    for line in book.get("lines", []):
        if line in book.get("orphan", []):
            problems.extend(
                f"Collection for trip {line['trip']}: {issue}"
                for issue in line.get("issues", [])
            )
    if problems:
        unique = list(dict.fromkeys(problems))
        raise ValueError(
            "Correct workbook data before reporting:\n- " + "\n- ".join(unique)
        )
    return book


def set_cell(tree, ref, value):
    data = tree.find("s:sheetData", NS)
    rownum = "".join(c for c in ref if c.isdigit())
    row = data.find("s:row[@r='" + rownum + "']", NS)
    if row is None:
        row = ET.SubElement(data, tag("row"), {"r": rownum})
    old = row.find("s:c[@r='" + ref + "']", NS)
    if old is not None:
        row.remove(old)
    if value in (None, ""):
        return
    c = ET.SubElement(row, tag("c"), {"r": ref})
    if isinstance(value, (int, float)):
        ET.SubElement(c, tag("v")).text = str(value)
    else:
        c.set("t", "inlineStr")
        ET.SubElement(ET.SubElement(c, tag("is")), tag("t")).text = str(value)

    # Excel expects cells in ascending column order.
    def number(c):
        n = 0
        for x in c.get("r", ""):
            if x.isalpha():
                n = n * 26 + ord(x) - 64
        return n

    row[:] = sorted(row, key=number)
    data[:] = sorted(data, key=lambda r: int(r.get("r")))


def workbook_parts(files):
    rel = {
        r.attrib["Id"]: r.attrib["Target"]
        for r in ET.fromstring(files["xl/_rels/workbook.xml.rels"])
    }
    result = {}
    for sheet in ET.fromstring(files["xl/workbook.xml"]).findall(
        "s:sheets/s:sheet", NS
    ):
        target = rel[sheet.attrib["{" + NS["r"] + "}id"]]
        result[sheet.attrib["name"]] = (
            target.lstrip("/") if target.startswith("/") else "xl/" + target
        )
    return result


def create_daily(day, lang="en", folder=None):
    day = date.fromisoformat(str(day))
    folder = Path(folder or ROOT / "daily")
    folder.mkdir(parents=True, exist_ok=True)
    if lang != "en":
        raise ValueError("This release supports English only")
    if list(folder.glob("Daily_" + str(day) + "_*.xlsx")):
        raise ValueError("This day already has a workbook. Continue that file.")
    with ZipFile(ROOT / f"Daily_Template_{lang}.xlsx") as z:
        files = {n: z.read(n) for n in z.namelist()}
    parts = workbook_parts(files)
    trees = {name: ET.fromstring(files[part]) for name, part in parts.items()}
    styles = {
        name: {c.get("r"): c.get("s") for c in tree.findall(".//s:c", NS)}
        for name, tree in trees.items()
    }
    set_cell(
        trees["Settings"],
        "B6",
        (datetime.combine(day, datetime.min.time()) - EPOCH).days,
    )
    set_cell(trees["Settings"], "B9", "LIVE")
    previous = sorted(
        p for p in folder.glob("Daily_*_" + lang + ".xlsx") if p.name[6:16] < str(day)
    )
    if not previous:
        set_cell(trees["Settings"], "B8", load_profile(ROOT)["company_name"])
    if previous:
        saved = read_book(previous[-1])
        from counter_accounting import validate_saved_inputs

        validate_saved_inputs(saved)
        if saved["Settings"].get("B12") != "AUTO_V6":
            raise ValueError("Keep old-format workbooks in a separate folder.")
        for ref, value in saved["Settings"].items():
            col = "".join(c for c in ref if c.isalpha())
            row = int("".join(c for c in ref if c.isdigit()))
            if ref in ("B7", "B8", "B17"):
                set_cell(trees["Settings"], ref, value)
        for name, cols, end in [
            ("Buses", ["A", "B"], 105),
            ("Crew", ["A", "B", "C"], 105),
            ("Counters", ["A", "B"], 105),
            ("Route List", ["A", "B", "C", "F", "G"], 305),
        ]:
            for row in range(6, end + 1):
                for col in cols:
                    set_cell(trees[name], f"{col}{row}", saved[name].get(f"{col}{row}"))
    for name, tree in trees.items():
        for c in tree.findall(".//s:c", NS):
            style = styles[name].get(c.get("r"))
            if style is not None:
                c.set("s", style)
        files[parts[name]] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
    book = ET.fromstring(files["xl/workbook.xml"])
    calc = book.find("s:calcPr", NS)
    if calc is None:
        calc = ET.SubElement(book, tag("calcPr"))
    calc.attrib.update(fullCalcOnLoad="1", forceFullCalc="1", calcMode="auto")
    files["xl/workbook.xml"] = ET.tostring(book, encoding="utf-8", xml_declaration=True)
    target = folder / f"Daily_{day}_{lang}.xlsx"
    with ZipFile(target, "x", ZIP_DEFLATED) as z:
        for name, raw in files.items():
            z.writestr(name, raw)
    return target


def collect(folder, start, end, allow_demo=False, require_closed=False):
    if require_closed and not allow_demo:
        from ledger_store import collect_closed

        return collect_closed(folder, start, end)
    start = date.fromisoformat(str(start))
    end = date.fromisoformat(str(end))
    if start > end:
        raise ValueError("Start date must be on or before end date.")
    found, excluded, failures = {}, [], []
    pattern = re.compile(r"^(Daily|Demo)_(\d{4}-\d{2}-\d{2})_(bn|en)\.xlsx$")
    for path in sorted(Path(folder).glob("*.xlsx")):
        match = pattern.fullmatch(path.name)
        if not match or match[1] == "Demo" and not allow_demo:
            continue
        # Inspect the filename first: an unrelated corrupt workbook must not
        # prevent the selected reporting period from being exported.
        try:
            filename_day = date.fromisoformat(match[2])
        except ValueError:
            continue
        if not start <= filename_day <= end:
            continue
        try:
            if match[3] != "en":
                raise ValueError("This release supports English daily workbooks only")
            book = calculate(path)
            day = date.fromisoformat(book["day"])
            if day != filename_day:
                raise ValueError("File date and filename differ")
            if book["dataset"] != "LIVE" and not allow_demo:
                excluded.append(path.name)
                continue
            validate_book(book)
            if day in found:
                raise ValueError(
                    f"Two workbooks for {day}: "
                    f"{Path(found[day]['path']).name} and {path.name}. "
                    "Keep only one daily file/language in the daily folder."
                )
            found[day] = book
        except Exception as error:
            failures.append(f"{path.name}: {type(error).__name__}: {error}")
    if failures:
        raise ValueError(
            "Report cancelled; no incomplete report was created.\n- "
            + "\n- ".join(failures)
        )
    if not found:
        raise ValueError("No saved daily workbooks found in the selected date range.")
    missing = [
        str(start + timedelta(days=i))
        for i in range((end - start).days + 1)
        if start + timedelta(days=i) not in found
    ]
    return [found[day] for day in sorted(found)], missing, excluded


def report_html(
    books, missing, excluded, start, end, lang="en", company=None, counter=None
):
    from report_layout import render_report

    return render_report(
        books,
        missing,
        excluded,
        start,
        end,
        lang,
        company or load_profile(ROOT)["company_name"],
        counter,
    )


def edge_path():
    for p in [
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
        / "Microsoft/Edge/Application/msedge.exe",
    ]:
        if p.exists():
            return str(p)
    raise ValueError("Microsoft Edge is required to create PDF reports.")


def make_printable_report(
    folder,
    start,
    end,
    lang="en",
    allow_demo=False,
    report_folder=None,
    company=None,
    counter=None,
):
    """Create a browser-printable report with the same closed-ledger accounts."""
    if lang != "en":
        raise ValueError("This release supports English only")
    books, missing, excluded = collect(
        folder, start, end, allow_demo, require_closed=True
    )
    reports = Path(report_folder or ROOT / "reports")
    reports.mkdir(parents=True, exist_ok=True)
    ident = (
        f"SmartBus_{start}_{end}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    )
    source = reports / (ident + ".html")
    source.write_text(
        report_html(books, missing, excluded, start, end, lang, company, counter),
        encoding="utf-8",
    )
    # A snapshot contains both readable PDF and machine-readable inputs for audit / R.
    with (reports / (ident + "_trips.csv")).open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        cols = [
            "day",
            "trip",
            "record_id",
            "coach",
            "start",
            "end",
            "route",
            "direction",
            "bus",
            "driver",
            "driver_phone",
            "guide",
            "guide_phone",
            "conductor",
            "conductor_phone",
            "capacity",
            "seats",
            "gross",
            "commission",
            "due",
            "actual",
            "variance",
            "occupancy",
            "status",
            "fuel",
            "other",
            "extra",
            "total_cost",
            "after_cost",
            "previous",
            "note",
            "sent_to_office",
            "held_cash",
            "outstanding",
            "pending_counters",
        ]
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for b in books:
            for t in b["trips"]:
                writer.writerow({k: stamp(t.get(k)) for k in cols})
    with (reports / (ident + "_counters.csv")).open(
        "w", newline="", encoding="utf-8-sig"
    ) as stream:
        columns = [
            "day",
            "trip",
            "counter",
            "kind",
            "seats",
            "gross",
            "commission",
            "due",
            "actual",
            "outstanding",
            "sent_to_office",
            "held_cash",
            "status",
        ]
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for book in books:
            for account in book["counter_groups"]:
                writer.writerow(
                    {
                        key: book["day"] if key == "day" else account.get(key)
                        for key in columns
                    }
                )
    (reports / (ident + "_sources.json")).write_text(
        json.dumps(
            dict(
                start=str(start),
                end=str(end),
                application_version=APP_VERSION,
                sources=[
                    dict(
                        day=b["day"], file=Path(b["path"]).name, ledger=b.get("ledger")
                    )
                    for b in books
                ],
                missing=missing,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return source


def make_report(
    folder,
    start,
    end,
    lang="en",
    allow_demo=False,
    report_folder=None,
    company=None,
    counter=None,
):
    """Optional automatic PDF; browser-printable HTML survives engine failures."""
    source = make_printable_report(
        folder, start, end, lang, allow_demo, report_folder, company, counter
    )
    pdf = source.with_suffix(".pdf")
    with tempfile.TemporaryDirectory(prefix="bus_pdf_") as profile:
        cmd = [
            edge_path(),
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--user-data-dir=" + profile,
            "--print-to-pdf=" + str(pdf.resolve()),
            "--no-pdf-header-footer",
            source.resolve().as_uri(),
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=90,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as error:
            raise ValueError(
                "PDF creation timed out. Use Open printable report, then Print / Save as PDF. Printable HTML: "
                + source.name
            ) from error
    if result.returncode or not pdf.exists() or pdf.stat().st_size < 1000:
        pdf.unlink(missing_ok=True)
        raise ValueError(
            "PDF creation failed. Use Open printable report, then Print / Save as PDF. The printable HTML is saved in reports: "
            + source.name
        )
    return pdf


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    new = sub.add_parser("new")
    new.add_argument("date")
    new.add_argument("--language", choices=["en"], default="en")
    rep = sub.add_parser("report")
    rep.add_argument("start")
    rep.add_argument("end")
    rep.add_argument("--folder", default=str(ROOT / "daily"))
    rep.add_argument("--language", choices=["en"], default="en")
    rep.add_argument("--demo", action="store_true")
    rep.add_argument("--company", default=None)
    rep.add_argument("--counter", default="")
    rep.add_argument(
        "--printable",
        action="store_true",
        help="Save HTML; open it and use Print / Save as PDF.",
    )
    a = p.parse_args()
    if a.cmd == "new":
        print(create_daily(a.date, a.language))
    else:
        export = make_printable_report if a.printable else make_report
        print(
            export(
                a.folder,
                a.start,
                a.end,
                a.language,
                a.demo,
                company=a.company,
                counter=a.counter,
            )
        )
