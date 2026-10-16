"""SmartBus local workstation: daily workbooks, financial controls and reports.

Operator names record attribution, without authenticating a person. The server
binds only to loopback. All requests check Host/Origin; actions also require a
random session token. One mutation lock serializes writes across request threads.
"""

import argparse
import html
import json
import logging
import re
import secrets
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from daily_system import ROOT, create_daily, make_printable_report, make_report
from insights import build_insights, plan_scenario
from ledger_store import LedgerStore
from period_export import make_period_excel
from platform_open import open_path
from project_profile import APP_VERSION, load_profile, save_profile
from ridership import load_benchmark
from workstation_ui import PAGE

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
            policy += (
                f"; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'"
                "; connect-src 'self'"
            )
        self.send_header("Content-Security-Policy", policy)
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value, status=200):
        self.send(
            json.dumps(value, ensure_ascii=False),
            status,
            "application/json; charset=utf-8",
        )

    def local_request(self):
        if (
            len(self.headers.get_all("Host", [])) != 1
            or self.headers.get("Host", "").lower() not in self.server.authorities
        ):
            return False
        origin = self.headers.get("Origin")
        if origin:
            try:
                parsed = urlparse(origin)
            except ValueError:
                return False
            if (
                parsed.scheme != "http"
                or parsed.netloc.lower() not in self.server.authorities
                or parsed.path
                or parsed.params
                or parsed.query
                or parsed.fragment
            ):
                return False
        return self.headers.get("Sec-Fetch-Site") not in {"cross-site", "same-site"}

    def token_valid(self):
        supplied = self.headers.get("X-SmartBus-Token", "")
        return (
            len(self.headers.get_all("X-SmartBus-Token", [])) == 1
            and bool(supplied)
            and secrets.compare_digest(
                supplied.encode("utf-8"), self.server.token.encode("ascii")
            )
        )

    def do_GET(self):
        if not self.local_request():
            self.send_json({"message": "Local requests only."}, 403)
            return
        url = urlparse(self.path)
        if url.path == "/":
            nonce = secrets.token_urlsafe(24)
            self.send(
                render_page(self.server.token, nonce, load_profile(self.server.root)),
                nonce=nonce,
            )
            return
        if url.path in {
            "/api/status",
            "/api/audit",
            "/api/insights",
            "/api/profile",
            "/api/benchmark",
        }:
            if not self.token_valid():
                self.send_json(
                    {"message": "Open SmartBus to start a local session."}, 403
                )
                return
            try:
                with self.server.mutation_lock:
                    if url.path == "/api/status":
                        result = {
                            "demo": self.server.root.joinpath(
                                ".smartbus-demo"
                            ).is_file(),
                            "days": self.server.ledger.status(),
                            "files": sorted(
                                (
                                    p.name
                                    for p in self.server.root.joinpath("daily").glob(
                                        "Daily_*.xlsx"
                                    )
                                    if DAILY_NAME.fullmatch(p.name)
                                ),
                                reverse=True,
                            ),
                            "backups": sorted(
                                (
                                    p.name
                                    for p in self.server.root.joinpath("backups").glob(
                                        "*.sqlite3"
                                    )
                                ),
                                reverse=True,
                            ),
                        }
                    elif url.path == "/api/audit":
                        result = {"events": self.server.ledger.audit(limit=100)}
                    elif url.path == "/api/profile":
                        result = {"profile": load_profile(self.server.root)}
                    elif url.path == "/api/benchmark":
                        result = load_benchmark(self.server.root)
                    else:
                        query = parse_qs(url.query, keep_blank_values=True)
                        if set(query) - {"start", "end", "route"} or any(
                            len(items) != 1 for items in query.values()
                        ):
                            raise ValueError(
                                "Use one start, end and optional route filter."
                            )
                        if "start" not in query or "end" not in query:
                            raise ValueError(
                                "Choose a start and end date for insights."
                            )
                        result = build_insights(
                            self.server.root,
                            query["start"][0],
                            query["end"][0],
                            route=query.get("route", [None])[0],
                        )
                self.send_json(result)
            except ValueError as error:
                self.send_json({"message": str(error)}, 400)
            except Exception:
                LOGGER.exception("Cannot load workstation state")
                self.send_json(
                    {
                        "message": "Could not load records. Check the local console and try again."
                    },
                    500,
                )
            return
        if url.path == "/file":
            names = parse_qs(url.query).get("name", [])
            try:
                candidate = (
                    (self.server.root / names[0]).resolve() if len(names) == 1 else None
                )
            except (ValueError, OSError):
                candidate = None
            report_root = (self.server.root / "reports").resolve()
            if (
                candidate is None
                or candidate.parent != report_root
                or candidate.suffix.lower() not in {".pdf", ".xlsx", ".html"}
                or not candidate.is_file()
            ):
                self.send("Report not found", 404, "text/plain; charset=utf-8")
                return
            if candidate.suffix.lower() == ".html":
                page = candidate.read_text(encoding="utf-8")
                if '<meta name="smartbus-report" content="1">' not in page:
                    self.send("Report not found", 404, "text/plain; charset=utf-8")
                    return
                nonce = secrets.token_urlsafe(24)
                page = page.replace("<style>", f'<style nonce="{nonce}">', 1)
                page = page.replace(
                    "<script data-smartbus-print>", f'<script nonce="{nonce}">', 1
                )
                self.send(page, nonce=nonce)
                return
            ctype = (
                "application/pdf"
                if candidate.suffix.lower() == ".pdf"
                else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            self.send(candidate.read_bytes(), ctype=ctype)
            return
        self.send("Not found", 404, "text/plain; charset=utf-8")

    def do_POST(self):
        if not self.local_request() or not self.token_valid():
            self.send_json(
                {
                    "message": "Request rejected. Reopen the SmartBus page and try again."
                },
                403,
            )
            return
        if self.path != "/action":
            self.send_json({"message": "Unknown endpoint."}, 404)
            return
        if (
            self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            != "application/json"
        ):
            self.send_json({"message": "JSON requests are required."}, 415)
            return
        raw_length = self.headers.get("Content-Length", "")
        if (
            self.headers.get("Transfer-Encoding")
            or len(self.headers.get_all("Content-Length", [])) != 1
            or not raw_length.isascii()
            or not raw_length.isdecimal()
        ):
            self.send_json({"message": "A valid request length is required."}, 400)
            return
        length = int(raw_length)
        if not 0 < length <= MAX_REQUEST_BYTES:
            self.send_json(
                {"message": "Request size is outside the supported limit."}, 413
            )
            return
        try:
            values = json.loads(self.rfile.read(length))
            if not isinstance(values, dict):
                raise ValueError("Request must be a JSON object.")
            with self.server.mutation_lock:
                result = self.perform_action(values)
            self.send_json(result)
        except (ValueError, KeyError, UnicodeDecodeError) as error:
            message = (
                str(error)
                if isinstance(error, ValueError)
                else "A required field is missing or invalid."
            )
            self.send_json({"message": "Not completed: " + message}, 400)
        except Exception:
            LOGGER.exception("Local action failed")
            self.send_json(
                {
                    "message": "Could not complete the action. Check the local console and try again."
                },
                500,
            )

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
        ledger = self.server.ledger
        if action == "scenario":
            return {
                "message": "Scenario calculated. Ledger records are unchanged.",
                "data": plan_scenario(
                    values.get("seats"), values.get("fare"), values.get("counter_type")
                ),
            }
        if action == "save_profile":
            profile = save_profile(values.get("profile"), root=self.server.root)
            return {
                "message": "Customization saved. Reload the page to apply it.",
                "profile": profile,
            }
        actor = clean_text(values.get("actor", "Local operator"), "Operator", 80)
        if action == "new":
            path = create_daily(
                checked_day(values["date"]), language, folder=self.server.root / "daily"
            )
            if not open_path(path):
                return {"message": f"File saved at {path}"}
            return {"message": "Workbook created: " + path.name}
        if action == "open":
            path = self.daily_path(values["name"])
            if not open_path(path):
                return {"message": f"File saved at {path}"}
            return {"message": "Opening workbook: " + path.name}
        if action == "folder":
            path = self.server.root / "daily"
            if not open_path(path):
                return {"message": f"Folder available at {path}"}
            return {"message": "Daily workbook folder opened."}
        if action in {"combined", "report", "printable"}:
            start, end = checked_day(values["start"]), checked_day(values["end"])
            if start > end:
                raise ValueError("Start date must be on or before end date.")
            company = clean_text(
                values.get("company", load_profile(self.server.root)["company_name"]),
                "Company",
                120,
            )
            report_function = {
                "report": make_report,
                "combined": make_period_excel,
                "printable": make_printable_report,
            }[action]
            path = report_function(
                self.server.root / "daily",
                start,
                end,
                language,
                company=company,
                counter=values.get("counter"),
                report_folder=self.server.root / "reports",
            )
            message = (
                "Printable report saved. Open it, click Print / Save as PDF, choose Save as PDF, then Save."
                if action == "printable"
                else "Final report saved: " + path.name
            )
            return {
                "message": message,
                "url": "/file?" + urlencode({"name": "reports/" + path.name}),
            }
        if action == "ledger_import":
            data = ledger.import_workbook(self.daily_path(values["name"]), actor=actor)
            return {
                "message": "Workbook imported. Review this day before closing.",
                "data": data,
            }
        if action == "ledger_review":
            data = ledger.review_day(checked_day(values["day"]), actor=actor)
            return {
                "message": "Review passed. The day can now be closed.",
                "data": data,
            }
        if action == "ledger_close":
            data = ledger.close_day(checked_day(values["day"]), actor=actor)
            return {
                "message": "Day closed. Its snapshot is available for final reports.",
                "data": data,
            }
        if action == "ledger_correct":
            reason = clean_text(values.get("reason", ""), "Correction reason", 500)
            data = ledger.begin_correction(
                checked_day(values["day"]), actor=actor, reason=reason
            )
            return {
                "message": "Correction opened. Edit and save Excel, then import, review and close again.",
                "data": data,
            }
        if action == "backup":
            path = ledger.backup()
            return {"message": "Backup saved: " + Path(path).name}
        if action == "restore":
            name = clean_text(values.get("name", ""), "Backup name", 160)
            if (
                Path(name).name != name
                or "/" in name
                or "\\" in name
                or not name.endswith(".sqlite3")
            ):
                raise ValueError("Choose a listed backup.")
            data = ledger.restore_backup(name, actor=actor)
            return {
                "message": "Backup restored. Check your daily review before continuing.",
                "data": data,
            }
        raise ValueError("Unknown action.")


def clean_text(value, field, limit):
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value.strip()) > limit
        or any(ord(c) < 32 for c in value)
    ):
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
    page = (
        PAGE.replace("__TOKEN__", json.dumps(token))
        .replace("__NONCE__", html.escape(nonce, quote=True))
        .replace("__TODAY__", date.today().isoformat())
    )
    for key in (
        "project_name",
        "tagline",
        "company_name",
        "default_operator",
        "author",
        "accent_color",
    ):
        page = page.replace(
            "__" + key.upper() + "__", html.escape(profile[key], quote=True)
        )
    return page.replace("__VERSION__", APP_VERSION)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the SmartBus local finance workstation."
    )
    parser.add_argument(
        "--port", type=int, default=0, help="Local port (default: choose a free port)."
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Print the local URL without opening a browser.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Separate workstation data folder (for an isolated demonstration).",
    )
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    server = SmartBusServer(("127.0.0.1", args.port), root=args.root)
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
