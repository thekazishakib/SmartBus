# SmartBus 1.2.0 release notes

Release date: 14 October 2026.

## What changed

- Browser-printable report with a Print / Save as PDF button, keeping Excel/PDF data tied to the same closed ledger.
- PDF export guide covering browser printing, optional automatic Edge output and direct Excel export.
- Editable project identity, company/operator defaults and a repeatable README template.
- README rebuilt with six real workbook section renders and two clearly labeled workflow illustrations.
- MIT License, copyright Kazi Shakib, and explicit third-party/runtime/development-tool notices.
- Disposable demo command, GitHub contribution templates and safe release packaging with checksums.

## Financial behavior

The accounting model is unchanged: 62-seat capacity; Tk 50 commission at commission counters; zero at own counters; separate per-trip/counter shortages and extra receipts. Operating expenses and net profit remain outside this model. Final reports keep the previous closed values while a correction is open.

## Existing users

Keep backups before adopting the new version. Save and close Excel before import. The SQLite schema remains version 1; the release does not automatically re-import or revise accounts. `project.json` affects branding and defaults, not historical financial records.

## Start

Run `launch.bat`, or `python control_panel.py`. For a fictional demonstration, run `python demo.py` in a clean project copy. Follow [PDF export](PDF_EXPORT.md), [customization](CUSTOMIZATION.md) and [GitHub setup](GITHUB_SETUP.md).

## Verification

See [delivery verification](DELIVERY_VERIFICATION.md) for final local test results and desktop/printing limitations. GitHub workflows are configured but have not been run remotely by this file-preparation task.
