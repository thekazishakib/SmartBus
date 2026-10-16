<p align="center"><img src="assets/logo.svg" width="92" alt="{{PROJECT_NAME}} logo"></p>

<h1 align="center">{{PROJECT_NAME}}</h1>

<p align="center">{{TAGLINE}}</p>

<p align="center"><strong>Version {{VERSION}} · Python 3.11+ · Excel · Local workstation · MIT License</strong></p>

<p align="center"><a href="docs/PORTFOLIO_GUIDE.md">Portfolio and learning guide</a> · <a href="docs/PROFESSIONAL_GUIDE.md">Operating guide</a> · <a href="docs/CUSTOMIZATION.md">Customize</a> · <a href="docs/PDF_EXPORT.md">Export to PDF</a></p>

## Project overview

{{PROJECT_NAME}} is a practical finance automation project for daily bus trips and counter accounts. It connects trip records with ticket sales, commission, deposits and outstanding balances, then preserves reviewed results in a local ledger.

The project uses Excel for familiar daily data entry, Python for accounting and reporting, SQLite for versioned records, and a small HTML/CSS/JavaScript control panel for the operator workflow. It runs on one computer and does not need an online account or a cloud database.

For an undergraduate portfolio, a separate public-data research area adds official CTA ridership analysis, a chronological forecast comparison and an advanced Excel analysis workbook. The public Chicago data demonstrates a reproducible research method; the financial example uses fictional Tk accounts. Python and Excel are the core learning path, with R available as an optional independent analysis.

