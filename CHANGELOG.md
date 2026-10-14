# Changelog

## 1.2.0 - 2026-10-14

- Added browser-printable reports with Print / Save as PDF and an export guide.
- Added editable project identity, company/operator defaults and README generation.
- Reworked README with separate section previews and author attribution.
- Added MIT License, third-party notices, demo command and GitHub release packaging.


## 1.1.0 — 2026-10-13

### Changed

- Made the control panel, workbook templates, example records and generated reports English only.
- Standardized daily filenames as `Daily_YYYY-MM-DD_en.xlsx`.
- Switched to system fonts so no separate font installation is required.
- Replaced obsolete guides and examples with the current operating guide, release notes, finance case study, delivery verification and English closed-ledger Excel example.
- Preserved daily review and closure, financial snapshots, corrections, audit history and backup recovery.

## 1.0.0 — 2026-10-13

### Added

- Local SQLite ledger with draft, reviewed and closed daily revision states.
- Closed snapshots so later workbook and master-list edits do not alter accepted reports.
- Reason-required correction revisions while the previous closure remains authoritative until replacement closure.
- Stable trip UUIDs across matching revisions, local actor labels and audit-event history.
- Atomic source-workbook freezing of imported identifiers and lookups with a source backup.
- Versioned ledger backups and integrity checks during restoration.
- Current operating guide, finance case study, release notes and contributor guidance.
- Command-line ledger operations and a browser-free panel startup option.

### Fixed

- Input outside the supported 100-trip and 500-collection daily capacity now fails visibly.
- Workbook preview excludes dated files outside the requested period before parsing.
- Malformed in-range workbooks produce errors instead of incomplete totals.
- Blank deposits require explicit resolution before review; zero remains a valid declared deposit.

### Retained

- Excel input, period Excel export and Windows PDF export.
- Decimal arithmetic, independent counter settlement and fixed Tk 50 commission rules.
- Demonstration workbooks and reference documents from the earlier package.

### Scope

This is a single-computer application. Actor labels are not authentication, and application closure does not prevent database-file owners from changing data. Reports do not calculate operating expenses or net profit. The professional guide is canonical.

## GitHub preparation — 2026-10-13 (earlier package)

- Prepared the earlier repository package with guides, demos and daily templates.
- Added ignore rules, attributes and a GitHub Actions test matrix.
- Preserved the existing workbook theme and accounting behavior.
- Documented local acceptance checks and known workflow limits.
- That package did not create or upload a remote repository.

