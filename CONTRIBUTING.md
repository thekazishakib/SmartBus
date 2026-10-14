# Contributing to SmartBus

Use Python 3.11 or later. The application and tests use the standard library; Microsoft Excel and Edge are external Windows requirements for the operator workflow. Develop with fictional data and a disposable ledger.

## Run checks

From the project root:

```text
python -m unittest discover -s . -p "test_*.py" -v
python -m compileall -q .
```

GitHub Actions runs unittest on Ubuntu and Windows with Python 3.11 and 3.13. CI does not operate Excel desktop or Edge printing. For workbook, report-layout or launcher changes, describe manual checks and anything unverified.

## Accounting changes

Explain financial behavior before changing calculations. Use decimal money values. Keep counter shortages and surpluses separate. Do not label fare less commission as net profit. Changing the fixed commission rule requires updated documentation and tests.

Import, closure, correction and storage changes must preserve these guarantees:

- Master-list or source edits cannot rewrite closed snapshots.
- Corrections require a reason; previous closed records remain authoritative until replacement closure.
- Reimport cannot double-count accepted records.
- Stable trip identities survive matching revision imports.
- Blank deposits are distinct from declared zero deposits.
- Invalid or overflowing input cannot disappear silently from a complete-looking report.
- Source workbook mutation preserves a recovery copy and freezes identifiers consistently.
- Restore validates the selected backup and protects the current ledger before replacement.

Add regression tests for financial defects, state transitions and recovery behavior. Prefer tests of user-visible guarantees to tests that repeat implementation details. Describe storage migration implications in release notes.

## Changes and reviews

Keep each change focused. State the trigger, expected result and validation. Update `docs/PROFESSIONAL_GUIDE.md` when behavior changes. Keep all interface text, workbook labels, reports, examples and documentation in English. Daily workbooks use `Daily_YYYY-MM-DD_en.xlsx`. Use system fonts and do not add a separate font installation requirement.

Before publishing, inspect the staged file list. Do not commit real business or personal records, local databases, backups, generated reports, credentials, caches or Office lock files. Use fictional reproductions.

## License

Contributions to original project material are made under the MIT License. Preserve applicable third-party licenses and attribution if dependencies or assets are added.