**Created and maintained by [{{AUTHOR}}](https://github.com/{{GITHUB_USERNAME}}).**

## Main features

- **Daily workbooks:** create one English Excel file for each business date; carry forward buses, staff, routes, fares and counters.
- **Trip records:** coach, departure, route, bus, driver, guide, conductor, capacity and sold seats.
- **Counter accounting:** reconcile each trip and counter separately; calculate fixed commission and retain shortages and extra receipts separately.
- **Reviewed daily accounts:** import, review and close a day, with checks for incomplete or invalid data.
- **Historical protection:** final reports read closed ledger revisions; later master-list edits do not silently rewrite accepted accounts.
- **Reasoned corrections:** keep the old closed revision until a replacement has been imported, reviewed and closed.
- **Report exports:** date-range Excel reports and a browser-printable report with a **Print / Save as PDF** button. Automatic Edge PDF export is also available.
- **Recovery and traceability:** source backups, verified ledger backups, restore, stable trip IDs and local audit events.
- **Closed-record insights:** reporting-date filters, route trends, weighted occupancy and separate counter shortages/extra receipts from authoritative closed snapshots.
- **Planning scenarios:** vary seats, fare and counter type to explore hypothetical revenue and commission without creating financial transactions.
- **Public-data research:** official CTA snapshot, source/checksum manifest, reproducible Python summaries and a training-only forecast baseline comparison.
- **Advanced Excel analysis:** a separate public-ridership workbook with formulas, charts, source notes and evaluation results.
- **Editable branding:** validated Customize controls for supported `project.json` settings, plus an editable README template.
- **Reproducible demonstration:** prepare 1–31 fictional closed days, including a 14-day showcase, without overwriting existing records.

See the [architecture and data dictionary](docs/ARCHITECTURE.md), [verification record](docs/VALIDATION_1.3.md) and [learning path](docs/LEARNING_PATH.md).

### Local operations workstation

Actual browser capture of the 14-day fictional demonstration. Closed financial records, route/counter comparisons, planning, public-data research, recovery and customization share the local panel.

![SmartBus local operations workstation](assets/09-workstation.jpg)

## Public-data research and learning

The included [CTA research snapshot](research/cta_ridership.csv) covers **2025-10-01 to 2025-11-30**: **6,972 observed route/date rows, 127 routes, 61 dates and 33,591,684 rides/boardings**. Source: [Chicago Transit Authority / City of Chicago Data Portal](https://data.cityofchicago.org/Transportation/CTA-Ridership-Bus-Routes-Daily-Totals-by-Route/jyb9-n7fm). The [source manifest](research/source.json) records retrieval details, query and checksum; external data retains the publisher's terms.

The final seven observed dates are held out: **2025-11-24 to 2025-11-30**. Training ends on **2025-11-23**. A historical mean for each route/daytype is compared with the last observed training value for that route, using the same **769** eligible records with **0** exclusions. The mean model's MAE is **1,291.45 rides per route/day**, versus **1,026.95** for the baseline; it **underperformed the baseline** in this holdout. Both forecasts use training records only.

This result is a useful starting point for investigating better methods, not evidence of improved demand forecasting. The dataset provides boardings, not seat capacity, GPS, fares, receipts or Bangladesh operations. Missing route-days are not filled with zero. One short backtest does not establish future accuracy.

Reproduce the Python results offline:

```text
python ridership.py analyze --folder research
```

Inspect the [benchmark](research/benchmark.json), [daily summary](research/daily_summary.csv), [route summary](research/route_summary.csv), [predictions](research/forecast_predictions.csv) and [Excel analysis workbook](research/SmartBus_Public_Data_Analysis.xlsx). The workbook is separate from financial entry templates; its notes explain formulas and assumptions.

To download a new public snapshot while preserving the bundled data:

```text
python ridership.py download --start 2025-10-01 --end 2025-11-30 --destination research_refresh
```

Optional independent analysis after installing R:

```text
Rscript analyze.R --ridership research/cta_ridership.csv analysis/cta
Rscript analyze.R reports/YOUR_REPORT_trips.csv analysis/accounts
```

Replace `YOUR_REPORT_trips.csv` with a real report-export filename. R generates summaries, evaluation details and PDF charts. R is optional and separately installed; inclusion of the script does not establish that it ran on your computer. See the [portfolio guide](docs/PORTFOLIO_GUIDE.md) for methodology, evidence, an honest presentation template and staged extensions, and the [learning path](docs/LEARNING_PATH.md) for courses and a proposed schedule.

## Preview, part by part

All values below are fictional demonstration data. Workbook images are renders of the actual Excel example. Workflow diagrams explain the controls; they are not live browser screenshots.

### 1. Daily financial dashboard

Trips, sold seats, fare, commission, deposits and outstanding for the sample day.

![Daily financial dashboard](assets/01-dashboard.png)

### 2. Counter performance and outstanding

Counter sales share and individual balances. A surplus at one counter does not clear another counter's shortage.

![Counter totals and charts](assets/02-counter-summary.png)

### 3. Trip records

Coach, departure, route, direction, bus and driver assignments stay together.

![Trip records](assets/03-trips.png)

### 4. Counter collections

Ticket counts, per-ticket fares, commission, actual deposits and counter outstanding.

![Counter collections](assets/04-collections.png)

### 5. Crew and contact records

Staff roles and demonstration phone numbers, stored as text to preserve leading zeros.

![Crew and contact records](assets/05-crew.png)

### 6. Routes and fares

Coach mappings and editable route fares are maintained in the daily workbook.

![Routes and fares](assets/06-routes-fares.png)

### 7. Review and close workflow

![Review and close workflow illustration](assets/07-review-workflow.svg)

### 8. PDF export workflow

![Print and save as PDF workflow illustration](assets/08-pdf-export.svg)

## Technology stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Accounting and reporting | Python standard library | Validation, decimal money arithmetic, workbook XML, CSV and report generation |
| Data entry and analysis | Microsoft Excel `.xlsx` | Daily trips, collections, master lists and a separate public-data analysis workbook |
| Ledger | SQLite through Python `sqlite3` | Versioned snapshots, audit events and recovery |
| Local control panel | HTML, CSS, vanilla JavaScript | Workbook actions, review, closure and exports |
| PDF | Browser Print / Save as PDF; optional Edge headless print | Save the printable report as a PDF |
| Public-data research | Python standard library | Official-data download, validation, provenance, summaries and chronological forecast comparison |
| Optional independent analysis | Base R | Analyze financial exports or public ridership CSV data |
| CI | GitHub Actions | Ruff formatting/lint, automated tests and Python compilation |

The application and unittest suite have no third-party Python package dependencies. Ruff is a separate development dependency for formatting and lint checks. External applications keep their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).

## Getting started

For a fictional demonstration on Windows, double-click **`launch_demo.bat`** after installing Python 3.11+. It creates a separate 14-day demo workspace, opens the local dashboard, and leaves your normal working ledger separate. Alternatively:

```text
python demo.py --folder portfolio_demo --days 14
python control_panel.py --root portfolio_demo
```

### Requirements

- Windows for the established desktop workflow. OS-specific file opening also supports macOS and Linux commands; the full desktop workflow has not been verified there.
- Python 3.11 or later.
- Microsoft Excel for editing workbooks.
- A browser with Print / Save as PDF; Microsoft Edge for optional automatic PDF output.

### Run the project

Download and extract the repository ZIP, then double-click `launch.bat`.

Or, after publishing this repository:

```text
git clone https://github.com/{{GITHUB_USERNAME}}/{{REPOSITORY_NAME}}.git
cd {{REPOSITORY_NAME}}
python control_panel.py
```

Keep the launcher window open. The application binds to `127.0.0.1` on a free local port.

### Try the example first

```text
python demo.py
```

This creates a separate `demo_workspace/`, imports a fictional day, reviews and closes it, and generates Excel and printable reports. Open the printed HTML path in your browser and use **Print / Save as PDF**. It does not populate your real `daily/` folder. To preserve an existing demo, use `python demo.py --folder another_demo` for a new copy.

## Working workflow

1. **Configure:** set the company name in `project.json`; set real routes, fares, buses, staff and counters in the daily workbook.
2. **Record:** create the date's workbook and enter trips and counter sales/deposits.
3. **Save and close Excel:** importing pins accepted identifiers and lookups and saves a source backup.
4. **Import:** bring the daily inputs into the local ledger.
5. **Review:** resolve invalid inputs and blank receipts; enter `0` for a known zero deposit.
6. **Close:** accept the revision for final reports. A known outstanding balance can remain.
7. **Export:** choose the reporting dates and company, then export Excel or open the printable report.

## Export a report as PDF

1. In the panel, choose the company and reporting dates.
2. Click **Open printable report**, then open the report link shown below the form.
3. Click **Print / Save as PDF** in the report, or press **Ctrl+P**.
4. Choose **Save as PDF** or **Microsoft Print to PDF** as the destination.
5. Use **Legal** paper and **Portrait** orientation. Disable browser headers and footers; enable background graphics if available.
6. Save the PDF to your chosen folder.

The printable report and Excel export use the same closed-ledger records. An open correction retains its previous closed values until the replacement closes. This is a finance control, not a request to re-enter the same transactions.

The [PDF export guide](docs/PDF_EXPORT.md) also explains direct Excel-to-PDF export and the optional **Automatic PDF** button. You can download [the sample printable report](docs/Demo_Report_en.html), open it locally and try the print workflow.

## Accounting rules

| Measure | Rule |
| --- | --- |
| Fare | Tickets sold × accepted fare per ticket |
| Commission | Tk 50 per ticket at commission counters; zero at own counters |
| Due after commission | Fare less commission |
| Deposits | Money actually received |
| Outstanding | Positive unpaid balance, calculated separately for each trip/counter |
| Extra receipts | Positive overpayment, shown separately |

Demo control totals: **3 trips, 74 seats, Tk 70,600 fare, Tk 2,250 commission, Tk 68,350 after commission, Tk 49,450 deposits, Tk 18,900 outstanding.**

The scope is revenue and collection reconciliation. Operating expenses, payroll and net profit are outside this model. Capacity and commission rules are fixed at 62 seats and the rates above; changing branding does not change those financial rules.

## Customization

Use **Customize** in the control panel, or edit `project.json`, for supported project identity and defaults:

```json
{{PROFILE_JSON}}
```

Reload the browser page after editing the JSON file. Report company defaults follow the profile; you can override the company in the export form. Branding changes do not alter capacity, commissions or closed financial records. The **Planning** view uses hypothetical inputs and does not reconfigure those accounting rules.

For repeatable README customization, edit `docs/README.template.md`, then run:

```text
python tools/update_readme.py
```

This is an explicit documentation step; the application never overwrites your README automatically. See [customization details](docs/CUSTOMIZATION.md) for master lists, images, copyright and repository naming.

## Project structure

```text
SmartBus/
├── control_panel.py             # Local operator controls
├── counter_accounting.py        # Accounting and reconciliation
├── daily_system.py              # Daily workbooks and printable/PDF reports
├── values.py                    # Shared money/date helpers
├── xlsx_io.py                   # Shared workbook XML reading
├── platform_open.py             # OS-aware saved-file/folder opening
├── ledger_store.py              # SQLite revisions, closure, audit and recovery
├── period_export.py             # Combined Excel reports
├── report_layout.py             # Printable report layout
├── project_profile.py           # Validated profile loading
├── project.json                 # Editable identity and report defaults
├── insights.py                  # Closed-record analysis and planning calculations
├── ridership.py                 # Reproducible official public-data research
├── analyze.R                    # Optional base-R accounts/ridership analysis
├── demo.py                      # Disposable end-to-end demonstration
├── Daily_Template_en.xlsx        # Live daily template; configure real fares
├── Demo_2026-10-12_en.xlsx        # Fictional example inputs
├── assets/                      # Part-by-part images and illustrations
├── docs/                        # Guides, README template and report example
├── research/                    # Public snapshot, provenance, benchmark and analysis workbook
├── tools/                       # README generation and release packaging
├── .github/                     # CI and contribution templates
├── daily/                       # Real daily inputs, ignored by Git
├── reports/                     # Real exports, ignored by Git
├── test_*.py                    # Standard-library automated tests
├── requirements-dev.txt         # Pinned development checks
├── ruff.toml                    # Python formatting/lint configuration
├── AGENTS.md                    # Repository guidance for coding agents
├── LICENSE                      # MIT License
└── THIRD_PARTY_NOTICES.md        # External tools and attribution
```

`data/`, `backups/`, `demo_workspace/` and `dist/` are created locally as needed and excluded from publication.

## Data controls and boundaries

- One workbook per business date; 100 trips and 500 collection lines per daily workbook.
- Overflow, duplicate keys and incomplete inputs are rejected rather than silently omitted.
- Final reports use published closed revisions, including when a source workbook later changes or disappears.
- Corrections require a reason and a replacement review/closure.
- A missing day is not assumed to be a zero-trip day.
- Operator names are attribution labels, not authenticated accounts. This is a single-workstation application.
- Closure is an application control; a database-file owner can alter local files directly.
- Backups cover the ledger; keep separate copies of source workbooks and exports.

## Tests and release checks

```text
python -m pip install -r requirements-dev.txt
ruff format --check .
ruff check .
python -m unittest discover -s . -p "test_*.py" -v
python -m compileall -q .
python tools/package_release.py
```

Development dependencies are needed only for formatting/lint checks. Use `ruff format .` to apply formatting and review any automatic lint fixes. CI checks formatting, lint, tests and compilation on Python 3.11 and 3.13 on Windows and Ubuntu. See [delivery verification](docs/DELIVERY_VERIFICATION.md) for the actual local results and desktop/PDF limitations. Remote CI results are established after the repository is uploaded and its jobs run.

## GitHub and releases

The [GitHub setup guide](docs/GITHUB_SETUP.md) covers repository upload, topics, release notes and the final ZIP. The manually triggered **Build release archive** workflow creates a downloadable artifact; it does not publish a GitHub release automatically.

## Development notes

Developed by {{AUTHOR}} with support from ChatGPT/Codex, an AI assistant. I guided the project direction and feature choices; the assistant helped with code generation, debugging, tests and documentation. No real-company adoption, financial outcomes or time savings are claimed by the demonstration data.

See the [portfolio and learning guide](docs/PORTFOLIO_GUIDE.md) for the research method, a Python/Excel learning path, practical exercises, contribution evidence and an adaptable project narrative. The earlier [owner guide](docs/OWNER_GUIDE.md) explains the financial demonstration. The [final package verification](docs/FINAL_PACKAGE_VERIFICATION.md) distinguishes freshly rerun checks from desktop steps still requiring manual acceptance.

Future work may add direct browser data entry and a dedicated Trips interface. Those features are not included in this release.

## Author

**{{AUTHOR}}**
[GitHub](https://github.com/{{GITHUB_USERNAME}})

## License

Released under the **[MIT License](LICENSE)**. External tools retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [NOTICE](NOTICE).

Copyright (c) 2026 {{AUTHOR}}.
