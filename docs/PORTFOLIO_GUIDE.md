# SmartBus undergraduate portfolio and learning guide

SmartBus combines an Excel and Python revenue-reconciliation application with a reproducible public bus-ridership study. This guide explains how to demonstrate the delivered work, understand the analysis, and develop evidence of your own contribution. It does not establish admission suitability, live deployment, or completed personal learning.

## A focused project question

The operating question is: **How can a bus operator reconcile ticket sales against counter receipts while preserving accepted historical accounts?** The research question is: **Does a historical route/daytype mean predict held-out daily ridership better than the last observed value for that route?**

These questions give the project a clear purpose. The accounting workflow demonstrates data controls; the research workflow demonstrates source evaluation, validation, forecasting and honest measurement. Excel supports visible inputs and analysis, while Python makes the calculations and exports reproducible.

## What to demonstrate

| Area | Delivered capability | Evidence to show |
| --- | --- | --- |
| Excel operations | Daily input templates, master lists, calculations and report exports | Enter one fictional trip, trace the formulas, and identify input validation |
| Python accounting | Decimal money calculations, independent counter balances and explicit unknown receipts | Explain the Tk 50 commission rule and a shortage/overpayment example |
| Historical records | Import, review, close, reasoned corrections and SQLite snapshots | Show that an open correction retains the last closed revision in final reports |
| Local dashboard | Closed-record insights and editable project identity | Explain the selected reporting dates and the authority of closed snapshots |
| Planning | Hypothetical seat/fare/counter-type scenarios | Change an assumption and explain that the result is a scenario, not a transaction |
| Public-data research | Official CTA extract, source manifest, checksums, summaries and chronological backtest | Reproduce the benchmark and show coverage, dates and MAE |
| Advanced Excel analysis | A separate public-ridership workbook with formulas and charts | Inspect its source/assumption notes and verify one summary against the CSV |
| Optional R | Independent CSV summaries, charts and forecast comparison using base R | Run the supplied script after installing R and compare common-record MAE with Python |

For interface operation, use the [operating guide](PROFESSIONAL_GUIDE.md). The release verification document records which automated checks and desktop steps were actually exercised; a feature's presence is not proof of every desktop workflow.

## Keep the two datasets distinct

**The financial example is fictional.** Its trips, Tk fares, counter receipts, staff and capacity illustrate SmartBus rules. A fictional example establishes calculation behavior, not operator adoption or a business outcome.

