# SmartBus 1.2.1 release notes

Release date: 14 October 2026.

## What changed

This release improves maintainability and saved-file handling. Python code uses Ruff formatting and lint checks. Input normalization now has a descriptive name and a clearer workbook-format error. Shared value/date helpers and workbook XML reading live in `values.py` and `xlsx_io.py`, so counter accounting no longer depends on `daily_system.py`.

Unused collection fee/cost inputs and zero-expense arithmetic were removed. Report and snapshot output keys remain compatible with older records. Newly generated report filenames start with `SmartBus_`. Optional R charts use a system sans-serif font.

Saved files and folders open through a platform helper: Windows uses its default association, macOS uses `open`, and Linux uses `xdg-open`. If desktop opening fails, the panel reports the saved path. This helper does not establish that the full application has been verified on macOS or Linux.

## Financial behavior and existing users

The accounting model is unchanged: 62-seat capacity; Tk 50 commission at commission counters; zero at own counters; separate per-trip/counter shortages and extra receipts. Operating expenses and net profit remain outside this model. Final reports keep the previous closed values while a correction is open.

The SQLite schema remains version 1, and Settings!B12 retains `AUTO_V6`. This release does not re-import accounts, revise closed snapshots or rename existing exports. Keep a backup before upgrading and save/close Excel before import.

## Development

The application and unittest suite still use only the Python standard library. Ruff 0.17.0 is a separate development dependency in `requirements-dev.txt`. CI is configured to check formatting, lint, tests and compilation on Windows and Ubuntu.

Run `launch.bat` or `python control_panel.py` for the established desktop workflow. Use `python demo.py --folder another_demo` for a fresh fictional example. Follow [PDF export](PDF_EXPORT.md), [customization](CUSTOMIZATION.md) and [contributing](../CONTRIBUTING.md).

Configurable financial rules, a package restructure, mypy, a Unix launcher, additional automatic PDF engines and LibreOffice CI are outside this first refactoring pass.

## Verification

See [delivery verification](DELIVERY_VERIFICATION.md) for the recorded checks and limitations. Local tests do not establish native macOS/Linux opening, Excel desktop behavior, Edge PDF rendering or R execution. Remote GitHub Actions results are established only after those jobs run.
