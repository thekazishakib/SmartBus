"""SmartBus local workstation: daily workbooks, financial controls and reports.

Operator names record attribution, without authenticating a person. The server
binds only to loopback. All requests check Host/Origin; actions also require a
random session token. One mutation lock serializes writes across request threads.
"""

import argparse
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import html
import json
import logging
import os
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import parse_qs, urlencode, urlparse
import webbrowser

from daily_system import ROOT, create_daily, make_report, make_printable_report
from ledger_store import LedgerStore
from period_export import make_period_excel
from project_profile import APP_VERSION, load_profile

MAX_REQUEST_BYTES = 16_384
DAILY_NAME = re.compile(r"Daily_\d{4}-\d{2}-\d{2}_en\.xlsx\Z")
LOGGER = logging.getLogger(__name__)


class SmartBusServer(ThreadingHTTPServer):
    """One server owns one token, ledger and lock for all request threads."""

    daemon_threads = True

    def __init__(self, address, root=ROOT):
        self.root = Path(root).resolve()
        self.root.joinpath("daily").mkdir(parents=True, exist_ok=True)
        self.root.joinpath("reports").mkdir(exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        self.mutation_lock = threading.RLock()
        self.ledger = LedgerStore(root=self.root)
        self.profile = load_profile(self.root)
        super().__init__(address, Handler)

    @property
    def authorities(self):
        return {f"127.0.0.1:{self.server_port}", f"localhost:{self.server_port}"}


class Handler(BaseHTTPRequestHandler):
    server_version = "SmartBus"
    sys_version = ""

    def log_message(self, *_args):
        pass

    def send(self, content, status=200, ctype="text/html; charset=utf-8", nonce=None):
        data = content.encode("utf-8") if isinstance(content, str) else content
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        policy = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        if nonce:
            policy += (f"; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'"
                       "; connect-src 'self'")
        self.send_header("Content-Security-Policy", policy)
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value, status=200):
        self.send(json.dumps(value, ensure_ascii=False), status,
                  "application/json; charset=utf-8")

    def local_request(self):
        if len(self.headers.get_all("Host", [])) != 1 or self.headers.get("Host", "").lower() not in self.server.authorities:
            return False
        origin = self.headers.get("Origin")
        if origin:
            try:
                parsed = urlparse(origin)
            except ValueError:
                return False
            if (parsed.scheme != "http" or parsed.netloc.lower() not in self.server.authorities
                    or parsed.path or parsed.params or parsed.query or parsed.fragment):
                return False
        return self.headers.get("Sec-Fetch-Site") not in {"cross-site", "same-site"}

    def token_valid(self):
        supplied = self.headers.get("X-SmartBus-Token", "")
        return (len(self.headers.get_all("X-SmartBus-Token", [])) == 1
                and bool(supplied) and secrets.compare_digest(supplied.encode("utf-8"), self.server.token.encode("ascii")))

    def do_GET(self):
        if not self.local_request():
            self.send_json({"message": "Local requests only."}, 403)
            return
        url = urlparse(self.path)
        if url.path == "/":
            nonce = secrets.token_urlsafe(24)
            self.send(render_page(self.server.token, nonce, load_profile(self.server.root)), nonce=nonce)
            return
        if url.path in {"/api/status", "/api/audit"}:
            if not self.token_valid():
                self.send_json({"message": "Open SmartBus to start a local session."}, 403)
                return
            try:
                with self.server.mutation_lock:
                    if url.path == "/api/status":
                        result = {
                            "days": self.server.ledger.status(),
                            "files": sorted((p.name for p in self.server.root.joinpath("daily").glob("Daily_*.xlsx")
                                             if DAILY_NAME.fullmatch(p.name)), reverse=True),
                            "backups": sorted((p.name for p in self.server.root.joinpath("backups").glob("*.sqlite3")), reverse=True),
                        }
                    else:
                        result = {"events": self.server.ledger.audit(limit=100)}
                self.send_json(result)
            except Exception:
                LOGGER.exception("Cannot load workstation state")
                self.send_json({"message": "Could not load records. Check the local console and try again."}, 500)
            return
        if url.path == "/file":
            names = parse_qs(url.query).get("name", [])
            try:
                candidate = (self.server.root / names[0]).resolve() if len(names) == 1 else None
            except (ValueError, OSError):
                candidate = None
            report_root = (self.server.root / "reports").resolve()
            if (candidate is None or candidate.parent != report_root
                    or candidate.suffix.lower() not in {".pdf", ".xlsx", ".html"} or not candidate.is_file()):
                self.send("Report not found", 404, "text/plain; charset=utf-8")
                return
            if candidate.suffix.lower() == '.html':
                page = candidate.read_text(encoding='utf-8')
                if '<meta name="smartbus-report" content="1">' not in page:
                    self.send('Report not found', 404, 'text/plain; charset=utf-8')
                    return
                nonce = secrets.token_urlsafe(24)
                page = page.replace('<style>', f'<style nonce="{nonce}">', 1)
                page = page.replace('<script data-smartbus-print>', f'<script nonce="{nonce}">', 1)
                self.send(page, nonce=nonce)
                return
            ctype = "application/pdf" if candidate.suffix.lower() == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            self.send(candidate.read_bytes(), ctype=ctype)
            return
        self.send("Not found", 404, "text/plain; charset=utf-8")

    def do_POST(self):
        if not self.local_request() or not self.token_valid():
            self.send_json({"message": "Request rejected. Reopen the SmartBus page and try again."}, 403)
            return
        if self.path != "/action":
            self.send_json({"message": "Unknown endpoint."}, 404)
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self.send_json({"message": "JSON requests are required."}, 415)
            return
        raw_length = self.headers.get("Content-Length", "")
        if (self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1
                or not raw_length.isascii() or not raw_length.isdecimal()):
            self.send_json({"message": "A valid request length is required."}, 400)
            return
        length = int(raw_length)
        if not 0 < length <= MAX_REQUEST_BYTES:
            self.send_json({"message": "Request size is outside the supported limit."}, 413)
            return
        try:
            values = json.loads(self.rfile.read(length))
            if not isinstance(values, dict):
                raise ValueError("Request must be a JSON object.")
            with self.server.mutation_lock:
                result = self.perform_action(values)
            self.send_json(result)
        except (ValueError, KeyError, UnicodeDecodeError) as error:
            message = str(error) if isinstance(error, ValueError) else "A required field is missing or invalid."
            self.send_json({"message": "Not completed: " + message}, 400)
        except Exception:
            LOGGER.exception("Local action failed")
            self.send_json({"message": "Could not complete the action. Check the local console and try again."}, 500)

    def daily_path(self, name):
        if not isinstance(name, str) or not DAILY_NAME.fullmatch(name):
            raise ValueError("Choose a saved daily workbook.")
        path = (self.server.root / "daily" / name).resolve()
        if path.parent != (self.server.root / "daily").resolve() or not path.is_file():
            raise ValueError("Daily workbook was not found.")
        return path

    def perform_action(self, values):
        language = checked_language(values)
        action = values.get("action")
        actor = clean_text(values.get("actor", "Local operator"), "Operator", 80)
        ledger = self.server.ledger
        if action == "new":
            path = create_daily(checked_day(values["date"]), language, folder=self.server.root / "daily")
            os.startfile(path)
            return {"message": "Workbook created: " + path.name}
        if action == "open":
            path = self.daily_path(values["name"])
            os.startfile(path)
            return {"message": "Opening Excel: " + path.name}
        if action == "folder":
            os.startfile(self.server.root / "daily")
            return {"message": "Daily workbook folder opened."}
        if action in {"combined", "report", "printable"}:
            start, end = checked_day(values["start"]), checked_day(values["end"])
            if start > end:
                raise ValueError("Start date must be on or before end date.")
            company = clean_text(values.get("company", load_profile(self.server.root)['company_name']), "Company", 120)
            report_function = {'report':make_report, 'combined':make_period_excel, 'printable':make_printable_report}[action]
            path = report_function(self.server.root / "daily", start, end,
                                   language, company=company,
                                   counter=values.get("counter"), report_folder=self.server.root / "reports")
            message = 'Printable report saved. Open it, click Print / Save as PDF, choose Save as PDF, then Save.' if action == 'printable' else 'Final report saved: ' + path.name
            return {"message": message,
                    "url": "/file?" + urlencode({"name": "reports/" + path.name})}
        if action == "ledger_import":
            data = ledger.import_workbook(self.daily_path(values["name"]), actor=actor)
            return {"message": "Workbook imported. Review this day before closing.", "data": data}
        if action == "ledger_review":
            data = ledger.review_day(checked_day(values["day"]), actor=actor)
            return {"message": "Review passed. The day can now be closed.", "data": data}
        if action == "ledger_close":
            data = ledger.close_day(checked_day(values["day"]), actor=actor)
            return {"message": "Day closed. Its snapshot is available for final reports.", "data": data}
        if action == "ledger_correct":
            reason = clean_text(values.get("reason", ""), "Correction reason", 500)
            data = ledger.begin_correction(checked_day(values["day"]), actor=actor, reason=reason)
            return {"message": "Correction opened. Edit and save Excel, then import, review and close again.", "data": data}
        if action == "backup":
            path = ledger.backup()
            return {"message": "Backup saved: " + Path(path).name}
        if action == "restore":
            name = clean_text(values.get("name", ""), "Backup name", 160)
            if Path(name).name != name or "/" in name or "\\" in name or not name.endswith(".sqlite3"):
                raise ValueError("Choose a listed backup.")
            data = ledger.restore_backup(name, actor=actor)
            return {"message": "Backup restored. Check your daily review before continuing.", "data": data}
        raise ValueError("Unknown action.")


