# SmartBus 1.3.0 verification

Checked on October 16, 2026, using Python 3.12.14 on Windows. Earlier delivery verification files describe previous releases; this document covers the 1.3.0 upgrade.

## Automated checks

- Full unittest discovery: **138 tests passed** (130.942 seconds). A further 34 HTTP, profile and release boundary checks passed after tightening invalid repository-name validation.
- Ruff 0.17.0 formatting and code checks: passed.
- Python compilation: passed.
- Extracted panel JavaScript syntax check with Node: passed.
- UI structure check: no duplicate IDs or missing literal element references. No inline event handlers, inline style attributes or unsafe HTML insertion.
- Release builder checks ZIP integrity and each packaged file against its SHA-256 manifest. The final archive is built after this document and the research workbook are included.

The tests cover money precision and rounding, blank versus zero receipts, independent shortage/extra balances, workbook validation, frozen closed snapshots, corrections, restore safety, HTTP session/origin restrictions, insights filters, profile validation, schema duplicates, public-data provenance and chronological holdout isolation. The new multi-day demo checks preserve existing files and the original one-day behavior.

## Browser checks

Exercised an isolated 14-day fictional demonstration ledger from September 29 through October 12, 2026. The overview displayed 14 closed days, Tk 913,800 gross fare revenue, Tk 831,250 actual receipts, Tk 56,850 outstanding and 37.10% weighted occupancy.

Verified reporting-date controls, navigation, published insights, public dataset totals and forecast metrics. A 40-ticket scenario at Tk 500 with a commission counter returned Tk 20,000 gross, Tk 2,000 commission and Tk 18,000 due. Saving a customization persisted through a page reload in the separate demonstration folder.

Checked the desktop layout and a mobile viewport. At the mobile check, document width equalled viewport width (375 pixels), with the navigation scrolling within its own region. A screenshot of the fictional overview is delivered with the package.

## Public-data research

Downloaded the official CTA dataset through the City of Chicago API, inspected its publisher/schema/terms metadata, and retained the original CSV with its SHA-256 provenance manifest. The included snapshot has 6,972 route/date observations, 127 routes, 61 observed dates and 33,591,684 boardings.

Reproduced the summaries and fixed chronological backtest from the snapshot. Training ends November 23, 2025; the holdout is November 24–30. Both methods evaluate the same 769 records with zero exclusions. The route/daytype mean has MAE 1,291.45 rides per route/day, versus 1,026.95 for the last-observed baseline. The mean model underperformed in this holdout.

## Excel research artifact

The separate `research/SmartBus_Public_Data_Analysis.xlsx` retains all 6,972 source observations and 769 held-out prediction records. Its Python-produced predictions are labeled as imported inputs; Excel computes summaries, shares, averages, lookup results and prediction errors.

Artifact-tool recalculation reconciled total boardings, row/route/date counts and both MAEs with Python. Changing the route selector to route 1 returned 48,480 boardings; filtering that route to November returned 21,325. Controls were restored to the full snapshot. The final formula-error scan matched no errors. All five sheet previews were rendered and visually inspected. Native Excel charts, validation and frozen panes are included.

## Verification limits

R is not installed in this environment, so the optional R script was reviewed but not executed. Native Excel editing/recalculation and the desktop Print / Save as PDF dialog were not exercised. Workbook calculations were checked in the authoring engine; they are not a claim of installed-Excel validation. GitHub Actions configuration is included but has not run on GitHub here. No public deployment, GPS feed, payment integration or authenticated multi-user service is claimed.

The included financial data is fictional, and public Chicago ridership remains separate from SmartBus accounts. The repository upgrade is delivered locally as a GitHub-ready package; it has not been pushed to the original remote repository.
