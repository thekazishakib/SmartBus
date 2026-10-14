"""Independent counter accounting; several fare groups may share one settlement."""
from collections import defaultdict, Counter
from decimal import Decimal
import re
FIRST_INPUT_ROW = 6
LAST_TRIP_ROW = 105
LAST_COLLECTION_ROW = 505
LAST_MASTER_ROW = 105
LAST_COACH_ROW = 305
LAST_FARE_ROW = 205
FROZEN_MARKER = 'SMARTBUS_FROZEN_V1'
REQUIRED_SHEETS = ('Settings', 'Trips', 'Collections', 'Buses', 'Crew', 'Counters', 'Route List')

def record_key(value):
    """Use the same key for an Excel numeric ID and its text representation."""
    if isinstance(value, (float, int)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()

def positive_integer(value, label):
    from daily_system import dec
    number = dec(value)
    if number is None or number < 1 or number != number.to_integral():
        raise ValueError(f'{label} must be a positive whole number')
    if number > 999999999999999:
        raise ValueError(f'{label} must be at most 15 digits')
    return int(number)

def input_records(book, sheet, columns, last_row=LAST_MASTER_ROW):
    cells = book[sheet]
    return [(row, [cells.get(f'{column}{row}') for column in columns]) for row in range(FIRST_INPUT_ROW, last_row + 1) if cells.get(f'{columns[0]}{row}') not in (None, '')]

def validate_saved_inputs(book):
    """Catch inputs that fixed worksheet ranges would otherwise discard."""
    from daily_system import dec, dt
    missing = [name for name in REQUIRED_SHEETS if name not in book]
    if missing:
        raise ValueError('Required worksheets missing: ' + ', '.join(missing))
    settings = book['Settings']
    if settings.get('B12') != 'AUTO_V6':
        raise ValueError('Use an Auto V6 daily file; keep older versions separately.')
    if not dt(settings.get('B6')):
        raise ValueError('Settings!B6: Invalid workbook date')
    tolerance = dec(settings.get('B7', 0))
    if tolerance is None or tolerance < 0:
        raise ValueError('Settings!B7: Invalid allowed difference')
    positive_integer(settings.get('B17', 1), 'Settings!B17 starting trip number')
    for cell, expected in [('B10', 62), ('B15', 50), ('B16', 0)]:
        if dec(settings.get(cell)) != expected:
            raise ValueError(f'Settings!{cell} must be {expected} for this workbook format')
    if settings.get('B9') not in ('LIVE', 'DEMO'):
        raise ValueError('Settings!B9 data type must be LIVE or DEMO')
    if settings.get('B11') != 'en':
        raise ValueError('Settings!B11 language must be English (en)')
    problems = []
    frozen = settings.get('B18') == FROZEN_MARKER
    allowed_columns = {'Trips': set(('A', 'B', 'C', 'D', 'E', 'F', 'G', 'I', 'K', 'N')), 'Collections': set(('D', 'E', 'G', 'M')) | ({'F', 'H'} if frozen else set()), 'Buses': {'A', 'B'}, 'Crew': {'A', 'B', 'C'}, 'Counters': {'A', 'B'}, 'Route List': {'A', 'B', 'C', 'F', 'G'}}
    last_rows = {'Trips': LAST_TRIP_ROW, 'Collections': LAST_COLLECTION_ROW, 'Buses': LAST_MASTER_ROW, 'Crew': LAST_MASTER_ROW, 'Counters': LAST_MASTER_ROW, 'Route List': LAST_COACH_ROW}
    for sheet, columns in allowed_columns.items():
        cells = book[sheet]
        for reference, value in cells.items():
            if value in (None, ''):
                continue
            match = re.fullmatch('([A-Z]+)(\\d+)', reference)
            if not match:
                continue
            column, row = (match[1], int(match[2]))
            if row < FIRST_INPUT_ROW:
                continue
            limit = LAST_FARE_ROW if sheet == 'Route List' and column in {'F', 'G'} else last_rows[sheet]
            if row > limit:
                problems.append(f'{sheet}!{reference}: input exceeds supported rows {FIRST_INPUT_ROW}–{limit}; move the entry into those rows')
            elif column not in columns:
                problems.append(f'{sheet}!{reference}: calculated or unsupported cell contains a manual value; restore its formula')
    for sheet, columns, end in [('Trips', ['B', 'C', 'E', 'F', 'I', 'K', 'A', 'D', 'G', 'N'], LAST_TRIP_ROW), ('Buses', ['A', 'B'], LAST_MASTER_ROW), ('Crew', ['A', 'B', 'C'], LAST_MASTER_ROW), ('Counters', ['A', 'B'], LAST_MASTER_ROW), ('Route List', ['A', 'B', 'C'], LAST_COACH_ROW), ('Route List', ['F', 'G'], LAST_FARE_ROW)]:
        for row in range(FIRST_INPUT_ROW, end + 1):
            if book[sheet].get(f'{columns[0]}{row}') in (None, '') and any((book[sheet].get(f'{column}{row}') not in (None, '') for column in columns[1:])):
                problems.append(f'{sheet}!{columns[0]}{row}: missing key for a populated row')
    for sheet, column, end in [('Buses', 'A', LAST_MASTER_ROW), ('Crew', 'A', LAST_MASTER_ROW), ('Counters', 'A', LAST_MASTER_ROW), ('Route List', 'A', LAST_COACH_ROW), ('Route List', 'F', LAST_FARE_ROW)]:
        seen = {}
        for row, (value,) in input_records(book, sheet, [column], end):
            key = record_key(value)
            if key in seen:
                problems.append(f'{sheet}!{column}{row}: duplicate master key {key!r} (also {column}{seen[key]})')
            seen[key] = row
    if problems:
        raise ValueError('Workbook input validation failed:\n- ' + '\n- '.join(problems))

def normalize_v5(book):
    """Recompute automatic fields from saved master inputs, not formula caches."""
    validate_saved_inputs(book)
    out = {name: values.copy() for name, values in book.items()}
    out['Settings']['B12'] = 'COMPANY_V4'
    buses = {record_key(v[0]): v[1] for _, v in input_records(book, 'Buses', ['A', 'B'])}
    coachmap = {record_key(v[0]): v[1:] for _, v in input_records(book, 'Route List', ['A', 'B', 'C'], LAST_COACH_ROW)}
    fares = {record_key(v[0]): v[1] for _, v in input_records(book, 'Route List', ['F', 'G'], LAST_FARE_ROW)}
    out['Buses'] = {}
    out['Crew'] = {}
    out['Routes'] = {}
    out['Trips'] = {}
    out['Collections'] = {}
    for i, (bus, driver) in enumerate(buses.items(), 6):
        out['Buses']['A' + str(i)] = bus
        out['Buses']['B' + str(i)] = 62
    for _, (name, role, phone) in input_records(book, 'Crew', ['A', 'B', 'C']):
        i = 6 + len(out['Crew']) // 3
        for col, val in zip('ABC', [name, role, phone]):
            out['Crew'][col + str(i)] = val
    for i, (route, fare) in enumerate(fares.items(), 6):
        out['Routes']['A' + str(i)] = route
    starting = positive_integer(book['Settings'].get('B17', 1), 'Settings!B17 starting trip number')
    last = starting - 1
    triprows = {}
    triproutes = {}
    for row, values in input_records(book, 'Trips', ['B', 'C', 'E', 'F', 'I', 'K']):
        coach, departure, direction, bus, guide, conductor = values
        number = book['Trips'].get('A' + str(row))
        if number in (None, ''):
            number = last + 1
        number = positive_integer(number, f'Trips!A{row} trip number')
        last = max(last, number)
        number = str(number)
        triprows[row] = number
        mapped = coachmap.get(record_key(coach), [None, None])
        route = mapped[1] if direction in ('Return',) else mapped[0]
        route = book['Trips'].get('D' + str(row), route)
        driver = book['Trips'].get('G' + str(row), buses.get(record_key(bus)))
        triproutes[number] = route
        for col, val in zip(['A', 'B', 'C', 'E', 'F', 'G', 'H', 'J', 'L'], [number, coach, departure, route, direction, bus, driver, guide, conductor]):
            if val is not None:
                out['Trips'][col + str(row)] = val
    frozen = book['Settings'].get('B18') == FROZEN_MARKER
    for row in range(FIRST_INPUT_ROW, LAST_COLLECTION_ROW + 1):
        c = book['Collections']
        counter = c.get('E' + str(row))
        seats = c.get('G' + str(row))
        actual = c.get('M' + str(row))
        if all((c.get(f'{col}{row}') in (None, '') for col in ('D', 'E', 'G', 'M', 'F', 'H'))):
            continue
        trip = c.get('D' + str(row), triprows.get(row))
        trip = record_key(trip) if trip is not None else None
        fare = fares.get(record_key(triproutes.get(trip)))
        if frozen and 'H' + str(row) in c:
            fare = c['H' + str(row)]
        kind = c.get('F' + str(row)) if frozen else None
        if trip is None:
            trip = '(missing)'
        for col, val in zip(['A', 'B', 'C', 'D', 'E', 'L'], [trip, counter, kind, seats, fare, actual]):
            if val is not None:
                out['Collections'][col + str(row)] = val
    return out

def calculate(path):
    from daily_system import read_book, rows, dt, dec, money
    saved = read_book(path)
    b = normalize_v5(saved)
    st = b['Settings']
    day = dt(st.get('B6'))
    if st.get('B12') != 'COMPANY_V4':
        raise ValueError('Use the new Counter V3 daily workbook. Older files have a different deposit rule.')
    if not day:
        raise ValueError('Invalid workbook date')
    day = str(day.date())
    tol = dec(st.get('B7', 0))
    if tol is None or tol < 0:
        raise ValueError('Invalid allowed difference')
    buses = rows(b['Buses'], ['A', 'B', 'C'], 105)
    crew = rows(b['Crew'], ['A', 'B', 'C', 'D'], 105)
    busmap = defaultdict(list)
    people = defaultdict(list)
    counters = defaultdict(list)
    for r in buses:
        busmap[str(r[0])].append(r)
    for r in crew:
        people[str(r[0])].append(r)
    for r in rows(b['Counters'], ['A', 'B', 'C'], 105):
        counters[str(r[0])].append(r)
    raw = rows(b['Trips'], list('ABCDEFGH') + ['J', 'L', 'Y', 'Z', 'AA', 'AD', 'AE'], 105)
    ids = Counter((str(r[0]) for r in raw))
    groups = {}
    lines = []
    for r in rows(b['Collections'], ['A', 'B', 'C', 'D', 'E', 'F', 'K', 'L', 'M', 'N'], LAST_COLLECTION_ROW):
        trip, counter, frozen_kind, n, fare, fee, cost, actual, sent, note = r
        trip = str(trip)
        issues = []
        match = counters[str(counter)]
        kind = frozen_kind if frozen_kind is not None else match[0][1] if len(match) == 1 else None
        seats = dec(n)
        price = dec(fare)
        rate = Decimal(0) if kind in ('Own',) else Decimal(50)
        expense = Decimal(0)
        received = dec(actual)
        transfer = dec(sent)
        if ids[trip] != 1:
            issues.append('Missing / duplicate trip')
        if seats is None or seats <= 0 or seats != seats.to_integral():
            issues.append('Invalid seats sold')
        if price is None or price < 0:
            issues.append('Invalid ticket fare')
        if kind not in ('Own', 'Commission'):
            issues.append('Unknown counter / type')
        if kind in ('Own',):
            comm = Decimal(0)
        else:
            if rate is None or rate < 0 or (price is not None and rate > price):
                issues.append('Invalid commission per ticket')
            comm = money(seats * rate) if seats is not None and rate is not None else None
        gross = money(seats * price) if seats is not None and price is not None else None
        if seats is not None and price is not None and (gross is None or comm is None):
            issues.append('Money amount exceeds supported precision')
        net = gross - comm if gross is not None and comm is not None else None
        if expense is None or expense < 0:
            issues.append('Invalid counter expense')
        due = net - expense if net is not None and expense is not None else None
        if actual not in (None, '') and (received is None or received < 0):
            issues.append('Invalid received money')
        if sent not in (None, '') and (transfer is None or transfer < 0):
            issues.append('Invalid office transfer')
        line = dict(trip=trip, counter=counter, kind=kind, seats=seats, fare=price, fee=rate, gross=gross, commission=comm, net=net, cost=expense, due=due, actual=received, sent_to_office=transfer, note=note, issues=issues)
        lines.append(line)
        key = (trip, str(counter))
        if key not in groups:
            groups[key] = dict(trip=trip, counter=counter, kind=kind, lines=[])
        groups[key]['lines'].append(line)
    for g in groups.values():
        ls = g['lines']
        g['issues'] = [message for l in ls for message in l['issues']]
        for field in ('seats', 'gross', 'commission', 'cost', 'net', 'due'):
            g[field] = sum((l[field] for l in ls), Decimal(0)) if all((l[field] is not None for l in ls)) else None
        for field in ('actual', 'sent_to_office'):
            vals = [l[field] for l in ls if l[field] is not None]
            g[field] = sum(vals, Decimal(0)) if vals else None
        if g['due'] is not None and g['due'] < 0:
            g['issues'].append('Counter expenses exceed its fare after commission')
        actual = g['actual']
        due = g['due']
        sent = g['sent_to_office']
        g['held_cash'] = None
        if sent is not None:
            if actual is None or sent > actual:
                g['issues'].append('Office transfer exceeds received money')
            else:
                g['held_cash'] = actual - sent
        g['outstanding'] = max(due - (actual or Decimal(0)), Decimal(0)) if due is not None else None
        g['extra_received'] = max((actual or Decimal(0)) - due, Decimal(0)) if due is not None else None
        g['variance'] = actual - due if actual is not None and due is not None else None
        g['applied'] = due - g['outstanding'] if due is not None else None
        g['status'] = 'CHECK' if g['issues'] else 'Deposit pending' if actual is None else 'Matched' if abs(g['variance']) <= tol else 'Short / extra'
    trips = []
    seen = Counter(((str(r[1]), str(r[2])) for r in raw))
    routes = {str(b['Routes'].get('A' + str(i))) for i in range(6, 206) if b['Routes'].get('A' + str(i))}
    for r in raw:
        ident, coach, departure, arrival, route, direction, bus, driver, guide, conductor, fuel, other, extra, previous, note = r
        ident = str(ident)
        start = dt(departure)
        end = dt(arrival)
        issues = []
        if ids[ident] != 1:
            issues.append('Duplicate trip number')
        if not coach:
            issues.append('Coach missing')
        if seen[str(coach), str(departure)] > 1:
            issues.append('Duplicate coach departure')
        if not start or str(start.date()) != day:
            issues.append('Departure does not match file date')
        if arrival not in (None, '') and (not end or not start or end < start):
            issues.append('Invalid arrival')
        if str(route) not in routes:
            issues.append('Unknown route')
        if direction not in ('Going', 'Return'):
            issues.append('Choose going / return')
        entries = busmap[str(bus)]
        capacity = dec(entries[0][1]) if len(entries) == 1 else None
        if capacity is None or capacity <= 0 or capacity != capacity.to_integral():
            issues.append('Invalid bus / seats')
        phones = []
        for name, roles in [(driver, ('Driver',)), (guide, ('Guide',)), (conductor, ('Conductor',))]:
            if not name and roles[0] != 'Driver':
                phones.append(None)
                continue
            person = people[str(name)]
            if len(person) != 1 or person[0][1] not in roles or (not person[0][2]):
                issues.append('Invalid staff: ' + str(name))
                phones.append(None)
            else:
                phones.append(str(person[0][2]))
        gs = [g for (trip, _), g in groups.items() if trip == ident]
        ls = [l for l in lines if l['trip'] == ident]

        def total(field, blank=False):
            vals = [g[field] for g in gs if g[field] is not None]
            return sum(vals, Decimal(0)) if vals else None if blank else Decimal(0)
        seats = total('seats')
        gross = total('gross')
        commission = total('commission')
        expense = total('cost')
        due = total('due', True)
        actual = total('actual', True)
        if capacity is not None and seats > capacity:
            issues.append('Sold seats exceed bus capacity')
        for g in gs:
            issues += [str(g['counter']) + ': ' + m for m in g['issues']]
        pending = sum((g['actual'] is None for g in gs))
        unmatched = any((g['status'] == 'Short / extra' for g in gs))
        status = 'CHECK' if issues else 'No collection' if not gs else 'Deposit pending' if pending else 'Short / extra' if unmatched else 'Matched'
        head = [dec(x) for x in (fuel, other, extra)]
        cost_issue = any((x not in (None, '') for x in (fuel, other, extra))) and (None in head or any((x < 0 for x in head if x is not None)))
        headcost = sum(head) if None not in head and (not cost_issue) else None
        trips.append(dict(day=day, trip=ident, coach=coach, start=start, end=end, route=route, direction=direction, bus=bus, driver=driver, driver_phone=phones[0], guide=guide, guide_phone=phones[1], conductor=conductor, conductor_phone=phones[2], capacity=capacity, seats=seats, gross=gross, commission=commission, counter_cost=expense, due=due, actual=actual, variance=actual - due if actual is not None and due is not None else None, outstanding=total('outstanding'), extra_received=total('extra_received'), applied=total('applied'), pending_counters=pending, occupancy=seats / capacity if capacity else None, status=status, time='Arrival pending' if not end else 'OK', data='CHECK' if issues else 'OK', fuel=head[0], other=head[1], extra=head[2], total_cost=headcost, after_cost=due - headcost if due is not None and headcost is not None else None, previous=previous, note=note, sent_to_office=total('sent_to_office', True), held_cash=total('held_cash', True), transfer_unknown=sum((g['actual'] is not None and g['sent_to_office'] is None for g in gs)), line_count=len(ls), counter_count=len(gs), cost_check='CHECK' if cost_issue else 'Not entered' if headcost is None else 'OK', issues=issues + (['Head office cost inputs incomplete'] if cost_issue else [])))
    for row, t in zip([r for r in range(6, 106) if saved['Trips'].get('B' + str(r)) not in (None, '')], trips):
        declared = saved['Trips'].get('N' + str(row))
        if declared is not None and dec(declared) != t['seats']:
            t['issues'].append('Entered sold seats do not match counter ticket totals')
            t['status'] = 'CHECK'
            t['data'] = 'CHECK'
    return dict(day=day, dataset=st.get('B9', 'LIVE'), trips=trips, lines=lines, counter_groups=list(groups.values()), buses=buses, crew=crew, orphan=[l for l in lines if ids[l['trip']] != 1], routes=rows(b['Routes'], ['A', 'B'], 205), path=str(path), route_list=b['Route List'], bus_master=saved['Buses'], counter_master=saved['Counters'])

def counter_totals(books):
    totals = {}
    for b in books:
        for g in b['counter_groups']:
            name = str(g['counter'])
            if name not in totals:
                totals[name] = dict(counter=name, kind=g['kind'], trips=set(), seats=Decimal(0), gross=Decimal(0), commission=Decimal(0), cost=Decimal(0), due=Decimal(0), actual=Decimal(0), outstanding=Decimal(0), extra_received=Decimal(0), held_cash=Decimal(0), pending=0)
            r = totals[name]
            r['trips'].add((b['day'], g['trip']))
            for field in ('seats', 'gross', 'commission', 'cost', 'due', 'actual', 'outstanding', 'extra_received', 'held_cash'):
                if g[field] is not None:
                    r[field] += g[field]
            r['pending'] += g['actual'] is None
    return sorted(totals.values(), key=lambda r: (-r['seats'], -r['gross'], r['counter']))
