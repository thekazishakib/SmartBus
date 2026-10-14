"""Legal portrait report: cover, single-page dashboard, journeys, assignments."""

import html
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal


def e(x):
    return html.escape("" if x is None else str(x))


def value(x):
    if x is None or x == "":
        return "-"
    if isinstance(x, datetime):
        return x.strftime("%d-%m-%Y\n(%I:%M %p)")
    if isinstance(x, Decimal):
        return f"{x:,.2f}"
    if isinstance(x, str):
        try:
            return (
                datetime.fromisoformat(x).strftime("%d-%m-%Y") if len(x) == 10 else e(x)
            )
        except ValueError:
            pass
    return e(x)


def date_ranges(items):
    dates = sorted(set((date.fromisoformat(str(d)) for d in items)))
    groups = []
    if not dates:
        return "-"
    first = last = dates[0]
    for d in dates[1:]:
        if d == last + timedelta(days=1):
            last = d
        else:
            groups.append((first, last))
            first = last = d
    groups.append((first, last))
    return ", ".join(
        (
            a.strftime("%d-%m-%Y")
            if a == b
            else a.strftime("%d-%m-%Y") + " - " + b.strftime("%d-%m-%Y")
            for a, b in groups
        )
    )


def summary(books):
    trips = [t for b in books for t in b["trips"]]
    sums = {
        k: sum((t[k] for t in trips if t[k] is not None), Decimal(0))
        for k in (
            "seats",
            "gross",
            "commission",
            "due",
            "actual",
            "outstanding",
            "applied",
        )
    }
    sums["cost"] = sum((t["counter_cost"] for t in trips), Decimal(0))
    sums["extra"] = sum((t["extra_received"] for t in trips), Decimal(0))
    sums["held"] = sum(
        (t["held_cash"] for t in trips if t["held_cash"] is not None), Decimal(0)
    )
    sums["transfer_unknown"] = sum((t["transfer_unknown"] for t in trips))
    return (trips, sums)


