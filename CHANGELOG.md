# Changelog

## 1.3.0 - 2026-10-16

- Added a professional local dashboard with closed-record insights, weighted occupancy, route trends and separate counter outstanding/extra receipts.
- Added hypothetical seat/fare/counter-type planning and validated branding controls. Planning inputs do not alter accepted transactions or fixed financial rules.
- Added reproducible official CTA public-ridership research, a historical two-month snapshot, provenance/checksum manifest, summaries and a chronological holdout comparison with a last-observed baseline.
- Added a separate advanced Excel public-data analysis workbook with source notes and measured forecast results. The historical route/daytype mean underperformed the baseline on the included holdout; no forecasting improvement or financial outcome is claimed.
- Extended the optional base-R script with strict ridership validation, chronological forecasts, coverage/exclusion reporting, weekday/daytype summaries and chart output; retained financial trips CSV analysis and added unknown-receipt counts.
- Added an undergraduate portfolio guide with Python/Excel learning topics, reproducible commands, an adaptable authorship statement, evidence exercises and staged extensions.
- Added a deterministic 1–31 day fictional demo, isolated-workspace launch support, source/schema documentation and Windows/Linux verification workflows. Release packaging excludes daily records, private reports and analysis outputs even inside nested workspaces.
- Retained the fictional financial demonstration, Decimal accounting, review/close workflow, accepted closed snapshots and single-workstation scope. Public Chicago boardings are separate from company accounts and are not evidence of Bangladesh operating demand.

## 1.2.1 - 2026-10-14

- Final distribution preparation: clarified AI assistance and the owner's learning context, added an owner guide and browser publishing instructions, and recorded fresh final-package checks. Application code and workbook fixtures remain unchanged in this preparation.

- Formatted Python code with Ruff and added pinned development requirements plus CI formatting/lint checks.
- Renamed input normalization to `normalize_inputs`, removed the internal `COMPANY_V4` handshake and clarified workbook-format errors while retaining `AUTO_V6`.
- Removed unused collection fee/cost inputs and zero-expense arithmetic; retained the report/snapshot output schema for existing records.
- Extracted shared value/date and workbook-reading helpers into `values.py` and `xlsx_io.py`, removing the accounting module's circular dependency.
- Added OS-aware file/folder opening with a saved-path response when desktop launching fails.
- Renamed newly generated `HeadCounter_` report filenames to `SmartBus_` and changed optional R chart text to the system sans-serif font.
- Kept the ledger schema, closed snapshots, fixed capacity/commission rules and standard-library runtime unchanged.


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
