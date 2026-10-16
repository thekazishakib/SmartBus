"""Create reproducible fictional closed demo days and ready-to-print reports."""

import argparse
import io
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from daily_system import (
    EPOCH,
    NS,
    ROOT,
    dt,
    make_printable_report,
    set_cell,
    workbook_parts,
)
from ledger_store import LedgerStore
from period_export import make_period_excel

DEMO_END = date(2026, 10, 12)


def _demo_workbook(source, day):
    """Adjust only fictional inputs, preserving styles and all other ZIP parts."""
    files = source.copy()
    parts = workbook_parts(files)
    distance = (DEMO_END - day).days
    second_seats = 20 + distance % 9
    third_seats = 40 - 2 * (distance % 11)
    changes = {
        "Settings": {
            "B6": (datetime.combine(day, datetime.min.time()) - EPOCH).days,
            "B9": "LIVE",
        },
        "Collections": {
            "G10": second_seats,
            "G11": third_seats,
            # Day zero retains the original sample's explicit zero receipt.
            "M10": 0 if not distance else (second_seats - distance % 5) * 900,
            "M11": third_seats * 950 - (500 + 150 * (distance % 4)),
        },
        "Trips": {},
    }
    if distance:
        changes["Settings"]["A3"] = "Fictional deterministic multi-day demonstration."
    for name, updates in changes.items():
        tree = ET.fromstring(files[parts[name]])
        if name == "Trips":
            # Departure clocks stay the same, but each trip belongs to its own day.
            for row in (6, 7, 8):
                reference = f"C{row}"
                cell = tree.find(f".//s:c[@r='{reference}']/s:v", NS)
                if cell is None or dt(cell.text) is None:
                    raise ValueError("The packaged demo departure dates are invalid.")
                original = dt(cell.text)
                departure = datetime.combine(day, original.time())
                updates[reference] = (departure - EPOCH).total_seconds() / 86400
        for reference, value in updates.items():
            previous = tree.find(f".//s:c[@r='{reference}']", NS)
            style = previous.get("s") if previous is not None else None
            set_cell(tree, reference, value)
            if style is not None:
                tree.find(f".//s:c[@r='{reference}']", NS).set("s", style)
        files[parts[name]] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def prepare_demo(folder=None, days=1):
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 31:
        raise ValueError("Demo days must be a whole number from 1 to 31.")
    folder = Path(folder or ROOT / "demo_workspace").resolve()
    if folder.exists() and not folder.is_dir():
        raise ValueError("Choose a new disposable folder, not an existing file.")
    # Complete all destination checks before creating any files or ledger records.
    for name in ("daily", "data", "backups", "reports"):
        destination = folder / name
        if destination.is_symlink() or (
            destination.exists()
            and (not destination.is_dir() or any(destination.iterdir()))
        ):
            raise ValueError(
                f"The demo folder contains existing {name} files. Choose a new --folder to preserve them."
            )
    start = DEMO_END - timedelta(days=days - 1)
    dates = [start + timedelta(days=offset) for offset in range(days)]
    with ZipFile(ROOT / "Demo_2026-10-12_en.xlsx") as archive:
        source = {name: archive.read(name) for name in archive.namelist()}
    staged = [(day, _demo_workbook(source, day)) for day in dates]
    daily = folder / "daily"
    daily.mkdir(parents=True, exist_ok=True)
    store = LedgerStore(folder)
    for day, content in staged:
        target = daily / f"Daily_{day}_en.xlsx"
        with target.open("xb") as handle:
            handle.write(content)
        store.import_workbook(target, "Demo operator")
        store.review_day(day.isoformat(), "Demo reviewer")
        store.close_day(day.isoformat(), "Demo reviewer")
    company = "SmartBus DEMONSTRATION"
    printable = make_printable_report(
        daily,
        start.isoformat(),
        DEMO_END.isoformat(),
        company=company,
        report_folder=folder / "reports",
    )
    excel = make_period_excel(
        daily,
        start.isoformat(),
        DEMO_END.isoformat(),
        company=company,
        report_folder=folder / "reports",
    )
    (folder / ".smartbus-demo").write_text(
        "Fictional SmartBus demonstration. No real financial transactions.\n",
        encoding="utf-8",
    )
    return folder, printable, excel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--folder", type=Path, help="New disposable folder; default: demo_workspace"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Fictional closed dates ending 2026-10-12 (1 to 31; default 1)",
    )
    args = parser.parse_args()
    try:
        folder, printable, excel = prepare_demo(args.folder, days=args.days)
    except (ValueError, OSError) as error:
        parser.exit(1, f"SmartBus: {error}\n")
    print("Demonstration ready. All identities and transactions are fictional.")
    print(f"Closed days: {args.days}; end date: {DEMO_END}")
    print(f"Workspace: {folder}")
    print(f"Excel: {excel}")
    print(f"Printable report: {printable}")
    print(
        "Open the HTML file in your browser. Click Print / Save as PDF, select Save as PDF, then Save."
    )


if __name__ == "__main__":
    main()
