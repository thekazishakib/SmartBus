# Version 1.2.0 delivery verification

Release date: 14 October 2026. This English-only release was verified on Windows in a restricted workspace.

## Automated results

Run from the project root:

```text
python -m unittest discover -s . -p "test_*.py" -v
python -m compileall -q .
```

**All 89 automated tests passed** in 64.328 seconds on Python 3.12.14. Python compilation and the generated panel JavaScript syntax check also passed. New checks cover printable report contents, closed-record consistency, secure HTML report serving, profile validation, README generation and release-data exclusion.

The language checks scan every retained workbook's XML, including chart caches, for Bengali characters. The rendered interface has no language selector and rejects unsupported language requests. The Dashboard, counter summary, Trips, Collections, Crew and Route List views were rendered and visually inspected with the spreadsheet artifact tool. Formula checks found no errors in the edited input/template workbooks. Existing charts and freeze panes were preserved.

Checks cover accounting, workbook validation, supported capacity, closed snapshots, workflow transitions, reason-required corrections, stable IDs, source drift, backup recovery, report metadata and local request handling. Release checks also inspect retained files for non-English interface/template/report content and obsolete documentation references.

The HTTP handler tests do not establish browser rendering or an end-to-end desktop session. The annual export check generates a 365-day Excel report and HTML content; it does not establish that Edge printed a PDF.

## Integration rehearsal

The English workflow rehearsal passed in a disposable project copy: import, review, close, backup, restore, closed-ledger Excel export and printable HTML generation. The regenerated Excel and printable HTML reports retained the expected totals below, with English sample names and permanent record IDs. The printable report includes a Print / Save as PDF button, and tests confirm it does not require the Edge engine to generate the HTML.

The fictional reference day has these expected values:

| Measure | Expected sample result |
| --- | ---: |
| Trips | 3 |
| Sold seats | 74 |
| Fare | Tk 70,600 |
| Commission | Tk 2,250 |
| Fare after commission | Tk 68,350 |
| Received deposits | Tk 49,450 |
| Outstanding | Tk 18,900 |

Blank receipt amounts must be resolved before review. Enter zero explicitly if nothing was received. All sample identities and amounts are fictional; they do not measure real operational impact.

The English closed-ledger sample report is [Demo_Professional_en.xlsx](Demo_Professional_en.xlsx). Its Trips sheet includes permanent record IDs and published revision numbers.

## Checks requiring a normal desktop session

- Excel desktop editing, recalculation, dropdown behavior, appearance and workbook save/close require verification in the target installation.
- The live browser layout and OS print dialog require verification in a normal desktop session. A local HTML preview attempt was blocked by the browser URL policy; no bypass was used. README workflow figures are labeled illustrations. Six actual workbook section previews and two original diagrams were inspected for readability.
- Actual Edge PDF printing is not established by unit tests. The earlier restricted-workspace attempt exited with `0xC0000005`, produced no PDF and reported access-denied diagnostics. PDF printing needs verification on the target computer; automated tests cover failure and timeout handling.
- GitHub Actions is configured for Python 3.11 and 3.13 on Windows and Ubuntu. Configuration does not establish that remote jobs have run.
- Optional R execution requires separate verification.

Use the [operating guide](PROFESSIONAL_GUIDE.md) to rehearse one complete day in a disposable copy before adopting real accounts.

## Release contents

The release includes MIT-licensed original source/documentation, an English workbook template, fictional input, closed-ledger Excel/HTML examples and separate section previews. It uses system fonts and bundles no font files. Live ledgers, backups, generated working reports, caches and temporary profiles are excluded. `RELEASE_MANIFEST.json` records SHA-256 hashes for the packaged files other than the manifest itself.
