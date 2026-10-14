"""Combine saved daily data using the simple Excel V5 layout."""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET
import re, uuid, json
from project_profile import APP_VERSION, load_profile

def col(n):
    out = ''
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out

def build_cells(books, start, end, lang='en', company=None, counter=None):
    if lang != 'en':
        raise ValueError('This release supports English only')
    from daily_system import ROOT, read_book, EPOCH
    from report_layout import summary, date_ranges
    from counter_accounting import counter_totals
    template = read_book(ROOT / f'Daily_Template_{lang}.xlsx')
    cells = {}
    for name, values in template.items():
        if name in ('Read the Manual', 'Settings', 'Route List'):
            cells[name] = values.copy()
        elif name == 'Dashboard':
            cells[name] = {r: v for r, v in values.items() if isinstance(v, str)}
        else:
            cells[name] = {r: v for r, v in values.items() if int(re.search('\\d+', r).group()) <= 5}

    def setrow(name, row, values):
        for i, v in enumerate(values, 1):
            if v is not None:
                cells[name][col(i) + str(row)] = v
    if books and 'route_list' in books[-1]:
        cells['Route List'] = books[-1]['route_list'].copy()
    company = company or load_profile(ROOT)['company_name']
    trips, s = summary(books)
    trips = sorted(trips, key=lambda t: (t['day'], t['start'] or datetime.min, str(t['trip'])))
    d = cells['Dashboard']
    d['A1'] = company
    d['K1'] = datetime.fromisoformat(str(start)).strftime('%d-%m-%Y') + ' — ' + datetime.fromisoformat(str(end)).strftime('%d-%m-%Y')
    for ref, val in [('F5', len(trips)), ('P5', int(s['seats'])), ('F8', s['gross']), ('P8', s['due']), ('F11', s['commission']), ('P11', s['outstanding']), ('F14', s['actual']), ('V151', s['due']), ('V152', s['commission'])]:
        d[ref] = val
    ct = counter_totals(books)
    for i, r in enumerate(ct[:6], 36):
        for ref, val in zip(['A', 'F', 'H', 'K', 'N', 'Q'], [r['counter'], r['seats'], r['commission'], r['due'], r['actual'], r['outstanding']]):
            d[ref + str(i)] = val
    for i, r in enumerate(ct[:4], 151):
        d['Z' + str(i)] = r['counter']
        d['AA' + str(i)] = r['seats']
    d['Z155'] = 'Other counters'
    d['AA155'] = sum((r['seats'] for r in ct[4:]), Decimal(0))
    all_days = [b['day'] for b in books]
    from datetime import date, timedelta
    a, z = (date.fromisoformat(str(start)), date.fromisoformat(str(end)))
    missing = [str(a + timedelta(days=i)) for i in range((z - a).days + 1) if str(a + timedelta(days=i)) not in all_days]
    digits = lambda x: str(x)
    d['A44'] = 'Dates with data: ' + digits(date_ranges(all_days))
    d['A46'] = 'Missing dates: ' + digits(date_ranges(missing))
    d['A48'] = 'Missing dates do not show how many trips were operated.'
    d['A50'] = 'Extra deposits: ' + digits(f"{s['extra']:,.2f}")
    cells['Settings'].update(B6=(datetime.fromisoformat(str(start)) - EPOCH).days, B8=company, B9='REPORT', B12='PERIOD_SNAPSHOT_V6', A13='End date', B13=datetime.fromisoformat(str(end)).strftime('%d-%m-%Y'))
    for i, t in enumerate(trips, 6):
        setrow('Trips', i, [t['trip'], t['coach'], t['start'], t['route'], t['direction'], t['bus'], t['driver'], t['driver_phone'], t['guide'], t['guide_phone'], t['conductor'], t['conductor_phone'], t['capacity'], t['seats'], t['gross'], t['commission'], t['due'], t['actual'] or Decimal(0), t['outstanding'], t['occupancy']])
    if any((book.get('ledger') for book in books)):
        cells['Trips']['U5'] = 'Permanent record ID'
        cells['Trips']['V5'] = 'Closed revision'
        metadata = {book['day']: book.get('ledger', {}) for book in books}
        for i, trip in enumerate(trips, 6):
            cells['Trips']['U' + str(i)] = trip.get('record_id', '')
            cells['Trips']['V' + str(i)] = metadata[trip['day']].get('revision', '')
        d['A52'] = 'Final report: closed ledger revisions. See the companion sources manifest.'
        pending = [book['day'] for book in books if book.get('ledger', {}).get('correction_pending')]
        if pending:
            d['A54'] = 'Corrections pending; previous closed values shown: ' + digits(date_ranges(pending))
    row = 6
    for b in books:
        tm = {t['trip']: t for t in b['trips']}
        gm = {(g['trip'], str(g['counter'])): g for g in b['counter_groups']}
        seen = set()
        for l in b['lines']:
            key = (l['trip'], str(l['counter']))
            t = tm.get(l['trip'], {})
            g = gm[key]
            setrow('Collections', row, [datetime.fromisoformat(b['day']), t.get('coach'), t.get('route'), l['trip'], l['counter'], l['kind'], l['seats'], l['fare'], l['fee'], l['gross'], l['commission'], l['net'], l['actual'], g['outstanding'] if key not in seen else None])
            seen.add(key)
            row += 1
    buses = {}
    crew = {}
    for b in books:
        people = {str(r[0]): r[2] for r in b['crew']}
        master = b.get('bus_master', {})
        for row in range(6, 106):
            bus = master.get('A' + str(row))
            driver = master.get('B' + str(row))
            if bus:
                buses[str(bus)] = [bus, driver, 62, people.get(str(driver))]
        for r in b['crew']:
            crew[str(r[0]), str(r[1]), str(r[2])] = r[:3]
    for i, r in enumerate(buses.values(), 6):
        setrow('Buses', i, r)
    for i, r in enumerate(crew.values(), 6):
        setrow('Crew', i, r)
    counter_master = {}
    for b in books:
        master = b.get('counter_master', {})
        for row in range(6, 106):
            name = master.get('A' + str(row))
            if name:
                counter_master[str(name)] = [name, master.get('B' + str(row))]
    for i, r in enumerate(counter_master.values(), 6):
        setrow('Counters', i, r)
    routes = defaultdict(lambda: [0, Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0)])
    for t in trips:
        vals = routes[str(t['route'])]
        vals[0] += 1
        for i, k in enumerate(['capacity', 'seats', 'gross', 'commission', 'due', 'actual', 'outstanding'], 1):
            vals[i] += t[k] or Decimal(0)
    for i, (name, vals) in enumerate(sorted(routes.items(), key=lambda x: -x[1][0]), 6):
        setrow('Routes', i, [name] + vals)
    for name in cells:
        if name not in ('Dashboard', 'Read the Manual'):
            cells[name]['A3'] = 'Saved period report. Update daily files, then regenerate.'

    def normal(v):
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, datetime):
            return (v.replace(tzinfo=None) - EPOCH).total_seconds() / 86400
        return v
    return {name: {r: normal(v) for r, v in values.items()} for name, values in cells.items()}

