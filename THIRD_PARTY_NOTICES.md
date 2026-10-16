# Third-party tools and notices

SmartBus's original source, documentation, workbook templates and demonstration assets are released under the [MIT License](LICENSE), copyright 2026 Kazi Shakib. MIT does not relicense the external products below.

## Runtime and external applications

| Component | Use in SmartBus | Distribution / licensing |
| --- | --- | --- |
| Python 3.11+ and standard library | Accounting, workbook XML, local HTTP server, CSV, files and SQLite access | Installed separately; not bundled. See the [Python license](https://docs.python.org/3/license.html). |
| SQLite | Local ledger through Python's `sqlite3` module | Supplied by Python; no engine binary is included. See [SQLite copyright / public-domain information](https://www.sqlite.org/copyright.html). |
| Microsoft Excel | Edit daily workbooks; optional direct workbook-to-PDF export | Proprietary external product; installed and licensed separately. |
| Microsoft Edge | Optional automatic HTML-to-PDF printing | Proprietary external product; installed separately. Browser Print / Save as PDF is an alternative workflow. |
| Browser and operating-system fonts | Panel, printable reports and workbook text | Uses available system fonts, including Arial and Segoe UI. No font binaries are distributed. |
| R | Optional analysis with `analyze.R` | Installed separately; not required. See [R licensing](https://www.r-project.org/Licenses/). |

There are **no third-party Python package requirements** for normal operation or the unittest suite. Formatting and lint checks have a separate development dependency, listed below. The interface uses plain HTML, CSS and JavaScript; no frontend framework, CDN, analytics service or remote database is required.

## Development checks

| Tool | Use in SmartBus | Upstream license |
| --- | --- | --- |
| Ruff 0.17.0 | Python formatting and lint checks; installed through `requirements-dev.txt` locally and in CI | [MIT License](https://github.com/astral-sh/ruff/blob/0.17.0/LICENSE), copyright Charles Marsh |

Ruff is not bundled and is not required to run the application or unittest suite. Its license remains separate from SmartBus's copyright.

## GitHub workflow actions

These tools are downloaded by GitHub Actions when a workflow runs. Their source is not copied into this repository.

| Action | Purpose | Upstream license |
| --- | --- | --- |
| `actions/checkout@v4` | Check out source for CI | [LICENSE](https://github.com/actions/checkout/blob/v4/LICENSE) |
| `actions/setup-python@v5` | Select the CI Python interpreter | [LICENSE](https://github.com/actions/setup-python/blob/v5/LICENSE) |
| `actions/upload-artifact@v4` | Save a manually built release archive | [LICENSE](https://github.com/actions/upload-artifact/blob/v4/LICENSE) |

## Development assistance and preview assets

OpenAI ChatGPT/Codex assisted with implementation, debugging, tests and documentation. OpenAI's artifact tool was used to edit and render demonstration workbooks during development. Pillow was used for development-only layout verification of the SVG illustrations; see its [upstream license](https://pillow.readthedocs.io/en/stable/about.html#license). These tools are not bundled or needed to run SmartBus.

Images in `assets/` show this project's fictional examples. Workbook previews are renders of the actual demonstration file. Workflow illustrations explain the review and export steps; they are not live browser screenshots. They contain no club logo, Shohoz branding, real passenger data or third-party screenshots. Original project screenshots and illustrations are included under MIT.

Sample staff names, phone numbers, companies and amounts are fictional. Product names and trademarks remain the property of their respective owners; this project does not imply endorsement.

## Public transit research data

`research/cta_ridership.csv` contains a selected historical snapshot of **CTA - Ridership - Bus Routes - Daily Totals by Route**, published by the Chicago Transit Authority through the [City of Chicago Data Portal](https://data.cityofchicago.org/Transportation/CTA-Ridership-Bus-Routes-Daily-Totals-by-Route/jyb9-n7fm). The dataset metadata specifies `SEE_TERMS_OF_USE`; see the [portal terms and disclaimer](https://www.chicago.gov/city/en/narr/foia/data_disclaimer.html). This data retains its source terms and is not relicensed under SmartBus's MIT license.

The included period is October 1 through November 30, 2025. `research/source.json` records the query URL, retrieval timestamp, schema, attribution and SHA-256 checksum. Research summaries, predictions and the Excel analysis workbook are derived from this snapshot and retain that attribution. CTA does not endorse this project. Rides are observed Chicago boardings, not unique passengers, Bangladesh traffic, fare revenue, vehicle capacity or GPS observations.

The financial demonstration and the public ridership research are separate datasets. The workbook is built with OpenAI's artifact tool during development; that tool is not required to use Excel, run the local application, refresh the CSV snapshot or reproduce the Python/R research analysis.
