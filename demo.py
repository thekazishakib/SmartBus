"""Create a disposable closed demonstration day and ready-to-print report."""
import argparse
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

from daily_system import ROOT, NS, workbook_parts, set_cell, make_printable_report
from ledger_store import LedgerStore
from period_export import make_period_excel


def prepare_demo(folder=None):
    folder = Path(folder or ROOT / 'demo_workspace').resolve()
    if (folder / 'data/ledger.sqlite3').exists():
        raise ValueError('A demo ledger already exists in this folder. Keep its files or choose a different --folder.')
    daily = folder / 'daily'
    daily.mkdir(parents=True, exist_ok=True)
    target = daily / 'Daily_2026-10-12_en.xlsx'
    if target.exists():
        raise ValueError('The demo daily file already exists. Choose a new --folder to preserve it.')
    shutil.copy2(ROOT / 'Demo_2026-10-12_en.xlsx', target)
    with ZipFile(target) as archive:
        files = {name:archive.read(name) for name in archive.namelist()}
    parts = workbook_parts(files)
    for name, changes in {'Settings':{'B9':'LIVE'}, 'Collections':{'M10':0}}.items():
        tree = ET.fromstring(files[parts[name]])
        for reference, value in changes.items():
            set_cell(tree, reference, value)
        files[parts[name]] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name,data)
    store = LedgerStore(folder)
    store.import_workbook(target, 'Demo operator')
    store.review_day('2026-10-12', 'Demo reviewer')
    store.close_day('2026-10-12', 'Demo reviewer')
    company = 'SmartBus DEMONSTRATION'
    printable = make_printable_report(daily,'2026-10-12','2026-10-12',company=company,report_folder=folder/'reports')
    excel = make_period_excel(daily,'2026-10-12','2026-10-12',company=company,report_folder=folder/'reports')
    return folder, printable, excel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,help='New disposable folder; default: demo_workspace')
    args = parser.parse_args()
    try:
        folder, printable, excel = prepare_demo(args.folder)
    except (ValueError, OSError) as error:
        parser.exit(1, f'SmartBus: {error}\n')
    print('Demonstration ready. All identities and transactions are fictional.')
    print(f'Workspace: {folder}')
    print(f'Excel: {excel}')
    print(f'Printable report: {printable}')
    print('Open the HTML file in your browser. Click Print / Save as PDF, select Save as PDF, then Save.')


if __name__ == '__main__':
    main()