**The research input is public Chicago data.** The included snapshot comes from the Chicago Transit Authority / City of Chicago dataset [CTA — Ridership — Bus Routes — Daily Totals by Route](https://data.cityofchicago.org/Transportation/CTA-Ridership-Bus-Routes-Daily-Totals-by-Route/jyb9-n7fm). It covers **2025-10-01 through 2025-11-30**, with **6,972 observed route/date records, 127 routes, 61 dates and 33,591,684 rides/boardings** in the initial snapshot. The [source manifest](../research/source.json) records the requested period, retrieval details, API queries, publisher, terms link and CSV SHA-256 checksum. Recheck this manifest after any refresh; the bundled snapshot is a historical extract, not a live feed.

The source grain is one observed route on one date. `rides` means rides/boardings, not unique people. The provider's daytypes are `W` for weekday, `A` for Saturday, and `U` for Sunday/holiday. The raw CSV retains the API's midnight timestamps; the analysis accepts these and normalizes dates for grouping. Route identifiers remain text.

CTA records contain no SmartBus Tk fares, sold seats, receipts, commissions or vehicle capacity. They cannot establish Bangladesh route demand, local occupancy or financial revenue. The public research benchmark is never imported as company financial accounts. Public data remains subject to the publisher's terms; the repository's MIT license covers project code, not a new license for the external dataset.

## Research method you should be able to explain

1. **Validate input.** Require `route`, `date`, `daytype` and `rides`; reject malformed dates, unsupported daytypes, negative or fractional ride counts, and duplicate route/date records. Enforce the documented size and date bounds.
2. **Describe observed coverage.** Report the number of recorded dates, routes and route/date rows. Sum only recorded observations. A missing record does not prove that a route operated zero rides.
3. **Split chronologically.** Reserve the final seven distinct observed dates for evaluation. In the included snapshot, training ends on **2025-11-23** and the holdout is **2025-11-24 through 2025-11-30**. Keep all training observations strictly before the holdout.
4. **Build an interpretable forecast.** For each held-out route/date, use the training-only arithmetic mean for the same route and provider daytype. Do not update it with held-out outcomes.
5. **Compare a simple baseline.** Use each route's last observed training ride count for every held-out date. This is also fixed at the cutoff.
6. **Measure the same records.** Compare forecasts only where both methods have training history. Report excluded holdout records instead of silently treating new routes or unseen route/daytype pairs as zero.
7. **Report MAE.** Mean absolute error is the average absolute difference between predicted and observed rides per route/day. Lower is better for this holdout. Calculate errors before presentation rounding.

For example, a predicted 1,100 rides against 1,000 observed rides contributes an absolute error of 100 rides. This example explains MAE and is not a measured record from the included dataset.

The [benchmark JSON](../research/benchmark.json) is the source for the measured results. On the included snapshot, **769 holdout route/date records** were evaluated with **0 exclusions**. The route/daytype mean's MAE was **1,291.45 rides per route/day**, versus **1,026.95** for the last-observed baseline. The mean model therefore **underperformed the baseline** on this holdout, with about **25.76% higher MAE**. This result motivates investigation; it does not demonstrate a successful forecast improvement. The Python prediction CSV contains eligible holdout records; the benchmark reports total exclusions. The optional R output also lists excluded rows with reasons, making coverage easy to inspect.

This is a short, fixed-holdout baseline study. It does not model weather, service frequency, school calendars, disruptions or long-term trend. The `U` category combines Sunday and holiday behavior; a mean for this category may miss specific holiday effects. A model that wins one week may fail in another. Aggregated daily totals also depend on the routes present in the extract. Compare coverage before interpreting changes as system demand growth.

## Reproduce the project

Run these commands from the extracted project folder using Python 3.11 or newer. The operating application and Python research analysis use the standard library.

```text
python demo.py --folder portfolio_demo --days 14
python control_panel.py --root portfolio_demo
python ridership.py analyze --folder research
```

Choose a fresh demo folder when `portfolio_demo` already contains work. The demo uses fictional data and prepares a separate closed ledger. Follow the paths printed by the command to open its reports. `--root portfolio_demo` opens that separate ledger; omitting `--root` uses the project's own working ledger. On Windows, `launch_demo.bat` prepares and opens a 14-day fictional demonstration automatically.

The included research snapshot can be analyzed offline. To download another bounded public extract and preserve the original, use a new destination:

```text
python ridership.py download --start 2025-10-01 --end 2025-11-30 --destination research_refresh
```

Network access is needed for download. Review the new source manifest, observed coverage and holdout dates before replacing the included research. The provider can revise historical records; a later download may differ. Preserve the old checksum if comparing results across versions.

Open [SmartBus_Public_Data_Analysis.xlsx](../research/SmartBus_Public_Data_Analysis.xlsx) for the separate Excel research artifact. Inspect source notes and trace at least one formula against the raw CSV. The Python analysis command reproduces the benchmark and CSV summaries; this standalone workbook is a snapshot and has no one-click regeneration command.

For a new snapshot, reproduce the CSV analysis, import the refreshed CSV into the **Source data** table in a copy of the research workbook, and update date/route lists and summary ranges as needed. Refresh the imported predictions on **Forecast evaluation** from `forecast_predictions.csv`. Those predictions are computed by Python; changing source cells in Excel does not retrain them. Check the source notes, training dates, holdout dates, row counts and formulas after refresh before presenting the workbook as current.

R is optional and is installed separately. The script uses base R, selects a Cairo PDF device when available, and falls back to the standard PDF device.

```text
Rscript analyze.R --ridership research/cta_ridership.csv analysis/cta
Rscript analyze.R reports/YOUR_REPORT_trips.csv analysis/accounts
```

Replace `YOUR_REPORT_trips.csv` with an actual report CSV path. The historical trips mode remains available and looks for the matching `_counters.csv` export. Its route seat use is `sum(seats) / sum(capacity)`, not an unweighted average of trip percentages. Unknown receipt counts remain visible; partial known receipts do not establish full settlement.

The R ridership mode writes daily, route, calendar-weekday and provider-daytype summaries, holdout predictions, forecast metrics, methodology notes and a PDF with charts. Its files use the `ridership_` prefix. Calendar weekday and provider daytype are different groupings because holidays can occur on weekdays. Weekday means are means over recorded route/day rows, not system-wide daily averages. Compare R and Python MAE to rounding tolerance and compare their evaluation coverage before interpreting differences.

R execution is a separate acceptance step; do not claim it has run solely because the script is included. Similarly, workbook generation and structural checks do not establish successful editing or recalculation in your installed Excel.

## A five-minute project presentation

1. **Problem — 30 seconds.** Explain ticket revenue, commission, receipts and why accepted accounts need stable history.
2. **Excel and Python — 90 seconds.** Trace one fictional record. Explain blank versus zero receipts, independent counter balances and the review/close workflow.
3. **Analysis — 90 seconds.** Show the public data source and checksum. Explain the chronological split, mean forecast, baseline, MAE and excluded records.
4. **Customization — 30 seconds.** Show one project identity change and one clearly labeled planning scenario.
5. **Your contribution and next experiment — 60 seconds.** Identify a decision you made, a change you can explain, its verification evidence and an unresolved limitation.

Be prepared to explain why future observations cannot be used to train a forecast evaluated on earlier dates. Also explain why a counter overpayment must not conceal another counter's shortage, and why daily boardings cannot directly give seat occupancy.

## Personal contribution and authorship

Kazi Shakib directs the project. This upgrade includes implementation, debugging, analysis and documentation assistance from ChatGPT/Codex. Record the decisions, changes and verification you personally understand and perform. Do not imply that generated code, public source data or an unperformed experiment is entirely your independent work.

Use a contribution journal with these fields:

| Date | Question | My decision/change | AI or other assistance | Evidence checked | Result and limitation |
| --- | --- | --- | --- | --- | --- |
| Your actual date | The issue you investigated | What you personally changed or chose | The support actually used | A command, screenshot, calculation or reviewer note | What the evidence supports and what remains uncertain |

Suggested portfolio paragraph **to adapt only after understanding and demonstrating the work**:

> I directed SmartBus, a Python and Excel project for bus-revenue reconciliation, with implementation support from ChatGPT/Codex. The application validates daily trip and counter inputs, preserves reviewed closed records, and exports reports. A separate study uses official Chicago CTA daily bus-ridership data to compare an interpretable forecast with a training-only baseline on a chronological holdout. My personal contributions were [specific decisions or changes], which I verified through [specific evidence].

Replace the bracketed text with real work before using the paragraph. Add measured outcomes only when you can show the underlying evidence. Do not claim real-company adoption, money saved, reduced error rates or an admissions outcome from demonstration data.

## Learning map: Python and advanced Excel first

These are study topics and practical checkpoints, not completed courses or certificates. Use the [learning path](LEARNING_PATH.md) for verified course links and a proposed eight-week schedule.

| Stage | What to study | SmartBus exercise that demonstrates understanding |
| --- | --- | --- |
| 1. Python foundations | Variables, strings, lists, dictionaries, loops, functions, imports and command-line arguments | Explain one trip dictionary and trace its values through a report |
| 2. Reliable calculations | `Decimal`, rounding, exceptions, input validation and file paths | Reconcile a fictional commission counter by hand and explain blank versus zero |
| 3. Excel foundations | Tables, absolute/relative references, named inputs, data validation, number formats and conditional formatting | Identify inputs and formulas, then deliberately enter an invalid value in a disposable copy |
| 4. Advanced Excel analysis | `SUMIFS`, `COUNTIFS`, `AVERAGEIFS`, `IFERROR`, lookups, PivotTables, charts and scenario inputs | Independently summarize one route/date range and compare it with Python output |
| 5. Data preparation | CSV encodings, text identifiers, date parsing, missing data, duplicate keys, Power Query refresh and source attribution | Explain why routes stay text and why missing route-days are not zero-filled |
| 6. Statistics and forecasting | Group means, variation, chronological validation, leakage, baseline comparison, MAE and coverage | Calculate several held-out errors by hand and justify the evaluation split |
| 7. SQLite and testing | Tables, keys, queries, transactions, snapshots, unit tests and regression checks | Explain draft/review/close and run a meaningful correction test |
| 8. Optional R | Data frames, `aggregate`, date handling, grouping, plotting and independent calculation checks | Run both analysis modes and compare public-research coverage and MAE with Python |
| 9. Communication and Git | Commits, diffs, source documentation, limitations, evidence and concise demonstrations | Publish a change you understand with a clear problem statement and actual verification |

An effective sequence is Python foundations and Excel controls first, data preparation and statistics next, then SQLite, testing and optional R. Understanding a small, well-verified contribution is more useful than listing technologies you cannot yet explain.

## Practical learning checkpoints

- Trace the fictional three-trip example and record the accounting arithmetic yourself.
- Demonstrate Excel validation using a blank receipt, explicit zero, shortage and overpayment.
- Reproduce the public-data analysis and document source, grain, dates, missingness and checksum.
- Recreate one route summary in Excel and calculate several holdout errors by hand.
- Implement one small extension you can explain, verify its behavior, and keep a dated before/after record.
- Rehearse the demonstration, collect teacher or peer feedback, and resolve a concrete issue.

Follow the schedule in the [learning path](LEARNING_PATH.md) at a pace that fits your prior knowledge and actual deadline. Maintain dated evidence as you progress instead of marking tasks complete in advance.

## Extensions after the baseline

| Priority | Extension | Evidence required before claiming success |
| --- | --- | --- |
| Next | Rolling chronological backtests over several months | Per-period MAE and coverage, consistent baseline and no future leakage |
| Next | Power Query refresh into a separate research workbook | Documented source refresh, duplicate validation and a before/after checksum |
| Next | Replace fictional routes with authorized local data | Source permission, field definitions, quality checks and an independently reconciled sample |
| Later | Service/calendar or weather features | Reliable aligned sources, leakage checks and measurable improvement over the baseline |
| Later | Browser transaction entry | Validation parity with Excel and safe import/review/close behavior |
| Later | Expense and profit reporting | Explicit expense definitions and new accounting rules tested against independent examples |
| Later | Multiple users or public deployment | Authentication, authorization, secure hosting, concurrency and recovery design |

Keep the working finance rules stable while experimenting in the research and planning areas. Branding settings do not change capacity, commission or accepted historical transactions. Broader capabilities belong in staged, verified changes with updated documentation.