def clean_text(value, field, limit):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit or any(ord(c) < 32 for c in value):
        raise ValueError(f"{field} must contain 1–{limit} readable characters.")
    return value.strip()


def checked_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Choose a valid date.")
    return date.fromisoformat(value).isoformat()


def checked_language(values):
    language = values.get("language", "en")
    if language != "en":
        raise ValueError("Only English is supported in this edition.")
    return language


def render_page(token, nonce, profile=None):
    profile = profile or load_profile()
    page = PAGE.replace("__TOKEN__", json.dumps(token)).replace("__NONCE__", html.escape(nonce, quote=True)).replace("__TODAY__", date.today().isoformat())
    for key in ('project_name', 'tagline', 'company_name', 'default_operator', 'author', 'accent_color'):
        page = page.replace('__' + key.upper() + '__', html.escape(profile[key], quote=True))
    return page.replace('__VERSION__', APP_VERSION)


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__PROJECT_NAME__ · Finance workstation</title>
<style nonce="__NONCE__">
:root{--navy:#142d39;--teal:__ACCENT_COLOR__;--ink:#193744;--muted:#536b76;--line:#d7e2e4;--paper:#f3f6f4;--gold:#946319}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 "Segoe UI",Arial,sans-serif}button,input,select{font:inherit}button,a,input,select{touch-action:manipulation}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #deac4c;outline-offset:3px}
a{color:var(--teal)}.shell{display:grid;grid-template-columns:232px minmax(0,1fr);min-height:100vh}.sidebar{background:var(--navy);color:#fff;padding:32px 24px;position:sticky;top:0;height:100vh}.brand{font-size:28px;font-weight:750;letter-spacing:-1px}.brand span{color:#8ad4bd}.subbrand{font-size:12px;color:#b2c8d0;letter-spacing:1.5px;text-transform:uppercase;margin-top:4px}.nav{display:grid;gap:8px;margin:38px 0}.nav a{color:#d7e6ea;padding:10px 12px;text-decoration:none;border-radius:6px}.nav a:hover,.nav a.active{background:#294653;color:#fff}.local{font-size:12px;border-top:1px solid #405966;padding-top:18px;color:#bed2d9}.dot{display:inline-block;width:7px;height:7px;background:#88d2ab;border-radius:50%;margin-right:7px}.workspace{padding:32px 40px 50px;max-width:1500px;width:100%;margin:auto}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:25px;margin-bottom:24px}.eyebrow{font-size:11px;font-weight:750;text-transform:uppercase;letter-spacing:1.8px;color:var(--teal)}h1{font-size:30px;line-height:1.2;margin:7px 0 9px;letter-spacing:-.6px}h2{font-size:19px;margin:0 0 3px}h3{font-size:15px;margin:0 0 6px}p{margin:0 0 12px}.muted{color:var(--muted)}.date-tag{white-space:nowrap;border:1px solid var(--line);background:#fff;padding:8px 12px;border-radius:6px;color:var(--muted)}.steps{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 22px}.step{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}.step b{display:grid;place-items:center;background:#e3ece8;color:var(--teal);width:24px;height:24px;border-radius:50%;font-size:12px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:24px}.metric,.card{background:#fff;border:1px solid var(--line);border-radius:9px}.metric{padding:17px 19px}.metric small{display:block;color:var(--muted);font-size:12px}.metric strong{display:block;font-size:27px;font-weight:650;line-height:1.4}.metric.warn strong{color:var(--gold)}.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:20px}.card{padding:22px;margin-bottom:22px;scroll-margin-top:20px}.card-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}.card-head p{margin:0;font-size:13px}.section-number{font-size:11px;color:var(--teal);font-weight:750;letter-spacing:1px;text-transform:uppercase;margin-bottom:5px}.fields{display:flex;gap:14px;flex-wrap:wrap}.field{display:flex;flex:1 1 160px;flex-direction:column;gap:6px;margin-bottom:16px}label{font-size:12px;font-weight:650}input,select{width:100%;min-width:0;background:#fff;color:var(--ink);border:1px solid #a8bcc3;border-radius:5px;padding:10px 11px}input:disabled{background:#f1f4f5;color:#627a85}.actions{display:flex;gap:9px;flex-wrap:wrap;margin:3px 0 12px}button{cursor:pointer;border-radius:5px;padding:9px 14px;border:1px solid var(--teal);background:var(--teal);color:#fff;font-weight:600;font-size:13px}button.secondary{background:#fff;color:var(--ink);border-color:#b8c9ce}button.small{padding:6px 9px;font-size:12px}button:disabled{opacity:.5;cursor:wait}.help{font-size:12px;color:var(--muted);line-height:1.65;margin:0}.notice{padding:13px 16px;border-left:3px solid #6a9f8c;border-radius:4px;background:#eaf2ed;font-size:13px;margin-bottom:22px;overflow-wrap:anywhere}.notice.error{background:#fff0e8;border-color:#b35b36;color:#813c21}.notice.busy{background:#fff8e8;border-color:#c6a353}.notice a{display:inline-block;margin:6px 0 0;font-weight:650}.table-wrap{overflow:auto;margin-top:15px}table{border-collapse:collapse;width:100%;text-align:left;font-size:13px}th{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.7px;background:#f6f8f8;padding:11px 12px;white-space:nowrap}td{padding:13px 12px;border-top:1px solid #e4ebed;vertical-align:top}td small{display:block;font-size:11px;color:var(--muted)}.pill{display:inline-block;border-radius:4px;padding:3px 7px;font-size:10px;text-transform:uppercase;font-weight:750;letter-spacing:.5px;background:#edf0f3;color:#516775}.pill.closed{background:#e1f1e8;color:#1c6845}.pill.reviewed{background:#e3eef8;color:#275d83}.pill.correction{background:#fff0d4;color:#895d17}.pending{color:#9c582d;font-size:11px;margin-top:5px;max-width:250px}.row-actions{display:flex;gap:6px;flex-wrap:wrap;min-width:150px}.empty{padding:30px;color:var(--muted);text-align:center}.wide{grid-column:1/-1}.operator{max-width:250px;margin:0}.operator small{font-weight:400;font-size:10px;color:var(--muted)}.footer{color:var(--muted);font-size:11px;display:flex;justify-content:space-between;gap:15px}.backup-note{margin-top:14px;padding-top:14px;border-top:1px solid var(--line)}details summary{cursor:pointer;font-size:13px;color:var(--muted)}
@media(max-width:1100px){.workspace{padding:26px 24px}.shell{grid-template-columns:195px minmax(0,1fr)}.sidebar{padding:28px 18px}.grid{grid-template-columns:1fr}}
@media(max-width:760px){.shell{display:block}.sidebar{position:static;height:auto;padding:16px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}.brand{font-size:23px}.subbrand,.local{display:none}.nav{display:flex;flex-wrap:wrap;width:100%;justify-content:space-between;margin:0;gap:0;font-size:12px}.nav a{padding:6px 9px}.workspace{padding:22px 16px}.top{display:block}.date-tag{display:inline-block;margin-top:8px;font-size:12px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.metric{padding:13px 15px}.metric strong{font-size:24px}.card{padding:18px}.card-head{align-items:flex-start;flex-wrap:wrap}h1{font-size:27px}.operator{max-width:none;flex-basis:100%}.footer{display:block}}
</style></head>
<body><div class="shell"><aside class="sidebar"><div><div class="brand">__PROJECT_NAME__</div><div class="subbrand">Finance workstation</div></div><nav class="nav" aria-label="Main navigation"><a class="active" href="#daily">Daily work</a><a href="#reports">Reports</a><a href="#recovery">Recovery</a><a href="#audit">Activity</a></nav><div class="local"><p><span class="dot"></span>Local workstation</p><p>Records stay on this computer.</p></div></aside>
<main class="workspace"><header class="top"><div><div class="eyebrow">Operations · Reconciliation · Reporting</div><h1>__PROJECT_NAME__ finance workstation</h1><p class="help">__TAGLINE__</p></div><div class="date-tag">__TODAY__ · Single workstation</div></header>
<div class="steps" aria-label="Daily workflow"><span class="step"><b>1</b> Save Excel</span><span class="step"><b>2</b> Import</span><span class="step"><b>3</b> Review</span><span class="step"><b>4</b> Close day</span><span class="step"><b>5</b> Final report</span></div>
<div class="metrics" aria-label="Workstation overview"><div class="metric"><small>Daily workbooks</small><strong id="metric-files">—</strong></div><div class="metric warn"><small>Awaiting review / close</small><strong id="metric-pending">—</strong></div><div class="metric"><small>Closed days</small><strong id="metric-closed">—</strong></div><div class="metric"><small>Recovery copies</small><strong id="metric-backups">—</strong></div></div>
<div id="result" class="notice" role="status" aria-live="polite">Loading local records…</div>
<div class="grid"><section class="card" id="daily"><div class="section-number">01 · Record</div><h2>Start the day</h2><form id="daily-form"><div class="fields"><div class="field"><label for="day">Departure date</label><input id="day" type="date" value="__TODAY__" required></div></div><div class="actions"><button type="submit">Create & open Excel</button><button type="button" class="secondary" id="folder">Open daily folder</button></div></form><p class="help">Save your entries in Excel before importing. Each date has one workbook; existing files are preserved. Master lists carry forward to the next day.</p></section>
<section class="card" id="reports"><div class="section-number">03 · Report</div><h2>Publish a final report</h2><form id="report-form"><div class="fields"><div class="field"><label for="company">Company</label><input id="company" value="__COMPANY_NAME__" maxlength="120" required></div><div class="field"><label for="period">Period</label><select id="period"><option value="30">Last 30 days</option><option value="1">One day</option><option value="custom">Custom</option></select></div></div><div class="fields"><div class="field"><label for="start">Start</label><input id="start" type="date" required></div><div class="field"><label for="end">End</label><input id="end" type="date" value="__TODAY__" required></div></div><div class="actions"><button type="submit">Export Excel</button><button type="button" id="printable">Open printable report</button><button type="button" class="secondary" id="pdf">Automatic PDF</button></div></form><p class="help">Final reports use closed ledger snapshots. Import, review and close every recorded day in the period first. An open correction keeps its previous closed snapshot until the replacement closes. For PDF: open the printable report, click Print / Save as PDF, choose Save as PDF, then Save. Automatic PDF additionally requires Microsoft Edge.</p></section>
<section class="card wide" id="review"><div class="card-head"><div><div class="section-number">02 · Verify & close</div><h2>Daily review</h2></div><div class="field operator"><label for="actor">Operator <small>Attribution, no sign-in</small></label><input id="actor" value="__DEFAULT_OPERATOR__" maxlength="80" required></div><button type="button" class="secondary small" id="refresh">Refresh</button></div><p class="help">Review requires valid trips, linked counter records and an entered receipt for each active counter. Enter 0 for a known zero receipt; leave nothing unknown. Outstanding balances may remain. To change a closed day, open a correction with a reason, save Excel, then import, review and close again.</p><div class="table-wrap"><table><thead><tr><th>Date & workbook</th><th>Financial state</th><th>Imported amounts</th><th>Revision</th><th>Actions</th></tr></thead><tbody id="days"><tr><td colspan="5" class="empty">Loading…</td></tr></tbody></table></div></section>
<section class="card" id="recovery"><div class="section-number">04 · Recover</div><h2>Backups & recovery</h2><p class="help">Back up the ledger before important changes. Keep a separate copy of the project folder to protect daily Excel files and reports too.</p><div class="actions"><button type="button" id="backup">Create verified backup</button></div><details class="backup-note"><summary>Restore a saved ledger</summary><div class="field"><label for="backup-name">Available backups</label><select id="backup-name"><option value="">No backups yet</option></select></div><button type="button" class="secondary" id="restore">Restore selected backup</button><p class="help">Restoring replaces the current ledger. Daily Excel files remain separate; check their dates and contents before importing again.</p></details></section>
<section class="card" id="audit"><div class="card-head"><div><div class="section-number">05 · Trace</div><h2>Recent activity</h2></div></div><p class="help">The latest 100 recorded ledger events. Operator names support traceability on this local workstation.</p><div class="table-wrap"><table><thead><tr><th>When / who</th><th>Event</th></tr></thead><tbody id="events"><tr><td colspan="2" class="empty">Loading…</td></tr></tbody></table></div></section></div><footer class="footer"><span>__PROJECT_NAME__ v__VERSION__ · Built by __AUTHOR__</span><span>Save → Import → Review → Close → Report</span></footer></main></div>
<script nonce="__NONCE__">
'use strict';
const TOKEN=__TOKEN__;
const $=id=>document.getElementById(id);
let busy=false;
function notice(message,error=false){$('result').className='notice'+(error?' error':'');$('result').textContent=message;}
function setBusy(value){busy=value;document.querySelectorAll('button').forEach(button=>button.disabled=value);$('result').setAttribute('aria-busy',String(value));}
function node(tag,text,className){const element=document.createElement(tag);if(text!==undefined)element.textContent=String(text);if(className)element.className=className;return element;}
async function read(url){const response=await fetch(url,{headers:{'X-SmartBus-Token':TOKEN}});const value=await response.json();if(!response.ok)throw new Error(value.message||'Could not load records.');return value;}
async function refresh(){
  const [state,activity]=await Promise.allSettled([read('/api/status'),read('/api/audit')]);
  if(state.status==='rejected')throw state.reason;
  drawState(state.value);
  if(activity.status==='fulfilled'){drawAudit(activity.value.events);return '';}
  drawAudit([]);
  $('events').firstElementChild.firstElementChild.textContent='Activity log unavailable. Restore a verified backup if the ledger is damaged.';
  return 'Activity log unavailable. Recovery controls remain available.';
}
async function call(action,values={}){
  if(busy)return;setBusy(true);$('result').className='notice busy';$('result').textContent='Working…';
  try{
    const response=await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json','X-SmartBus-Token':TOKEN},body:JSON.stringify({action,actor:$('actor').value,...values})});
    const value=await response.json();notice(value.message,!response.ok);
    if(value.url){const link=node('a',action==='printable'?'Open report — Print / Save as PDF':action==='report'?'Open PDF':'Download Excel');link.href=value.url;link.target='_blank';link.rel='noopener';$('result').append(document.createElement('br'),link);}
    const warning=await refresh();if(warning)$('result').append(document.createElement('br'),node('small',warning));return value;
  }catch(error){notice(error.message||'Connection lost. Check the local application window.',true);}finally{setBusy(false);}
}
function button(label,action,secondary=false){const element=node('button',label,'small'+(secondary?' secondary':''));element.type='button';element.disabled=busy;element.addEventListener('click',action);return element;}
function amount(value){const number=Number(value);return value===undefined||value===null||!Number.isFinite(number)?'—':number.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});}
function drawState(state){
  const rows=new Map((state.days||[]).map(day=>[day.day,{...day}]));
  for(const file of state.files||[]){const day=file.slice(6,16);if(rows.has(day)){rows.get(day).file=file;}else{rows.set(day,{day,status:'unimported',file});}}
  const body=$('days');body.replaceChildren();
  for(const row of [...rows.values()].sort((a,b)=>b.day.localeCompare(a.day))){
    const tr=node('tr');const file=row.file||row.source_name;const first=node('td');first.append(node('strong',row.day||'Ledger recovery required'),node('small',file||'Workbook not found'));
    const finance=node('td');const status=String(row.status||'draft').toLowerCase();
    const correction=Boolean(row.published_revision&&status!=='closed');
    finance.append(node('span',correction?'correction · '+status:status.replaceAll('_',' '),'pill '+(correction?'correction':['closed','reviewed'].includes(status)?status:'')));
    if(row.stale&&status!=='recovery_required')finance.append(node('div','Workbook changed or missing. Import the saved file before review; closed days require a correction.','pending'));
    const issues=[...(Array.isArray(row.errors)?row.errors:[]),...(Array.isArray(row.warnings)?row.warnings:[])];
    if(issues.length)finance.append(node('div',issues.map(issue=>typeof issue==='string'?issue:issue.message||JSON.stringify(issue)).join(' · '),'pending'));
    const amounts=node('td');amounts.append(node('strong','Gross '+amount(row.gross)),node('small','Outstanding '+amount(row.outstanding)));
    if(row.trip_count!==undefined)amounts.append(node('small',row.trip_count+' trips · '+(row.pending_counters||0)+' blank receipts'));
    const revision=node('td',row.revision?'r'+row.revision:'—');if(row.published_revision)revision.append(node('small','Final: r'+row.published_revision));
    const actions=node('div',undefined,'row-actions');
    if(row.file){actions.append(button('Open Excel',()=>call('open',{name:row.file}),true));if(status!=='closed')actions.append(button('Import',()=>call('ledger_import',{name:row.file}),true));}
    if((status==='draft'||status==='correction')&&!row.needs_import&&!row.stale)actions.append(button('Review',()=>call('ledger_review',{day:row.day})));
    if(status==='reviewed'&&!row.stale)actions.append(button('Close day',()=>{if(window.confirm('Close '+row.day+'? Its imported values will become the final report snapshot.'))call('ledger_close',{day:row.day});}));
    if(status==='closed')actions.append(button('Correct',()=>{const reason=window.prompt('Reason for correcting '+row.day+'');if(reason!==null&&reason.trim())call('ledger_correct',{day:row.day,reason});},true));
    const last=node('td');last.append(actions);tr.append(first,finance,amounts,revision,last);body.append(tr);
  }
  if(!rows.size){const tr=node('tr');const td=node('td','Create your first daily workbook to begin.','empty');td.colSpan=5;tr.append(td);body.append(tr);}
  $('metric-files').textContent=(state.files||[]).length;$('metric-pending').textContent=[...rows.values()].filter(row=>row.status!=='closed').length;$('metric-closed').textContent=(state.days||[]).filter(row=>row.status==='closed').length;$('metric-backups').textContent=(state.backups||[]).length;
  const select=$('backup-name');const selected=select.value;select.replaceChildren();for(const backup of state.backups||[]){const option=node('option',backup);option.value=backup;select.append(option);}
  if(!select.options.length){const option=node('option','No backups yet');option.value='';select.append(option);}else if((state.backups||[]).includes(selected))select.value=selected;
}
function drawAudit(events){
  const body=$('events');body.replaceChildren();
  for(const event of events||[]){
    const tr=node('tr');const timestamp=event.occurred_at||event.created_at||event.timestamp||event.at||'';const parsed=new Date(timestamp);
    const when=Number.isNaN(parsed.getTime())?timestamp:new Intl.DateTimeFormat('en-US',{dateStyle:'short',timeStyle:'short'}).format(parsed);
    const who=node('td',when);who.append(node('small',event.actor||'Local operator'));
    const what=node('td',[event.action||event.event||'Event',event.day||'',event.revision?'r'+event.revision:''].filter(Boolean).join(' · '));
    const reason=event.reason||(event.details||{}).reason;if(reason)what.append(node('small',reason));tr.append(who,what);body.append(tr);
  }
  if(!body.children.length){const tr=node('tr');const td=node('td','No ledger activity yet.','empty');td.colSpan=2;tr.append(td);body.append(tr);}
}
function dates(){const period=$('period').value;$('start').disabled=period!=='custom';if(period==='custom')return;const end=new Date($('end').value+'T12:00:00Z');if(Number.isNaN(end.getTime()))return;end.setUTCDate(end.getUTCDate()-Number(period)+1);$('start').value=end.toISOString().slice(0,10);}
function report(action){if(!$('report-form').reportValidity())return;call(action,{start:$('start').value,end:$('end').value,language:'en',company:$('company').value});}
$('daily-form').addEventListener('submit',event=>{event.preventDefault();call('new',{date:$('day').value,language:'en'});});$('report-form').addEventListener('submit',event=>{event.preventDefault();report('combined');});$('pdf').addEventListener('click',()=>report('report'));$('printable').addEventListener('click',()=>report('printable'));$('folder').addEventListener('click',()=>call('folder'));$('period').addEventListener('change',dates);$('end').addEventListener('change',dates);$('refresh').addEventListener('click',async()=>{if(busy)return;setBusy(true);try{const warning=await refresh();notice(warning||'Records refreshed.',Boolean(warning));}catch(error){notice(error.message,true);}finally{setBusy(false);}});$('backup').addEventListener('click',()=>call('backup'));$('restore').addEventListener('click',()=>{const name=$('backup-name').value;if(!name){notice('Create a backup first.',true);return;}if(window.confirm('Restore '+name+'? This replaces the current ledger with the selected backup.'))call('restore',{name});});dates();refresh().then(warning=>notice(warning||'Ready. Save Excel, then import and review your day.',Boolean(warning))).catch(error=>notice(error.message,true));
</script></body></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the SmartBus local finance workstation.")
    parser.add_argument("--port", type=int, default=0, help="Local port (default: choose a free port).")
    parser.add_argument("--no-browser", action="store_true", help="Print the local URL without opening a browser.")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    server = SmartBusServer(("127.0.0.1", args.port))
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"SmartBus Professional is running at {url}", flush=True)
    print("Keep this window open. Press Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSmartBus stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
