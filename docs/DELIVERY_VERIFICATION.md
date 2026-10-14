# Version 1.2.1 delivery verification

Release date: 14 October 2026. This English-only maintenance release was prepared on Windows in a restricted workspace.

## Automated results

**All 106 tests passed** in the final run (65.137 seconds) on Python 3.12.14. Ruff 0.17.0 formatting and lint checks, Python compilation, and syntax checks of the generated panel and printable-report JavaScript also passed.

The full suite passed after each refactoring stage:

| Stage | Passing tests | Duration |
| --- | ---: | ---: |
| Baseline before edits | 89 | 67.859 s |
| Formatting and lint cleanup | 89 | 65.210 s |
| Normalization names and marker validation | 90 | 60.090 s |
| Dead-code cleanup and compatibility checks | 92 | 62.194 s |
| Shared helper extraction | 100 | 83.137 s |
| Portable file opener | 106 | 82.672 s |
| Final release changes | 106 | 65.137 s |

```text
python -m pip install -r requirements-dev.txt
ruff format --check .
ruff check .
python -m unittest discover -s . -p "test_*.py" -v
python -m compileall -q .
```

Refactoring checks must cover monetary totals, blank versus explicit-zero receipts, workbook marker validation, closed snapshots and corrections, backup recovery, report compatibility and file-opening success/failure behavior. Platform-helper unit tests exercise command selection and error handling using controlled subprocess/OS behavior; they do not establish that native desktop launchers ran.

## Integration and release checks

A disposable demo passed import, review, close, backup, restore, period Excel export and printable HTML generation. The report and its CSV/JSON sidecars use the `SmartBus_` prefix, and source metadata identifies version 1.2.1. The Excel report retains the expected fare and receipt totals. The full calculated fictional-day account matches version 1.2.0, including compatibility fields. Independent comparison also found equivalent HTML content and period-export cell maps after the formatting cleanup.

All retained workbook fixtures are byte-for-byte unchanged. ZIP integrity and XML parsing checks passed for those fixtures and the newly generated period workbook. Documentation links were checked, with README-template paths resolved relative to the generated root README.

The release builder checks ZIP integrity, each manifest file hash, and the archive's SHA-256 checksum. Final archive inspection verifies the new modules and development files are included while Ruff caches and working accounts are excluded.

The fictional reference day should retain these values:

| Measure | Expected sample result |
| --- | ---: |
| Trips | 3 |
| Sold seats | 74 |
| Fare | Tk 70,600 |
| Commission | Tk 2,250 |
| Fare after commission | Tk 68,350 |
| Received deposits | Tk 49,450 |
| Outstanding | Tk 18,900 |

All example identities and amounts are fictional. Retained README workbook previews and workflow illustrations were prepared for version 1.2.0; their inclusion does not establish a new desktop rendering check for version 1.2.1.

## Checks requiring the target environment

- Native Windows, macOS `open` and Linux `xdg-open` launching have not been exercised for this release; platform-selection and failure-handling tests use controlled OS/subprocess behavior.
- Excel desktop editing, recalculation, dropdowns, workbook save/close and appearance require verification in the target installation.
- Live browser layout and the OS print dialog require a normal desktop session. Workflow diagrams are illustrations, not live browser screenshots.
- Actual Edge PDF rendering has not been verified for this release. Printable HTML and automatic-PDF error handling can be checked independently of native PDF printing.
- Optional R execution and the resulting PDF charts have not been verified locally.
- GitHub workflows are configured for Windows and Ubuntu with Python 3.11 and 3.13. Configuration does not establish that remote jobs ran.
- LibreOffice conversion is not part of this release's CI checks.

Use the [operating guide](PROFESSIONAL_GUIDE.md) to rehearse a complete fictional day before adopting real accounts.

## Release contents

The release includes MIT-licensed original source/documentation, English workbook templates, fictional inputs, example reports and separate section previews. Ruff is declared as a development dependency but is not bundled. Live ledgers, backups, private generated reports, caches and virtual environments must be excluded. `RELEASE_MANIFEST.json` records SHA-256 hashes for packaged files other than the manifest itself.
