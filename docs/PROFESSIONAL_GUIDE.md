# SmartBus 1.3.0 operating guide

The local panel now has Overview, Daily operations, Reports & exports, Scenario planner, Public data lab, Recovery & activity, and Customize views. Overview reads closed ledger revisions only. Scenario planning creates no transaction. Public data lab uses a separate official Chicago ridership snapshot. See [the portfolio guide](PORTFOLIO_GUIDE.md) for research methods and [the learning path](LEARNING_PATH.md) for courses.

This is the current guide for SmartBus's English-only interface, Excel workbooks, reports and SQLite ledger.

## Install and start

Use a writable project folder on one Windows computer with Python 3.11+ and Microsoft Excel. Microsoft Edge is optional for automatic PDF printing; browser Print / Save as PDF is the portable reporting method. The application and unittest suite use only the Python standard library. Ruff is a separate development dependency. The application uses system fonts and needs no font installation. R analysis is optional.

Run `launch.bat` or `python control_panel.py`. Keep the launcher open. Stop the server by closing it or pressing Ctrl+C in its terminal. Run `python control_panel.py --no-browser` to avoid opening the browser automatically, then use the printed local address.

Saved files and folders use the operating system's default opener. If opening fails, the panel shows the saved path so you can open it manually. macOS and Linux launch commands are supported by the helper, but the full desktop workflow has not been verified there.

The ledger is stored at `data/ledger.sqlite3`; database backups are under `backups/` and source-workbook recovery copies are under `backups/workbooks/`. Use one running application against a ledger.

## Configure and enter a day

Create the English daily workbook. Daily files use `Daily_YYYY-MM-DD_en.xlsx`, such as `Daily_2026-10-13_en.xlsx`. Replace fictional company, staff, bus, coach, route and counter data. Configure fares before sales; live-template fares start blank. Confirm counter names and types because they determine commission and settlement.

The input capacity is 100 trips and 500 collection rows per day. Extra nonempty rows are rejected. Extend and test the application before adopting a larger daily workload; simply adding spreadsheet rows does not extend the supported input layout.

Enter trip sales and counter collection lines. Enter **0** as a deposit when nothing was received; a blank amount means incomplete information and blocks review. A known outstanding balance may remain after review.

Save and **close Excel before importing**. Import updates the source workbook atomically to freeze trip identifiers, route/driver assignments, collection references and accepted fares; it preserves a source backup before changing the workbook. Unsaved Excel changes are not included.

## Import, review and close

1. Import the saved workbook to create or update its daily draft.
2. Compare trip counts, sold seats, fare, commission, deposits and counter differences with supporting records.
3. Resolve invalid inputs, investigate differences and record an explicit review using your operator label.
4. Close the reviewed revision when accepted.
5. Generate final reports from the closed ledger records.

Importing does not approve accounts. Replacing a draft requires review again. The supplied actor label appears in audit history but does not authenticate identity or enforce separate reviewer and closer roles.

Example commands, run from the project folder:

```text
python ledger_store.py import daily/Daily_2026-10-13_en.xlsx --actor "Finance intern"
python ledger_store.py status
python ledger_store.py review 2026-10-13 --actor "Reviewer"
python ledger_store.py close 2026-10-13 --actor "Closer"
python ledger_store.py audit --limit 20
```

Use your actual workbook path and business date. `python ledger_store.py --help` shows the available commands. An alternate project/data root is supplied before the command: `python ledger_store.py --root PATH status`.

## Understand the amounts

| Measure | Meaning |
| --- | --- |
| Fare | Sold seats multiplied by the accepted fare |
| Commission | Tk 50 per ticket at commission counters; zero at own counters |
| After commission | Fare minus counter commission |
| Deposits | Amounts recorded as received from each counter |
| Outstanding | Counter shortfalls remaining against the amount due |
| Surplus | Counter overpayments, separate from other counters' shortages |

Investigate individual counter rows as well as totals. A surplus at one counter does not discharge another counter's obligation. These measures exclude fuel, salaries, maintenance, taxes and other operating expenses. Fare less commission is not net profit.

The reference demo has three trips and 74 sold seats: Tk 70,600 fare, Tk 2,250 commission, Tk 68,350 after commission, Tk 49,450 deposits and Tk 18,900 outstanding. Demo identities and amounts are fictional.

## Correct a closed day

Start a correction for the closed business date and supply a clear reason:

