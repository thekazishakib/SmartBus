# Agent instructions for SmartBus

These instructions apply throughout this repository. Follow the user's requested scope and higher-priority instructions when making changes.

## Project purpose

SmartBus is a local bus revenue and collection reconciliation project built with Python, Excel workbooks, and SQLite. Its control panel uses plain HTML, CSS, and JavaScript. Keep project code, interface text, documentation, and reports in English.

The author is Kazi Shakib (`thekazishakib`). The project uses the MIT license. Preserve accurate attribution and third-party notices. Do not describe the project as a full accounting system: operating expenses and net profit are outside its current model.

## Architecture

- `daily_system.py`: workbook creation, input validation, collection, and printable reports.
- `counter_accounting.py`: monetary calculations and counter reconciliation.
- `values.py`: shared Decimal parsing, money rounding and date helpers.
- `xlsx_io.py`: shared workbook XML reading and worksheet row extraction.
- `platform_open.py`: OS-specific opening of saved files and folders.
- `ledger_store.py`: SQLite records, revisions, review, closing, corrections, audit history, and recovery.
- `control_panel.py`: local HTTP server and browser interface.
- `period_export.py` and `report_layout.py`: period workbooks and report presentation.
- `project_profile.py` and `project.json`: validated identity and branding settings.
- `demo.py`: isolated fictional demonstration data.
- `docs/README.template.md` and `tools/update_readme.py`: editable README source and generator.
- `tools/package_release.py`: distributable ZIP and checksum generation.

Read the relevant implementation and tests before changing behavior. The application and unittest suite use only the Python standard library. Ruff is a separate development dependency pinned in `requirements-dev.txt`; keep runtime and development requirements distinct. Do not add runtime dependencies unless the requested work justifies them. Do not add a frontend framework or turn the local panel into a public service without an explicit request.

## Financial rules

- Use `Decimal` for internal money calculations; convert only at an existing export boundary where needed.
- Fare revenue equals seats multiplied by fare. Capacity is 62 seats per trip.
- Commission counters receive Tk 50 per ticket; Own counters receive zero commission.
- Amount due equals fare revenue minus commission. Deposits represent actual receipts.
- Compute outstanding and extra receipts separately for each trip and counter. Never offset one counter's shortage against another counter's overpayment.
- Preserve the difference between a blank actual receipt and an explicit zero.
- Recompute from workbook inputs rather than trusting cached formula results.
- Reject invalid, duplicate, unsupported, or overflowing records explicitly. Never silently truncate data.
- Current workbook bounds are 100 trip rows, 500 collection rows, 100 master rows, 300 coaches, and 200 fares. Update validation, documentation, and tests together if bounds change.

## Ledger and user data

Preserve the draft → review → close workflow. Review must reject invalid or orphaned entries, trips without collection records, and blank receipt amounts. A known outstanding balance can be reviewed and closed.

Closed snapshots are the authority for final reports, even if the original workbook is later edited or removed. Preserve stable trip record IDs and revision history. Corrections require a reason; the previously published revision remains authoritative until the replacement is reviewed and closed. Missing dates are not automatically zero-activity days.

Keep same-hash imports idempotent, cross-process locking, source and snapshot checksums, and application audit protections. Operator labels provide attribution, not authenticated identities or separation of duties. Do not claim tamper-proof auditing.

Never use real account data for tests or demos. Do not overwrite user workbooks, databases, or backups while developing. Restore must validate the candidate database and retain recovery copies. Use a disposable folder for demo runs.

## Excel and reports

Preserve formulas, styles, validations, charts, sheet order, and freeze panes when editing workbook generation. Keep frozen transaction references stable so master-data edits cannot reprice existing records. Preserve existing workbook format markers unless implementing an explicit compatibility change. Settings!B12 must retain `AUTO_V6`; normalization uses `normalize_inputs`. Shared helpers belong in `values.py` or `xlsx_io.py`, while existing `daily_system` helper reexports preserve caller compatibility. Keep output keys such as `fee`, `net`, `cost` and `counter_cost` compatible with historical snapshots and reports even though collection fee/cost inputs and zero-expense calculations have been removed.

Users should save and close Excel before importing. Period exports must retain source revision information and use the same closed records as printable reports. Keep CSV and JSON source sidecars consistent with their report.

Printable HTML is the portable PDF workflow: open the report, choose **Print / Save as PDF**, and save from the browser. Automatic Edge PDF generation is optional. Preserve usable HTML and sidecars if automatic PDF generation fails. Hide interactive controls when printing, and preserve report pagination and paper settings.

Do not claim a native print dialog, Excel desktop interaction, or PDF rendering was verified unless it was actually exercised. Identify workflow illustrations separately from actual workbook previews.

## Local interface security

Keep the server bound to loopback. Preserve session tokens, Host/Origin checks, request limits, CSP nonces, serialized mutations, and restricted report-file serving. Never expose arbitrary files, database contents, or raw exception tracebacks through browser endpoints. Route file/folder opening through `platform_open.open_path`; a desktop launch failure must retain the saved-file path in the response instead of turning a completed export into an HTTP 500. New mutating routes need the same protections as existing routes.

## Customization and documentation

Use `project.json` for supported branding settings. Do not make financial rules configurable through branding fields. Keep validation and defaults aligned.

Edit `docs/README.template.md` for lasting README changes, then run:

```powershell
python tools/update_readme.py
```

Document actual behavior, supported commands, and known limitations. Keep examples fictional. Update `THIRD_PARTY_NOTICES.md` when adding third-party code or assets; the project's MIT license does not relicense external tools.

## Verification

Use Python 3.11 or newer. Run checks appropriate to the change. For accounting, ledger, validation, or export behavior, run the relevant tests and the full suite before release:

```powershell
python -m pip install -r requirements-dev.txt
ruff format --check .
ruff check .
python -m unittest discover -s . -p "test_*.py" -v
python -m compileall -q .
```

Use `ruff format .` to apply formatting and inspect any fixes from `ruff check --fix .`. Run the full suite after each substantial refactoring step. For workbook changes, also inspect generated workbook structure and relevant formatting. For interface changes, check JavaScript syntax and relevant server tests. For documentation-only changes, verify paths, generated documentation, and package contents; do not add redundant tests or claim a test run that did not happen.

## Release packaging

Build the distributable using:

```powershell
python tools/package_release.py
```

The default output folder is `dist/`. The builder creates a ZIP, a release manifest with file hashes, and a SHA-256 checksum. Verify archive integrity and manifest consistency after changes. If delivering an extracted copy alongside the ZIP, keep its files and manifest synchronized.

Exclude live ledgers, backups, daily transactions, generated private reports, secrets, caches, and virtual environments from releases. Preserve the MIT license and third-party notices. Creating a local GitHub-ready package does not authorize publishing a repository or release; follow the user's requested delivery scope.
