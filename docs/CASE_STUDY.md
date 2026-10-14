# Finance case study: SmartBus

## Business problem

Bus operations produce trip sales and counter deposits that must be reconciled. Changed fares, moved spreadsheet rows and unreviewed corrections can undermine historical accounts. Counter shortages and overpayments also need to remain visible separately.

## Workflow

SmartBus combines English Excel entry, Python decimal reconciliation and SQLite snapshots of accepted accounts. Operators import a day, review differences and close a revision. Later corrections record reasons, preserve the prior closure and become authoritative only after review and closure.

The scope is ticket-revenue settlement: fare, fixed commission, deposits, outstanding and surplus. Expense accounting and net profit are outside the application.

## Demonstration

The fictional reference day contains three trips and 74 sold seats.

| Measure | Sample result (Tk) |
| --- | ---: |
| Fare | 70,600 |
| Counter commission | 2,250 |
| Fare after commission | 68,350 |
| Deposits | 49,450 |
| Outstanding | 18,900 |

Commission counters earn Tk 50 per ticket; own counters earn zero. Calculations preserve separate counter differences. Closed snapshots retain accepted fares and assignments.

## Skills demonstrated

- Translating an operational finance process into entry, review and reporting steps.
- Implementing reconciliation rules and preserving exceptions.
- Designing application controls for accepted records, corrections, audit history and recovery.
- Writing regression checks for financial behavior and documenting manual acceptance limits.
- Providing an English operator workflow with entry templates, status checks and reports.

## Evidence and limits

The package includes fictional English inputs, test code, current instructions and a closed-ledger Excel report example. It does not establish live deployment, measured time savings, fewer errors, user adoption or independent audit. Claim those outcomes only after a pilot measures them.

Actor labels are not authentication, closure does not prevent database-file edits, and the application targets one computer. A pilot must confirm reference data, independently reconcile representative days, rehearse recovery and verify Excel/Edge output.

## Portfolio description

> Built an English-language Python, Excel and SQLite bus-revenue reconciliation application with daily review and closure, reasoned corrections, stable trip identifiers, audit events and backup recovery.

Describe the delivered behavior and actual verification honestly. Add quantified results after collecting verifiable pilot evidence.