```text
python ledger_store.py correct 2026-10-13 --reason "Correct counter deposit from receipt" --actor "Finance intern"
```

Edit the source workbook, save and close Excel, then import it. Review and close the replacement revision using the same workflow. The previous closure remains authoritative until the replacement closes. A half-completed correction does not erase accepted accounts.

Imported rows retain their captured values. Changing a master fare, driver or route list does not refresh those existing rows. After starting a correction, edit the appropriate transaction field: Collections column H for fare or F for counter type; Trips column D for route or G for driver. These captured cells remain editable. Verify the replacement draft before closure; master lists still support new rows.

Preserve frozen trip identifiers in corrections. They match stable ledger UUIDs across revisions. Worksheet row numbers and pre-import formula numbering are not permanent ledger identifiers; moving rows before the first import can still affect workbook formula references. Inspect identity matching and the replacement reconciliation before closing.

The audit history records local operations, actor labels and correction reasons.

## Generate reports

For PDF, use **Open printable report**, open the result link, then click **Print / Save as PDF** and choose a PDF destination. The [PDF export guide](PDF_EXPORT.md) gives browser, Excel and optional automatic methods. Company and identity defaults are editable in [project.json](../project.json); see [customization](CUSTOMIZATION.md).


Final Excel/PDF exports use closed ledger snapshots. Later source fare or assignment edits do not change those accepted values. The panel warns when source data differs from its imported snapshot; resolve a needed change through correction.

Excel exports include permanent record IDs and closed revision numbers on the Trips sheet. Each Excel export has a companion `.sources.json` manifest; successful PDF exports include source metadata and trip/counter CSV files. Keep those files together for traceability. Reports visibly disclose open corrections and retain the last closed revision until replacement closure.

Check date range, included dates, missing dates and totals before distribution. A missing date does not prove zero business. Workbook-only preview is for demonstrations and uses `--demo` where supported; it does not establish ledger closure. Malformed files inside a preview range stop processing with the source identified; dated files outside the range are ignored before parsing.

PDF output uses Edge on Windows and system fonts. Inspect representative English PDFs on the target computer. Automated tests do not verify Excel desktop, your printer or Edge rendering in your installation.

## Back up and restore

Create a ledger backup after important closures and before maintenance:

```text
python ledger_store.py backup
```

SmartBus creates versioned SQLite backup files under `backups/`. Copy selected backups to separate storage through your normal backup process.

Stop other SmartBus processes using the ledger before restoration. Select the intended backup in the panel, or run:

```text
python ledger_store.py restore SELECTED_BACKUP.sqlite3 --actor "Operator"
```

Replace the example with the actual filename from `backups/`; restore accepts a filename, not a path outside that folder. Restore checks SQLite integrity before replacing the ledger and preserves the current ledger as a recovery copy. Then inspect status and recent audit events and reproduce a known report to confirm the restored point in time.

Recovery also works when the current ledger is damaged. A damaged current file is preserved with a `.sqlite3.damaged` extension for investigation; it is not offered as a verified backup. If the panel cannot start, use the command-line restore above. Recoverable audit events after the selected backup are retained as recovery history; they do not reinstate rolled-back account revisions.

Ledger backups cover database records. Source workbooks, exports and application files need separate copies. Rehearse recovery with a disposable project copy before relying on this process.

## Operating boundaries

SmartBus targets one computer. It provides no authenticated login, multiuser concurrency controls or role-based approvals. Actor labels do not enforce segregation of duties. A database-file owner can modify records directly. Closure and audit history provide application-level traceability, not tamper-proof storage or legal record certification.

Use your computer's access controls for the project and backups. Confirm accounting and retention procedures with the responsible finance operator.

## Acceptance before real use

- Verify fares, counter types, commission rules and identities.
- Independently reconcile a representative day's calculations.
- Confirm invalid and overflowing inputs fail visibly.
- Close a test day, edit its source fare, and confirm closed report values remain stable.
- Complete a reasoned correction and inspect both revisions.
- Back up and restore a disposable ledger, then reproduce known totals.
- Edit and save in your Excel installation; inspect English exports in Edge and on the intended printer.

## Developer checks

```text
python -m pip install -r requirements-dev.txt
ruff format --check .
ruff check .
python -m unittest discover -s . -p "test_*.py" -v
python -m compileall -q .
```

See [contributor guidance](../CONTRIBUTING.md). Original project material is released under the MIT License; see LICENSE and THIRD_PARTY_NOTICES.md.
