"""Reproducible public bus ridership research, separate from SmartBus accounts.

Uses the official Chicago Transit Authority open dataset. No fare, occupancy,
passenger identity or Bangladesh operating facts are inferred from ridership.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA_URL = "https://data.cityofchicago.org/resource/jyb9-n7fm.csv"
SOURCE_URL = "https://data.cityofchicago.org/Transportation/CTA-Ridership-Bus-Routes-Daily-Totals-by-Route/jyb9-n7fm"
TERMS_URL = "https://www.chicago.gov/city/en/narr/foia/data_disclaimer.html"
FIELDS = ("route", "date", "daytype", "rides")


def checked_range(start, end):
    """Bound downloads and analyses without quietly truncating input."""
    for value in (start, end):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Dates must use YYYY-MM-DD.")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if not 0 <= (last - first).days < 366:
        raise ValueError("Choose an ordered date range of at most 366 days.")
    return first, last


def load_rows(path):
    """Validate the original API CSV. Missing route-days are never invented."""
    result, seen = [], set()
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if len(reader.fieldnames or ()) != len(FIELDS) or set(
            reader.fieldnames or ()
        ) != set(FIELDS):
            raise ValueError(
                "Ridership CSV requires route, date, daytype and rides only."
            )
        for line, item in enumerate(reader, 2):
            if None in item or any(item.get(key) is None for key in FIELDS):
                raise ValueError(f"Malformed CSV row {line}.")
            route = item["route"].strip()
            raw_date = item["date"].strip()
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T00:00:00(?:\.000)?)?", raw_date):
                raise ValueError(f"Invalid date on row {line}.")
            day = date.fromisoformat(raw_date[:10]).isoformat()
            if not route or len(route) > 80 or any(ord(c) < 32 for c in route):
                raise ValueError(f"Invalid route on row {line}.")
            if item["daytype"] not in {"W", "A", "U"}:
                raise ValueError(f"Invalid daytype on row {line}.")
            if not re.fullmatch(r"\d+", item["rides"]):
                raise ValueError(f"Rides must be a non-negative integer on row {line}.")
            rides = int(item["rides"])
            if rides > 1_000_000_000:
                raise ValueError(
                    f"Ridership is outside the supported range on row {line}."
                )
            if (day, route) in seen:
                raise ValueError(f"Duplicate route/date on row {line}.")
            seen.add((day, route))
            result.append(
                dict(date=day, route=route, daytype=item["daytype"], rides=rides)
            )
            if len(result) > 200_000:
                raise ValueError("Ridership CSV exceeds the 200,000 row limit.")
    if not result:
        raise ValueError("Ridership CSV has no records.")
    result.sort(key=lambda row: (row["date"], row["route"]))
    checked_range(result[0]["date"], result[-1]["date"])
    return result


def rounded(value):
    return float(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def summarize(rows, source=None):
    """Chronological fixed holdout: all model inputs precede the test period."""
    rows = sorted(rows, key=lambda row: (row["date"], row["route"]))
    days = sorted({row["date"] for row in rows})
    if len(days) < 14:
        raise ValueError(
            "Research requires at least 14 observed dates for a seven-date holdout."
        )
    daily = defaultdict(int)
    by_route = defaultdict(list)
    daytypes = defaultdict(list)
    for row in rows:
        daily[row["date"]] += row["rides"]
        by_route[row["route"]].append(row)
        daytypes[row["daytype"]].append(row["rides"])
    train_end = days[-8]
    training = [row for row in rows if row["date"] <= train_end]
    test = [row for row in rows if row["date"] > train_end]
    history, latest = defaultdict(list), {}
    for row in training:
        history[(row["route"], row["daytype"])].append(row["rides"])
        latest[row["route"]] = row["rides"]
    predictions = []
    for row in test:
        values = history.get((row["route"], row["daytype"]))
        if not values or row["route"] not in latest:
            continue
        mean = Decimal(sum(values)) / len(values)
        baseline = latest[row["route"]]
        predictions.append(
            dict(
                **row,
                predicted=rounded(mean),
                baseline=baseline,
                absolute_error=rounded(abs(Decimal(row["rides"]) - mean)),
                baseline_absolute_error=abs(row["rides"] - baseline),
            )
        )
    count = len(predictions)
    if not count:
        raise ValueError(
            "No holdout rows have both route/daytype history and baseline history."
        )
    # MAE uses unrounded predictions. Round only the presentation/export boundary.
    model_mae = (
        sum(
            abs(
                Decimal(row["rides"])
                - Decimal(sum(history[(row["route"], row["daytype"])]))
                / len(history[(row["route"], row["daytype"])])
            )
            for row in test
            if history.get((row["route"], row["daytype"])) and row["route"] in latest
        )
        / count
    )
    baseline_mae = (
        Decimal(sum(row["baseline_absolute_error"] for row in predictions)) / count
    )
    return dict(
        source=source or {},
        period=dict(start=days[0], end=days[-1]),
        totals=dict(
            rows=len(rows),
            routes=len(by_route),
            rides=sum(daily.values()),
            observed_days=len(days),
        ),
        daily=[dict(day=day, rides=value) for day, value in sorted(daily.items())],
        routes=sorted(
            [
                dict(
                    route=route,
                    rides=sum(x["rides"] for x in items),
                    days=len(items),
                    average_daily_rides=rounded(
                        Decimal(sum(x["rides"] for x in items)) / len(items)
                    ),
                )
                for route, items in by_route.items()
            ],
            key=lambda row: (-row["rides"], row["route"]),
        ),
        daytypes=[
            dict(
                daytype=kind,
                rows=len(values),
                rides=sum(values),
                average_route_day_rides=rounded(Decimal(sum(values)) / len(values)),
            )
            for kind, values in sorted(daytypes.items())
        ],
        forecast=dict(
            method="Historical mean for the same route and CTA daytype",
            baseline="Last observed ridership for each route in the training period",
            train_start=days[0],
            train_end=train_end,
            test_start=days[-7],
            test_end=days[-1],
            mae=rounded(model_mae),
            baseline_mae=rounded(baseline_mae),
            evaluated_rows=count,
            excluded_rows=len(test) - count,
            predictions=predictions,
        ),
        limitations=[
            "Observed Chicago route-day boardings, not unique passengers or Bangladesh service data.",
            "No fares, capacity, GPS, expenses or profit are available in this dataset.",
            "Missing route-days are omitted, not assumed to be zero service or zero demand.",
            "The seven observed-date holdout is one retrospective evaluation, not a validated deployment forecast.",
        ],
    )


def write_atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix=".research_", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.replace(filename, path)
    finally:
        Path(filename).unlink(missing_ok=True)


def analyze(folder):
    folder = Path(folder)
    path = folder / "cta_ridership.csv"
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    source = json.loads((folder / "source.json").read_text(encoding="utf-8"))
    if source.get("sha256") != checksum:
        raise ValueError(
            "Research source checksum does not match source.json. Download or register the source again."
        )
    result = summarize(load_rows(path), source)
    result["data_sha256"] = checksum
    write_atomic(
        folder / "benchmark.json", (json.dumps(result, indent=2) + "\n").encode()
    )
    for filename, items, fields in (
        ("daily_summary.csv", result["daily"], ("day", "rides")),
        (
            "route_summary.csv",
            result["routes"],
            ("route", "rides", "days", "average_daily_rides"),
        ),
        (
            "forecast_predictions.csv",
            result["forecast"]["predictions"],
            (
                "date",
                "route",
                "daytype",
                "rides",
                "predicted",
                "baseline",
                "absolute_error",
                "baseline_absolute_error",
            ),
        ),
    ):
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(items)
        write_atomic(folder / filename, output.getvalue().encode("utf-8"))
    return result


def load_benchmark(root=ROOT):
    folder = Path(root) / "research"
    if not folder.is_dir():
        folder = ROOT / "research"
    # Recompute from the verified raw snapshot, rather than trusting edited summaries.
    source = json.loads((folder / "source.json").read_text(encoding="utf-8"))
    path = folder / "cta_ridership.csv"
    if hashlib.sha256(path.read_bytes()).hexdigest() != source.get("sha256"):
        raise ValueError(
            "The research dataset changed. Refresh the source manifest before analysis."
        )
    return summarize(load_rows(path), source)


def download(start, end, destination, replace=False):
    checked_range(start, end)
    folder = Path(destination)
    if (folder / "cta_ridership.csv").exists() and not replace:
        raise ValueError(
            "Dataset already exists. Use a new folder or --replace to refresh it."
        )
    collected, requests = [], []
    for offset in range(0, 200_001, 10_000):
        query = urlencode(
            {
                "$where": f"date >= '{start}T00:00:00' AND date <= '{end}T00:00:00'",
                "$order": "date,route",
                "$limit": 10_000,
                "$offset": offset,
            }
        )
        url = DATA_URL + "?" + query
        with urlopen(
            Request(url, headers={"User-Agent": "SmartBus-Research/1.3"}), timeout=45
        ) as response:
            data = response.read(20_000_001)
        if len(data) > 20_000_000:
            raise ValueError("Dataset response is too large.")
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        if len(reader.fieldnames or ()) != len(FIELDS) or set(
            reader.fieldnames or ()
        ) != set(FIELDS):
            raise ValueError("The public API schema changed. No dataset was saved.")
        chunk = list(reader)
        collected.extend(chunk)
        requests.append(url)
        if len(collected) > 200_000:
            raise ValueError(
                "Dataset exceeds supported row limit. Select a shorter period."
            )
        if len(chunk) < 10_000:
            break
    if not collected:
        raise ValueError("No public records found for the requested period.")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(collected)
    raw = buffer.getvalue().encode("utf-8")
    folder.mkdir(parents=True, exist_ok=True)
    # Validate staged content before replacing an existing snapshot.
    descriptor, name = tempfile.mkstemp(prefix=".validate_", dir=folder)
    os.close(descriptor)
    try:
        Path(name).write_bytes(raw)
        rows = load_rows(name)
        if any(not start <= row["date"] <= end for row in rows):
            raise ValueError(
                "The public API returned dates outside the requested period."
            )
        if len({row["date"] for row in rows}) < 14:
            raise ValueError(
                "Choose at least 14 observed dates for the research holdout."
            )
    finally:
        Path(name).unlink(missing_ok=True)
    source = dict(
        title="CTA - Ridership - Bus Routes - Daily Totals by Route",
        publisher="Chicago Transit Authority / City of Chicago Data Portal",
        url=SOURCE_URL,
        geography="Chicago, Illinois, United States",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        license="SEE_TERMS_OF_USE (City of Chicago portal terms)",
        terms_url=TERMS_URL,
        dataset_id="jyb9-n7fm",
        requested_period=dict(start=start, end=end),
        query_urls=requests,
        rows=len(rows),
        sha256=hashlib.sha256(raw).hexdigest(),
        grain="One observed date and bus route; rides are boardings",
        daytypes={"W": "Weekday", "A": "Saturday", "U": "Sunday/Holiday"},
    )
    write_atomic(folder / "cta_ridership.csv", raw)
    write_atomic(folder / "source.json", (json.dumps(source, indent=2) + "\n").encode())
    return analyze(folder)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser(
        "download", help="Download an official snapshot and generate analysis"
    )
    fetch.add_argument("--start", required=True)
    fetch.add_argument("--end", required=True)
    fetch.add_argument("--destination", type=Path, default=ROOT / "research")
    fetch.add_argument("--replace", action="store_true")
    analyze_command = commands.add_parser(
        "analyze", help="Reproduce results from the included snapshot"
    )
    analyze_command.add_argument("--folder", type=Path, default=ROOT / "research")
    args = parser.parse_args()
    try:
        result = (
            download(args.start, args.end, args.destination, args.replace)
            if args.command == "download"
            else analyze(args.folder)
        )
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"SmartBus research: {error}\n")
    print(
        json.dumps(
            {
                "period": result["period"],
                "totals": result["totals"],
                "forecast": {
                    key: value
                    for key, value in result["forecast"].items()
                    if key != "predictions"
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