def render_report(
    books, missing, excluded, start, end, lang="en", company=None, counter=None
):
    if lang != "en":
        raise ValueError("This release supports English only")

    def digits(x):
        return str(x)

    def value(x):
        return digits(globals()["value"](x))

    def header(title, when=None):
        return (
            "<div class=reporthead><b>"
            + e(company)
            + "</b><span>"
            + digits(e(when or period))
            + "</span></div><h1>"
            + e(title)
            + "</h1>"
        )

    company = company or "Demo Company"
    from counter_accounting import counter_totals

    counters = counter_totals(books)
    trips, sums = summary(books)
    period = (
        datetime.fromisoformat(str(start)).strftime("%d-%m-%Y")
        + " — "
        + datetime.fromisoformat(str(end)).strftime("%d-%m-%Y")
    )
    trips = sorted(
        trips, key=lambda t: (t["day"], t["start"] or datetime.min, str(t["trip"]))
    )
    invalid = sum((bool(t["issues"]) for t in trips)) + sum(
        (len(b["orphan"]) for b in books)
    )

    def table(heads, rows, cls=""):
        return (
            '<table class="'
            + cls
            + '"><thead><tr>'
            + "".join(("<th>" + e(h) + "</th>" for h in heads))
            + "</tr></thead><tbody>"
            + "".join(
                (
                    "<tr>" + "".join(("<td>" + value(c) + "</td>" for c in r)) + "</tr>"
                    for r in rows
                )
            )
            + "</tbody></table>"
        )

    status = {
        "Matched": "Matched",
        "Deposit pending": "Deposit pending",
        "Short / extra": "Short / extra",
        "No collection": "No collection",
        "CHECK": "Check entries",
    }
    routes = defaultdict(
        lambda: {
            "trips": 0,
            "seats": Decimal(0),
            "gross": Decimal(0),
            "capacity": Decimal(0),
            "commission": Decimal(0),
            "income": Decimal(0),
        }
    )
    for t in trips:
        ends = [p.strip() for p in str(t["route"]).split(" - ")]
        ends.sort(key=lambda x: (x != "Dhaka", x))
        key = " / ".join(ends)
        routes[key]["trips"] += 1
        routes[key]["seats"] += t["seats"]
        routes[key]["gross"] += t["gross"]
        routes[key]["capacity"] += t["capacity"] or Decimal(0)
        routes[key]["commission"] += t["commission"]
        routes[key]["income"] += t["due"] or Decimal(0)
    ranked = sorted(
        routes.items(),
        key=lambda x: (-x[1]["trips"], -x[1]["seats"], -x[1]["gross"], x[0]),
    )
    demo = any((b["dataset"] != "LIVE" for b in books))
    body = (
        '<section class="cover"><div class="brand">'
        + e(company)
        + '</div><div class="rule"></div><h1>'
        + "Trip and collection report"
        + '</h1><div class="period">'
        + digits(e(period))
        + "</div><p>"
        + "Reporting period"
        + "</p>"
    )
    if demo:
        body += '<p class="notice">' + "DEMO: sample records for learning." + "</p>"
    body += (
        '<p class="muted">'
        + "Created: "
        + digits(datetime.now().strftime("%d-%m-%Y (%I:%M %p)"))
        + "</p></section>"
    )
    published = [b for b in books if b.get("ledger")]
    if published:
        note = "Final report from closed ledger revisions."
        pending = [b["day"] for b in published if b["ledger"].get("correction_pending")]
        if pending:
            note += (
                " "
                + "Corrections are pending; previous closed values are shown for: "
                + e(date_ranges(pending))
            )
        body = body.replace(
            "</section>", '<p class="notice">' + note + "</p></section>", 1
        )
    body += '<section class="dashboard page">' + header("Dashboard")
    metrics = [
        ("Total trips", len(trips)),
        ("Total sold seats", int(sums["seats"])),
        ("Total fare", sums["gross"]),
        ("Total income", sums["due"]),
        ("Total commission cost", sums["commission"]),
        ("Total outstanding", sums["outstanding"]),
        ("Total deposits", sums["actual"]),
    ]
    body += (
        '<div class="metrics">'
        + "".join(
            (
                "<div><span>" + e(k) + "</span><strong>" + value(v) + "</strong></div>"
                for k, v in metrics
            )
        )
        + "</div>"
    )
    parts = [
        ("Total income", max(sums["due"], Decimal(0)), "#40566D"),
        ("Total commission", max(sums["commission"], Decimal(0)), "#6F7C89"),
    ]
    total = sum((v for _, v, _ in parts), Decimal(0))
    svg = (
        '<svg viewBox="0 0 330 240" role="img" aria-label="Money breakdown pie chart">'
    )
    angle = -math.pi / 2
    for label, amount, color in parts:
        if amount <= 0 or total <= 0:
            continue
        sweep = float(amount / total) * 2 * math.pi
        x1 = 100 + 72 * math.cos(angle)
        y1 = 93 + 72 * math.sin(angle)
        x2 = 100 + 72 * math.cos(angle + sweep)
        y2 = 93 + 72 * math.sin(angle + sweep)
        if sweep >= 2 * math.pi - 1e-08:
            svg += f'<circle cx="100" cy="93" r="72" fill="{color}"/>'
        else:
            svg += f'<path d="M100,93 L{x1},{y1} A72,72 0 {int(sweep > math.pi)} 1 {x2},{y2} Z" fill="{color}" stroke="white" stroke-width="1"/>'
        mid = angle + sweep / 2
        if amount / total >= Decimal(".05"):
            svg += f'<text x="{100 + 49 * math.cos(mid):.1f}" y="{97 + 49 * math.sin(mid):.1f}" fill="white" font-size="11" text-anchor="middle">{float(amount / total) * 100:.1f}%</text>'
        angle += sweep
    if total == 0:
        svg += '<text x="20" y="90" font-size="13">' + "No fare recorded" + "</text>"
    for i, (label, amount, color) in enumerate(parts):
        svg += f'<rect x="192" y="{43 + i * 42}" width="9" height="9" fill="{color}"/><text x="208" y="{52 + i * 42}" font-size="10">{e(label)}</text><text x="208" y="{67 + i * 42}" font-size="12">{amount:,.0f} ({(float(amount / total) * 100 if total else 0):.1f}%)</text>'
    svg += "</svg>"
    svg = __import__("re").sub("(?<=>)[^<>]+(?=<)", lambda m: digits(m.group()), svg)
    sales = [(r["counter"], r["seats"], r["seats"]) for r in counters if r["seats"] > 0]
    if len(sales) > 4:
        sales = sales[:4] + [
            (
                "Other counters",
                sum((r[1] for r in sales[4:]), Decimal(0)),
                sum((r[2] for r in sales[4:]), Decimal(0)),
            )
        ]
    colours = [
        "#40566D",
        "#59646F",
        "#6F7C89",
        "#92999F",
        "#52677A",
        "#7D8791",
        "#6F7C89",
        "#92999F",
    ]
    sales_total = sum((r[1] for r in sales), Decimal(0))
    counter_svg = (
        '<svg viewBox="0 0 330 240" role="img" aria-label="Counter sales pie chart">'
    )
    angle = -math.pi / 2
    for i, (name, amount, tickets) in enumerate(sales):
        sweep = float(amount / sales_total) * math.pi * 2
        cx, cy, radius = (74, 98, 66)
        x1 = cx + radius * math.cos(angle)
        y1 = cy + radius * math.sin(angle)
        x2 = cx + radius * math.cos(angle + sweep)
        y2 = cy + radius * math.sin(angle + sweep)
        colour = colours[i]
        if sweep >= 2 * math.pi - 1e-08:
            counter_svg += f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{colour}"/>'
        else:
            counter_svg += f'<path d="M{cx},{cy} L{x1},{y1} A{radius},{radius} 0 {int(sweep > math.pi)} 1 {x2},{y2} Z" fill="{colour}" stroke="white" stroke-width="1"/>'
        if amount / sales_total >= Decimal(".08"):
            mid = angle + sweep / 2
            counter_svg += f'<text x="{cx + 43 * math.cos(mid)}" y="{cy + 43 * math.sin(mid) + 4}" font-size="10" fill="white" text-anchor="middle">{float(amount / sales_total) * 100:.0f}%</text>'
        angle += sweep
        y = 18 + i * 27
        counter_svg += (
            f'<rect x="150" y="{y}" width="7" height="7" fill="{colour}"/><text x="162" y="{y + 7}" font-size="8">{e(name)}</text><text x="162" y="{y + 19}" font-size="8">{int(tickets)} '
            + "tickets"
            + "</text>"
        )
    if not sales:
        counter_svg += (
            '<text x="20" y="100" font-size="12">' + "No sales recorded" + "</text>"
        )
    counter_svg += "</svg>"
    counter_svg = __import__("re").sub(
        "(?<=>)[^<>]+(?=<)", lambda m: digits(m.group()), counter_svg
    )
    body += (
        '<div class="charts"><div><h3>'
        + "Total income and commission"
        + "</h3>"
        + svg
        + "</div><div><h3>"
        + "Top counters by tickets sold"
        + "</h3>"
        + counter_svg
        + "</div></div>"
    )
    body += table(
        ["Counter", "Tickets", "Commission", "Total income", "Received", "Outstanding"],
        [
            [
                r["counter"],
                int(r["seats"]),
                r["commission"],
                r["due"],
                r["actual"],
                r["outstanding"],
            ]
            for r in counters[:6]
        ],
        "compact",
    )
    body += (
        '<div class="coverage"><p><b>'
        + "Dates with data: "
        + "</b>"
        + digits(e(date_ranges([b["day"] for b in books])))
        + "</p><p><b>"
        + "Missing dates: "
        + "</b>"
        + digits(e(date_ranges(missing)))
        + '</p><p class="tiny">'
        + "Date ranges include both ends. A missing file is not a zero-trip day."
        + "</p></div>"
    )
    body += "<p>" + "Extra deposits: " + value(sums["extra"]) + "</p>"
    if missing:
        body += (
            '<p class="tiny">'
            + "The number of trips on missing dates cannot be determined without data."
            + "</p>"
        )
    if invalid:
        body += (
            '<p class="notice">'
            + f"{invalid} records need correction; amounts may be incomplete. See trip issues."
            + "</p>"
        )
    body += "</section>"
    body += (
        '<section class="page collections">'
        + header("Collections")
        + "<p>"
        + "Every counter has its own account. Totals cover the whole selected period."
        + "</p>"
    )
    body += (
        table(
            [
                "Counter",
                "Tickets",
                "Fare",
                "Commission",
                "Total income",
                "Received",
                "Outstanding",
            ],
            [
                [
                    r["counter"],
                    int(r["seats"]),
                    r["gross"],
                    r["commission"],
                    r["due"],
                    r["actual"],
                    r["outstanding"],
                ]
                for r in counters
            ],
        )
        + "</section>"
    )
    for t in trips:
        body += '<section class="trip page">' + header(
            "Trip " + digits(t["trip"]), value(t["day"])
        )
        if t.get("record_id"):
            source = next((b for b in books if b["day"] == t["day"]))
            body += '<p class="tiny">' + "Record ID: " + e(t["record_id"])
            body += (
                " · "
                + "Closed revision: "
                + digits(source.get("ledger", {}).get("revision", "-"))
                + "</p>"
            )
        items = [
            ("Coach number", t["coach"]),
            ("Departure date / time", t["start"]),
            ("Route", t["route"]),
            ("Going / return", t["direction"]),
            ("Bus number", t["bus"]),
            (
                "Seats available",
                int(t["capacity"]) if t["capacity"] is not None else None,
            ),
            ("Sold seats", int(t["seats"])),
            (
                "Seat use",
                f"{t['occupancy'] * 100:.1f}%" if t["occupancy"] is not None else None,
            ),
        ]
        rows = []
        for i in range(0, len(items), 2):
            rows.append([items[i][0], items[i][1], items[i + 1][0], items[i + 1][1]])
        body += table(["Field", "Information", "Field", "Information"], rows)
        assignments = []
        for role, label in [
            ("driver", "Driver"),
            ("guide", "Guide"),
            ("conductor", "Conductor"),
        ]:
            if t[role]:
                assignments.append([label, t[role], t[role + "_phone"]])
        body += table(["Job", "Name", "Phone"], assignments)
        remaining = t["outstanding"]
        extra = t["extra_received"]
        body += (
            "<h2>"
            + "Fare and cash"
            + "</h2>"
            + table(
                [
                    "Fare",
                    "Commission",
                    "Total income",
                    "Deposit",
                    "Outstanding",
                    "Extra received",
                ],
                [
                    [
                        t["gross"],
                        t["commission"],
                        t["due"],
                        t["actual"] or Decimal(0),
                        remaining,
                        extra,
                    ]
                ],
            )
        )
        body += (
            "<p>"
            + "Deposit status: "
            + e(status.get(t["status"], t["status"]))
            + "</p>"
        )
        if t.get("held_cash") is not None:
            body += (
                "<p>"
                + "Sent to head office: "
                + value(t["sent_to_office"])
                + " | "
                + "Cash held: "
                + value(t["held_cash"])
                + "</p>"
            )
        if t.get("held_cash") is None:
            body += (
                '<p class="tiny">'
                + "Cash held: transfer information not entered. Extra receipts are shown separately."
                + "</p>"
            )
        body += "<h2>" + "Collections · Counters on this trip" + "</h2>"
        group_rows = next((b for b in books if b["day"] == t["day"]))["counter_groups"]
        group_rows = [g for g in group_rows if g["trip"] == t["trip"]]
        body += table(
            [
                "Counter",
                "Tickets",
                "Fare",
                "Commission",
                "Total income",
                "Received",
                "Outstanding",
            ],
            [
                [
                    g["counter"],
                    int(g["seats"]) if g["seats"] is not None else None,
                    g["gross"],
                    g["commission"],
                    g["due"],
                    g["actual"] or Decimal(0),
                    g["outstanding"],
                ]
                for g in group_rows
            ],
        )
        if t["previous"]:
            body += "<p>" + "Previous trip reference: " + e(t["previous"]) + "</p>"
        if t["note"]:
            body += "<p>" + "Note: " + e(t["note"]) + "</p>"
        if t["issues"]:
            body += (
                '<p class="notice">' + "Check: " + e("; ".join(t["issues"])) + "</p>"
            )
        body += "</section>"
    body += (
        '<section class="page buses">'
        + header("Buses")
        + "<p>"
        + "Vehicles used during this period, one row per trip."
        + "</p>"
    )
    busrows = []
    crewrows = []
    for t in trips:
        b = next((b for b in books if b["day"] == t["day"]))
        busrows.append(
            [
                t["day"],
                t["coach"],
                t["bus"],
                t["trip"],
                t["route"],
                int(t["capacity"]) if t["capacity"] is not None else None,
                int(t["seats"]),
            ]
        )
        for role, title in [
            ("driver", "Driver"),
            ("guide", "Guide"),
            ("conductor", "Conductor"),
        ]:
            if t[role]:
                note = next(
                    (r[3] for r in b["crew"] if str(r[0]) == str(t[role])), None
                )
                crewrows.append(
                    [
                        t["day"],
                        t["trip"],
                        t["bus"],
                        t["coach"],
                        title,
                        t[role],
                        t[role + "_phone"],
                    ]
                )
    body += (
        table(
            [
                "Date",
                "Coach number",
                "Bus number",
                "Trip number",
                "Route",
                "Total seats",
                "Sold seats",
            ],
            busrows,
        )
        + "</section>"
    )
    body += (
        '<section class="page crew">'
        + header("Crew")
        + "<p>"
        + "People assigned to trips, including their vehicle and contact details."
        + "</p>"
        + table(
            [
                "Date",
                "Trip number",
                "Bus number",
                "Coach number",
                "Job",
                "Name",
                "Phone number",
            ],
            crewrows,
        )
        + "</section>"
    )
    orphan = [
        (b["day"], collection_line) for b in books for collection_line in b["orphan"]
    ]
    if orphan:
        body += (
            '<section class="page"><h1>'
            + "Unmatched collection entries"
            + "</h1>"
            + table(
                ["Date", "Trip", "Counter", "Fare", "Issues"],
                [
                    [
                        day,
                        collection_line["trip"],
                        collection_line["counter"],
                        collection_line["gross"],
                        "; ".join(collection_line["issues"]),
                    ]
                    for day, collection_line in orphan
                ],
            )
            + "</section>"
        )
    if ranked:
        body += (
            '<section class="page">'
            + header("All routes")
            + table(
                [
                    "Route",
                    "Trips",
                    "Total seats",
                    "Sold seats",
                    "Gross fare",
                    "Commission",
                    "Final income",
                ],
                [
                    [
                        n,
                        r["trips"],
                        int(r["capacity"]),
                        int(r["seats"]),
                        r["gross"],
                        r["commission"],
                        r["income"],
                    ]
                    for n, r in ranked
                ],
            )
            + "</section>"
        )
    css = ""
    css += '@page{size:8.5in 14in;margin:12mm 11mm 14mm;@bottom-right{content:"Page " counter(page) " / " counter(pages);font:8pt Arial;color:#586B7E}}*{box-sizing:border-box}body{margin:0;font:10pt Arial,sans-serif;color:#263445}h1{font-size:20pt;color:#34495E;margin:0 0 8px}h2{font-size:12pt;color:#34495E;margin:16px 0 8px;border-bottom:1px solid #3C7D88;padding-bottom:5px}h3{font-size:10pt;margin:8px 0}.page{break-before:page}.cover{padding:100px 10px 0;text-align:center}.brand{font-size:25pt;color:#34495E;font-weight:700}.rule{height:4px;background:#3C7D88;margin:30px 0}.cover h1{margin:35px 0 20px}.cover h2{border:0;font-size:18pt}.period{font-size:17pt;margin-top:40px}.coverfacts{margin:75px 0 30px;text-align:left}.muted,.subtitle{color:#586B7E}.subtitle{margin:0 0 12px;font-size:10pt}p{line-height:1.5;margin:8px 0}table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:8.5pt;margin:9px 0 13px}th{background:#34495E;color:white;font-weight:600;text-align:left;padding:6px}td{padding:6px;border-bottom:1px solid #DCE3EB;vertical-align:top;overflow-wrap:anywhere}tr:nth-child(even){background:#F6F6F6}thead{display:table-header-group}tr{break-inside:avoid}.notice{background:#FFFDF2;color:#794B20;padding:9px;font-size:9pt}.metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:6px 12px}.metrics div{padding:7px 10px;background:#F6F6F6;display:flex;align-items:center;justify-content:space-between;gap:8px;border-left:3px solid #3C7D88}.metrics span{font-size:9pt}.metrics strong{font-size:12pt;color:#34495E;white-space:nowrap}.charts{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:13px}.charts svg{width:100%;font-family:Arial,sans-serif}.tiny{font-size:8pt;line-height:1.35}.compact td,.compact th{padding:4px 6px}.compact th:first-child{width:46%}.coverage{border-top:1px solid #DCE3EB;margin-top:8px}.coverage p{font-size:8.5pt;line-height:1.35}.trip h1{font-size:18pt}.trip table td{padding:6px}.trip table{font-size:8.5pt}'
    css += ".reporthead{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;border-bottom:3px solid #59646F;margin-bottom:14px;padding-bottom:8px}.reporthead b{font-size:16pt;color:#34495E}.reporthead span{font-size:9pt;text-align:right}.trip td{white-space:pre-line}"
    css += " .cover .rule{background:#59646F}.metrics div:nth-child(6n+1),.metrics div:nth-child(6n+2){background:#F2F3F4;border-color:#40566D}.metrics div:nth-child(6n+3),.metrics div:nth-child(6n+4){background:#F2F3F4;border-color:#6F7C89}.metrics div:nth-child(6n+5),.metrics div:nth-child(6n+6){background:#F2F3F4;border-color:#59646F}.dashboard .compact th{background:#59646F}.trip table:nth-of-type(1) th{background:#40566D}.trip table:nth-of-type(2) th{background:#6F7C89}.trip table:nth-of-type(3) th{background:#52677A}.trip table:nth-of-type(4) th{background:#59646F}.trip h2{color:#59646F;border-color:#59646F}.collections h1{color:#59646F}.collections th{background:#59646F}.buses h1{color:#40566D}.buses th{background:#40566D}.crew h1{color:#6F7C89}.crew th{background:#6F7C89}.collections tr:nth-child(even){background:#F2F3F4}.buses tr:nth-child(even){background:#F2F3F4}.crew tr:nth-child(even){background:#F2F3F4}"
    css += ".print-toolbar{position:sticky;top:0;z-index:5;display:flex;justify-content:space-between;align-items:center;gap:18px;padding:14px 20px;background:#edf3f1;border-bottom:1px solid #baccc5;font:14px Arial,sans-serif;color:#233e36}.print-toolbar small{display:block;margin-top:4px}.print-toolbar button{border:0;border-radius:5px;padding:12px 18px;background:#22675f;color:#fff;font-weight:bold;cursor:pointer}.print-toolbar+section{margin-top:20px}@media print{.print-toolbar{display:none!important}.print-toolbar+section{margin-top:0}}"
    toolbar = '<aside class="print-toolbar"><div><strong>Save your report as PDF</strong><small>Click Print / Save as PDF, choose Save as PDF, then Save. Paper: Legal, portrait. Disable browser headers and footers.</small></div><button id="print-report" type="button">Print / Save as PDF</button></aside>'
    script = '<script data-smartbus-print>document.getElementById("print-report").addEventListener("click",function(){window.print();});</script>'
    return (
        '<!doctype html><html lang="'
        + lang
        + '"><meta charset="utf-8"><meta name="smartbus-report" content="1"><title>'
        + e(company)
        + " - "
        + e(period)
        + "</title><style>"
        + css
        + "</style><body>"
        + toolbar
        + body
        + script
        + "</body></html>"
    )
