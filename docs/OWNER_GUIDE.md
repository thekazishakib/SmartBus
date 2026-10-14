# Owner learning and showcase guide

SmartBus 1.2.1 is a finance automation project by Kazi Shakib. This guide builds on an Excel background and introduces the Python needed to understand and maintain the project. It is a practice plan, not evidence that the tasks below have already been completed.

## Describe the project accurately

Suggested introduction, to adapt to your actual contributions:

> I developed SmartBus with support from ChatGPT/Codex, an AI assistant. I guided the project direction and feature choices, while the assistant helped with implementation, debugging, tests and documentation. SmartBus uses Excel, Python and SQLite to reconcile bus revenue and counter receipts. The demonstration uses fictional data.

The application also has a local HTML/CSS/JavaScript control panel, SQLite storage and optional R analysis. Do not describe this version as using only Python and Excel. It reconciles revenue and receipts; it does not calculate operating profit or provide a full general ledger. It is not an official Hanif Enterprise system and contains no established Hanif deployment or business-impact evidence.

## Understand the sample account

| Measure | Fictional amount (Tk) |
| --- | ---: |
| Fare | 70,600 |
| Commission | 2,250 |
| Fare after commission | 68,350 |
| Recorded deposits | 49,450 |
| Outstanding | 18,900 |

Explain 70,600 - 2,250 = 68,350, then 68,350 - 49,450 = 18,900 for this sample, which has no extra receipts. In general, calculate shortages and overpayments separately for each trip/counter; a single net difference can conceal exceptions.

The raw example has a blank receipt. Blank means unknown, not confirmed zero. `demo.py` explicitly changes that fictional receipt to zero before review and closure. Never replace an unknown real receipt with zero just to close accounts.

Some original workbook previews use "Total income" for fare after commission. Explain this amount as fare after commission, not net profit; operating expenses are excluded.

## Rehearse a three-minute demonstration

1. State the problem: reconcile ticket sales with counter receipts and preserve accepted accounts.
2. Open the fictional workbook and identify inputs, calculated cells and master lists.
3. Run `python demo.py --folder demo_workspace` from a fresh extracted copy. If that folder already contains a demo, keep it and choose a fresh folder outside the source repository.
4. Open the generated Excel and printable report. Reconcile the amounts above.
5. Explain separate shortages/overpayments, blank versus zero and reasoned corrections.
6. State the limits: fixed capacity/commission rules, no profit calculation, local operator labels rather than authenticated approvals, and fictional data.

Automated tests do not verify Excel editing or browser printing on your computer. Rehearse saving/closing a workbook, importing, reviewing, closing and printing in a disposable copy before recording a demo.

## Four-week learning plan

### Week 1: Excel and finance

Trace one trip from fare and tickets through commission, deposit and outstanding. Work through a zero receipt, an unknown receipt and an overpayment by hand. Explain workbook formulas and validations. Record what you personally checked.

### Week 2: Essential Python

Learn variables, lists, dictionaries, loops, functions, imports, exceptions and `Decimal`. Read `values.py`, then follow the main calculation in `counter_accounting.py`. Trace one sample counter with a notebook and a calculator; do not memorize the entire application.

### Week 3: Verification and controlled changes

Run `python -m unittest discover -s . -p "test_*.py" -v`. Read the tests for separate shortages/overpayments and blank receipts. In a disposable copy, make one small change you can explain, inspect the difference and run appropriate tests. Do not change financial rules without understanding their effects on templates, reports and validation.

### Week 4: Communication and external feedback

Record a short demo. Ask a teacher, accountant or operator to review fictional cases. Keep their observations, your response and what changed. Report measured outcomes only after collecting evidence; feedback alone is not deployment or proven time saving.

## Keep a personal contribution record

For each meaningful update, record the date, question, your decision, AI assistance, how you verified it and what remains uncertain. Do not invent past work or outcomes. Specific explanations are stronger than a claim of advanced Python expertise.

## After publication

- Check GitHub Actions results, README images and a fresh download of the release.
- Keep v1.2.1 as the published baseline. Later changes need accurate changelog entries and new version numbers where appropriate.
- Learn the existing finance model and get feedback before expanding features.
- Use fictional or explicitly authorized, appropriately anonymized examples publicly. Access to company records does not imply permission to publish them.

Follow [GitHub setup](GITHUB_SETUP.md) and the [operating guide](PROFESSIONAL_GUIDE.md).
