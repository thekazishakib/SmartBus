# Final GitHub package verification

Prepared on 14 October 2026 for SmartBus 1.2.1. This is a local distribution check, not confirmation that a GitHub repository or release has been published.

## Finalization scope

The final package adds clearer AI-assistance and learning-context wording, a practical owner guide, browser-upload instructions and this verification record. Application Python sources, the launcher, optional R script and all Excel fixtures were compared with the supplied SmartBus 1.2.1 folder and are byte-for-byte unchanged. The application version remains 1.2.1. README was regenerated from its editable template.

## Fresh checks

| Check | Result |
| --- | --- |
| Full automated suite, Windows, Python 3.12.14 | 106 tests passed in 62.198 seconds |
| Ruff 0.17.0 formatting | 40 Python files already formatted |
| Ruff lint | All checks passed |
| Python compilation | Passed |
| Disposable fictional demo | Import, review, close, period Excel and printable HTML generation passed |
| Closed ledger totals | Fare 70,600; commission 2,250; after commission 68,350; deposits 49,450; outstanding 18,900 Tk |
| Demo backup and restore | Published trip data preserved |
| Generated Excel | ZIP integrity and all XML parsing passed |

The final ZIP is built with `tools/package_release.py`, which checks archive integrity and every manifest file hash and writes a SHA-256 sidecar. Final archive inspection checks that only publication files are included, local relative documentation links resolve and the source/workflow files are present. Live data, working accounts, backups and generated demo results are excluded; packaged sample workbooks and reports are fictional fixtures.

## Limits

No GitHub push, remote CI run, tag or release was performed during this preparation. Excel desktop editing/recalculation, native file launch behavior, the live panel's visual layout, print dialog, actual Edge PDF output and optional R execution were not freshly verified. Automated tests include simulated platform/PDF behavior; those tests do not replace target-desktop acceptance. Retained images are existing workbook previews and labeled workflow illustrations.

The application is a single-workstation revenue-reconciliation tool. It does not calculate operating profit, authenticate reviewers or provide tamper-proof storage. Fixed 62-seat capacity and Tk 50/zero commission rules need to match any proposed use. No real-company deployment, adoption or time saving is established by this package.

See [operating instructions](PROFESSIONAL_GUIDE.md), [publishing instructions](GITHUB_SETUP.md), [owner learning guide](OWNER_GUIDE.md) and the earlier [release verification](DELIVERY_VERIFICATION.md).