def make_period_excel(folder, start, end, lang='en', allow_demo=False, company=None, counter=None, report_folder=None):
    from daily_system import ROOT, collect, workbook_parts, set_cell, NS, tag
    if lang != 'en':
        raise ValueError('This release supports English only')
    books, missing, excluded = collect(folder, start, end, allow_demo, require_closed=True)
    maps = build_cells(books, start, end, lang, company, counter)
    with ZipFile(ROOT / f'Daily_Template_{lang}.xlsx') as z:
        files = {n: z.read(n) for n in z.namelist()}
    parts = workbook_parts(files)
    for name, part in parts.items():
        tree = ET.fromstring(files[part])
        styles = {c.get('r'): c.get('s') for c in tree.findall('.//s:c', NS)}
        data = tree.find('s:sheetData', NS)
        data.clear()
        grouped = defaultdict(list)
        for ref, value in maps[name].items():
            if value not in (None, ''):
                grouped[int(re.search('\\d+', ref).group())].append((ref, value))

        def number(ref):
            n = 0
            for ch in re.match('[A-Z]+', ref).group():
                n = n * 26 + ord(ch) - 64
            return n
        for r in sorted(grouped):
            row = ET.SubElement(data, tag('row'), {'r': str(r)})
            if name == 'Dashboard' and r >= 150:
                row.set('hidden', '1')
            for ref, value in sorted(grouped[r], key=lambda x: number(x[0])):
                cell = ET.SubElement(row, tag('c'), {'r': ref})
                letters = re.match('[A-Z]+', ref).group()
                fallback = letters + ('26' if name == 'Dashboard' and r >= 26 and (letters in list('ABCDEFGHIJ')) else '6')
                style = styles.get(ref, styles.get(fallback, styles.get('A5') if r == 5 else styles.get('A6')))
                if style is not None:
                    cell.set('s', style)
                if isinstance(value, (int, float)):
                    ET.SubElement(cell, tag('v')).text = str(value)
                else:
                    cell.set('t', 'inlineStr')
                    ET.SubElement(ET.SubElement(cell, tag('is')), tag('t')).text = str(value)
        for tagname in ('tableParts', 'dataValidations'):
            element = tree.find('s:' + tagname, NS)
            if element is not None:
                tree.remove(element)
        maximum = max((int(re.search('\\d+', ref).group()) for ref in maps[name]))
        for rule in tree.findall('s:conditionalFormatting', NS):
            rule.set('sqref', re.sub('105\\b', str(max(105, maximum)), rule.get('sqref', '')))
        dimension = tree.find('s:dimension', NS)
        if dimension is not None:
            dimension.set('ref', f'A1:AS{max(maximum, 20)}')
        if name in ('Trips', 'Collections', 'Buses', 'Crew', 'Counters', 'Routes'):
            af = tree.find('s:autoFilter', NS)
            if af is None:
                af = ET.Element(tag('autoFilter'))
                tree.insert(list(tree).index(data) + 1, af)
            last = {'Trips': 'V', 'Collections': 'N', 'Buses': 'D', 'Crew': 'C', 'Counters': 'B', 'Routes': 'I'}[name]
            af.set('ref', f'A5:{last}{max(6, maximum)}')
        if name == 'Trips' and 'U5' in maps[name]:
            columns = tree.find('s:cols', NS)
            if columns is not None:
                ET.SubElement(columns, tag('col'), {'min': '21', 'max': '21', 'width': '42', 'customWidth': '1'})
                ET.SubElement(columns, tag('col'), {'min': '22', 'max': '22', 'width': '20', 'customWidth': '1'})
        files[part] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    cns = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
    ctag = lambda x: '{' + cns['c'] + '}' + x
    for part in list(files):
        if not '/charts/chart' in part or not part.endswith('.xml'):
            continue
        chart = ET.fromstring(files[part])
        for refnode in chart.findall('.//c:numRef', cns) + chart.findall('.//c:strRef', cns):
            f = refnode.find('c:f', cns)
            if f is None or not f.text:
                continue
            m = re.fullmatch("'?([^']+)'?!\\$?([A-Z]+)\\$?(\\d+)(?::\\$?([A-Z]+)\\$?(\\d+))?", f.text)
            if not m:
                continue
            sheet, c1, r1, c2, r2 = m.groups()
            r2 = r2 or r1
            vals = [maps.get(sheet, {}).get(c1 + str(r), '') for r in range(int(r1), int(r2) + 1)]
            numeric = refnode.tag == ctag('numRef')
            cachetag = 'numCache' if numeric else 'strCache'
            for old in list(refnode):
                if old.tag == ctag(cachetag):
                    refnode.remove(old)
            cache = ET.SubElement(refnode, ctag(cachetag))
            if numeric:
                ET.SubElement(cache, ctag('formatCode')).text = 'General'
            ET.SubElement(cache, ctag('ptCount'), {'val': str(len(vals))})
            for i, v in enumerate(vals):
                point = ET.SubElement(cache, ctag('pt'), {'idx': str(i)})
                ET.SubElement(point, ctag('v')).text = str(v if v != '' else 0) if numeric else str(v)
        files[part] = ET.tostring(chart, encoding='utf-8', xml_declaration=True)
    out = Path(report_folder or ROOT / 'reports')
    out.mkdir(parents=True, exist_ok=True)
    target = out / f'Period_{start}_{end}_{lang}_{uuid.uuid4().hex[:6]}.xlsx'
    with ZipFile(target, 'x', ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    target.with_suffix('.sources.json').write_text(json.dumps(dict(application_version=APP_VERSION, start=str(start), end=str(end), missing=missing, sources=[dict(day=book['day'], file=Path(book['path']).name, ledger=book.get('ledger')) for book in books]), ensure_ascii=False, indent=2), encoding='utf-8')
    return target
