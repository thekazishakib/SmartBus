"""Read-only operational insights from published revenue reconciliation snapshots.

Missing dates are gaps in publication, not zero-activity days. All money remains
Decimal until the JSON boundary. Planning scenarios never change saved accounts.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, DecimalException, localcontext

from ledger_store import LedgerStore
from values import dec, money

CAPACITY = 62
MAX_RANGE_DAYS = 366
MONEY_FIELDS = ("gross", "commission", "due", "actual", "outstanding", "extra")


def _range(start, end):
    result = []
    for value in (start, end):
        try:
            parsed = date.fromisoformat(str(value))
        except (ValueError, TypeError) as exc:
            raise ValueError("Use dates in YYYY-MM-DD format.") from exc
        if str(value) != parsed.isoformat():
            raise ValueError("Use dates in YYYY-MM-DD format.")
        result.append(parsed)
    first, last = result
    if first > last:
        raise ValueError("Start date must be on or before end date.")
    if (last - first).days + 1 > MAX_RANGE_DAYS:
        raise ValueError("Insights date ranges must not exceed 366 days.")
    return first, last


def _number(value, field):
    try:
        number = None if isinstance(value, bool) else dec(value)
    except DecimalException as exc:
        raise ValueError(f"Invalid {field} in closed revision.") from exc
    if number is None or number < 0:
        raise ValueError(f"Invalid {field} in closed revision.")
    return number


def _count(value, field):
    number = _number(value, field)
    if number != number.to_integral_value():
        raise ValueError(f"Invalid {field} in closed revision.")
    return int(number)


def _totals():
    return dict(trips=0, seats=0, capacity=0, **dict.fromkeys(MONEY_FIELDS, Decimal(0)))


def _add_trip(totals, trip):
    totals["trips"] += 1
    totals["seats"] += _count(trip["seats"], "seats")
    totals["capacity"] += _count(trip["capacity"], "capacity")
    for field in MONEY_FIELDS:
        source = "extra_received" if field == "extra" else field
        totals[field] += _number(trip[source], field)


def _percentage(seats, capacity):
    value = Decimal(seats) * 100 / Decimal(capacity) if capacity else Decimal(0)
    return format(money(value), ".2f")


def _output(totals):
    result = dict(totals)
    for field in MONEY_FIELDS:
        result[field] = format(totals[field], ".2f")
    result["occupancy_pct"] = _percentage(totals["seats"], totals["capacity"])
    return result


def build_insights(root, start, end, route=None):
    """Return JSON-safe totals and rankings for up to 366 inclusive calendar days.

    ``days`` counts published dates, including explicitly closed no-trip days.
    ``daily`` only contains those published dates; ``missing_days`` lists gaps.
    ``route`` is an exact route name, or None/empty for the full published scope.
    Pending corrections retain their previous closed publication until reclosed.
    """
    first, last = _range(start, end)
    if route == "":
        route = None
    if route is not None and (
        not isinstance(route, str)
        or not route.strip()
        or len(route) > 160
        or not route.isprintable()
    ):
        raise ValueError("Route must contain 1-160 printable characters.")
    store = LedgerStore(root, create=False)
    books = (
        store.published_books(first.isoformat(), last.isoformat())
        if store.path.is_file()
        else []
    )
    available = sorted({str(t["route"]) for b in books for t in b["trips"]})
    if route is not None and route not in available:
        raise ValueError("Choose an exact route from the available closed revisions.")
    closed_days = {book["day"] for book in books}
    missing = [
        (first + timedelta(days=offset)).isoformat()
        for offset in range((last - first).days + 1)
        if (first + timedelta(days=offset)).isoformat() not in closed_days
    ]

    # Supported snapshot amounts have at most 28 significant digits. Additional
    # precision keeps sums exact across every trip in a maximum-length period.
    with localcontext() as context:
        context.prec = 64
        total = _totals()
        route_totals = {}
        counter_totals = {}
        daily = []
        corrections = []
        for book in books:
            day_totals = _totals()
            selected_trips = set()
            for trip in book["trips"]:
                if route is not None and str(trip["route"]) != route:
                    continue
                selected_trips.add(str(trip["trip"]))
                _add_trip(total, trip)
                _add_trip(day_totals, trip)
                name = str(trip["route"])
                _add_trip(route_totals.setdefault(name, _totals()), trip)
            for group in book["counter_groups"]:
                if str(group["trip"]) not in selected_trips:
                    continue
                name = str(group["counter"])
                counter = counter_totals.setdefault(
                    name,
                    dict(
                        counter=name,
                        kind=group["kind"],
                        trips=set(),
                        seats=0,
                        **dict.fromkeys(MONEY_FIELDS, Decimal(0)),
                    ),
                )
                if counter["kind"] != group["kind"]:
                    counter["kind"] = "Mixed"
                counter["trips"].add((book["day"], str(group["trip"])))
                counter["seats"] += _count(group["seats"], "seats")
                for field in MONEY_FIELDS:
                    source = "extra_received" if field == "extra" else field
                    # Sum the already reconciled trip/counter balances. Replacing
                    # them with max(period due - actual, 0) would hide shortages.
                    counter[field] += _number(group[source], field)
            ledger = book["ledger"]
            daily.append(
                dict(
                    date=book["day"],
                    revision=ledger["revision"],
                    correction_pending=ledger["correction_pending"],
                    **_output(day_totals),
                )
            )
            if ledger["correction_pending"]:
                corrections.append(book["day"])
        routes = [
            dict(rank=rank, route=name, **_output(values))
            for rank, (name, values) in enumerate(
                sorted(
                    route_totals.items(),
                    key=lambda item: (-item[1]["gross"], -item[1]["seats"], item[0]),
                ),
                1,
            )
        ]
        counters = []
        for counter in sorted(
            counter_totals.values(),
            key=lambda item: (-item["outstanding"], -item["extra"], item["counter"]),
        ):
            counters.append(
                dict(
                    counter=counter["counter"],
                    kind=counter["kind"],
                    trips=len(counter["trips"]),
                    seats=counter["seats"],
                    **{field: format(counter[field], ".2f") for field in MONEY_FIELDS},
                )
            )
        totals = _output(total)

    alerts = []
    if missing:
        alerts.append(
            dict(
                code="missing_days",
                severity="warning",
                message=f"{len(missing)} date(s) have no closed revision. Missing dates are not zero-activity days.",
            )
        )
    if total["outstanding"]:
        alerts.append(
            dict(
                code="outstanding",
                severity="warning",
                message=f"Tk {totals['outstanding']} remains outstanding across trip/counter balances.",
            )
        )
    if total["extra"]:
        alerts.append(
            dict(
                code="extra",
                severity="warning",
                message=f"Tk {totals['extra']} in extra receipts is reported separately from shortages.",
            )
        )
    if corrections:
        alerts.append(
            dict(
                code="correction_pending",
                severity="info",
                message=f"{len(corrections)} date(s) have pending corrections. Their previous closed revisions remain published.",
            )
        )
    return dict(
        start=first.isoformat(),
        end=last.isoformat(),
        scope="closed revisions",
        days=len(books),
        totals=totals,
        routes=routes,
        daily=daily,
        counters=counters,
        alerts=alerts,
        missing_days=missing,
        available_routes=available,
    )


def plan_scenario(seats, fare, counter_type):
    """Calculate one hypothetical trip using the project's fixed financial rules."""
    try:
        sold = None if isinstance(seats, bool) else dec(seats)
    except DecimalException as exc:
        raise ValueError("Seats must be a whole number from 0 to 62.") from exc
    if sold is None or sold != sold.to_integral_value() or not 0 <= sold <= CAPACITY:
        raise ValueError("Seats must be a whole number from 0 to 62.")
    try:
        price = None if isinstance(fare, bool) else dec(fare)
    except DecimalException as exc:
        raise ValueError("Fare must be a valid non-negative money amount.") from exc
    rounded = money(price) if price is not None else None
    if price is None or price < 0 or rounded is None or rounded != price:
        raise ValueError(
            "Fare must be a non-negative amount with at most two decimal places."
        )
    if counter_type not in ("Own", "Commission"):
        raise ValueError("Counter type must be Own or Commission.")
    rate = Decimal(50) if counter_type == "Commission" else Decimal(0)
    if price < rate:
        raise ValueError("Fare cannot be less than commission per ticket.")
    try:
        gross = money(sold * price)
        commission = money(sold * rate)
        due = money(gross - commission) if gross is not None else None
    except DecimalException as exc:
        raise ValueError("Scenario money exceeds supported precision.") from exc
    if gross is None or commission is None or due is None:
        raise ValueError("Scenario money exceeds supported precision.")
    return dict(
        seats=int(sold),
        capacity=CAPACITY,
        fare=format(rounded, ".2f"),
        counter_type=counter_type,
        commission_per_ticket=format(rate, ".2f"),
        occupancy_pct=_percentage(int(sold), CAPACITY),
        gross=format(gross, ".2f"),
        commission=format(commission, ".2f"),
        due=format(due, ".2f"),
    )
