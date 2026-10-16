# Learning path for explaining and extending SmartBus

Work through the topics in order and apply each one to a visible project change. These are learning resources, not admission requirements or a promise of admission. Official pages were checked on October 16, 2026.

| Order | Resource | What to learn | Evidence to add to this project |
| --- | --- | --- | --- |
| 1 | [Harvard CS50's Introduction to Programming with Python](https://cs50.harvard.edu/python/) | Functions, exceptions, file I/O, unit testing, regular expressions, classes | Explain `ridership.py`; add a validated import and tests without copying a solution you cannot explain |
| 2 | [Microsoft Excel help and learning](https://support.microsoft.com/en-us/excel) | Excel Tables, data validation, SUMIFS, COUNTIFS, lookups, charts, Power Query and PivotTables | Reproduce a route total, change a dashboard filter and document an Excel CSV refresh |
| 3 | [Harvard CS50's Introduction to Databases with SQL](https://cs50.harvard.edu/sql/) | Keys, joins, constraints, transactions, indexes and database design | Draw the existing ledger schema and explain why published revisions remain authoritative |
| 4 | [R for Data Science, second edition](https://r4ds.hadley.nz/) | Data import, transformation, visualization, exploratory analysis and reproducibility | Run the optional R analysis and compare its MAE with the Python result. This is an online book; SmartBus itself uses base R |

## A practical eight-week sequence

1. **Weeks 1–2: Python and Git.** Run the demo. Trace one Excel input through validation, Decimal calculations and a report. Make a small change, write a test and commit it with a clear message.
2. **Weeks 3–4: Excel.** Explain the daily workbook's lookup, validation and reconciliation formulas. In the research workbook, use the period and route filters, check a total independently and create a PivotTable yourself from the raw source Table.
3. **Weeks 5–6: SQL and testing.** Study imports, review, closure and correction revisions. Demonstrate that changing the original Excel file does not rewrite a closed report. Explain blank receipts versus explicit zero.
4. **Week 7: Research.** Reproduce the public snapshot analysis. Explain chronological train/test separation, mean absolute error, the common evaluation population and why the more complex method underperformed the baseline.
5. **Week 8: Presentation.** Record a short walkthrough. Describe the problem, your contribution, one defect you fixed, the tests, the real research result and what you would investigate next.

## Questions you should be able to answer

- Why is money calculated with `Decimal`, and where is rounding applied?
- Why can one counter's extra receipt not erase another counter's shortage?
- What is the difference between an unrecorded date, a closed empty day and a day with zero receipts?
- Which data is fictional, which is official public data, and which values are predictions?
- What would data leakage do to a forecast evaluation?
- Why is ridership not enough to infer occupancy, ticket revenue or net profit?
- Which parts did you design, test or extend yourself? Which used external tools or coding assistance?

Keep your portfolio claims specific and accurate. Retain Kazi Shakib's authorship, CTA attribution and the development-assistance notice. Your strongest evidence is a working project you understand and can modify.
