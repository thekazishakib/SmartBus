# Customize SmartBus

## Project identity and report defaults

Open **Customize** in the control panel, edit the supported fields, and choose **Save & reload workspace**. The server validates the entire profile before atomically saving `project.json`. You can also edit that file in a text editor and reload the page.

| Field | What it changes |
| --- | --- |
| `project_name` | Panel title/brand and generated README heading |
| `tagline` | Panel introduction and README subtitle |
| `author` | Panel footer and generated README author |
| `github_username` | Generated GitHub profile and repository links |
| `repository_name` | Clone instructions and release archive folder/name |
| `company_name` | Default company in the report form and direct report calls |
| `default_operator` | Initial operator attribution in the panel |
| `accent_color` | Main panel color; use a six-digit hex value such as `#22675f` |

The company field in the report form can override the configured default for that export. These settings do not rewrite historical ledger values or change commission/capacity rules.

Company names allow up to 120 characters and default operators up to 80. Other text fields allow up to 160. Unknown settings and invalid colors are rejected before saving. A separate workstation launched with `--root` has its own profile and data folder.

`project.json` is public project metadata. Do not put passwords, account numbers or private contact information in it.

## README content

The README is yours to edit. For repeatable generation:

1. Change `project.json` for identity/defaults.
2. Edit `docs/README.template.md` for wording, sections and feature descriptions.
3. Run `python tools/update_readme.py`.
4. Inspect the regenerated `README.md` before committing it.

Direct edits to README stay in place until you explicitly regenerate it. If you want to retain those edits in future generations, make the same changes in the template. Profile changes do not automatically change the copyright holder in LICENSE; keep legal identity consistent when intentionally changing authorship.

## Images

The README has separate images for financial totals, counter charts, trips, collections, staff and route fares. Replace the relevant PNG under `assets/` with your own fictional-data screenshot using the same filename, or edit the image path in the template. Keep real staff contacts and financial records out of published images.

The two workflow diagrams and logo are original SVGs. Their generator is `tools/make_workflow_images.py`; it requires only Python's standard library. The diagrams explain the workflow rather than representing a live browser capture.

## Operational master lists

Configure real information in a daily workbook:

- **Buses:** bus and assigned driver.
- **Crew:** staff name, role and phone as text.
- **Counters:** counter names and Own/Commission type.
- **Route List:** coach direction mappings and route fares.
- **Settings:** workbook company, business date, starting trip number and permitted reconciliation tolerance.

New daily files carry master lists forward from the latest earlier same-language file in `daily/`. Accepted transaction lookups are pinned during import. To change imported transaction values, use the correct transaction cells and the documented correction workflow; changing a master alone does not reprice historical trips.

## Accounting scope

Capacity is fixed at 62 seats. Commission is Tk 50 per ticket at commission counters and zero at own counters. The code rejects unsupported edits to those format settings. Generalizing these rules would require coordinated workbook, calculation, validation and test changes; it is not a branding setting.
