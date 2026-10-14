"""HTTP handler boundary tests using in-memory sockets, without network access."""

from concurrent.futures import ThreadPoolExecutor
from email import message_from_bytes
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode

import control_panel


class ControlPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.root.joinpath("daily").mkdir()
        cls.root.joinpath("reports").mkdir()
        cls.server = control_panel.SmartBusServer.__new__(control_panel.SmartBusServer)
        cls.server.root = cls.root
        cls.server.server_port = 17001
        cls.server.token = "test-session-token"
        cls.server.mutation_lock = threading.RLock()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.server.ledger = Mock()
        self.server.ledger.status.return_value = []
        self.server.ledger.audit.return_value = []

    def request(self, method="GET", path="/", body=None, headers=None):
        body = body.encode("utf-8") if isinstance(body, str) else body or b""
        request_headers = {"Host": f"127.0.0.1:{self.server.server_port}", "Content-Length": str(len(body))}
        request_headers.update(headers or {})
        request = (f"{method} {path} HTTP/1.1\r\n" + "".join(f"{key}: {value}\r\n" for key, value in request_headers.items()) + "\r\n").encode("latin-1") + body
        socket = MemorySocket(request)
        control_panel.Handler(socket, ("127.0.0.1", 10000), self.server)
        raw_headers, response_body = socket.output.getvalue().split(b"\r\n\r\n", 1)
        status_line, header_bytes = raw_headers.split(b"\r\n", 1)
        return int(status_line.split()[1]), dict(message_from_bytes(header_bytes).items()), response_body

    def post(self, values, headers=None):
        request_headers = {"Content-Type": "application/json", "X-SmartBus-Token": self.server.token}
        request_headers.update(headers or {})
        return self.request("POST", "/action", json.dumps(values), request_headers)

    def test_page_bootstraps_session_with_security_headers(self):
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        page = body.decode("utf-8")
        self.assertIn("const TOKEN=" + json.dumps(self.server.token), page)
        self.assertIn("Daily review", page)
        self.assertNotRegex(page, r"[\u0980-\u09ff]")
        self.assertNotIn('id="language"', page)
        self.assertNotIn('lang="bn"', page)
        self.assertNotIn("font.ttf", page)
        self.assertIn("toLocaleString('en-US'", page)
        self.assertIn("new Intl.DateTimeFormat('en-US'", page)
        self.assertIn("language:'en'", page)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertIn("script-src 'nonce-", headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_missing_or_wrong_token_cannot_mutate(self):
        for token in ("", "wrong-token"):
            status, _, _ = self.post({"action": "backup"}, {"X-SmartBus-Token": token})
            self.assertEqual(status, 403)
        self.server.ledger.backup.assert_not_called()

    def test_status_and_audit_require_session_token(self):
        for path in ("/api/status", "/api/audit"):
            self.assertEqual(self.request(path=path)[0], 403)
            self.assertEqual(self.request(path=path, headers={"X-SmartBus-Token": self.server.token})[0], 200)

    def test_external_origin_and_rebinding_host_are_rejected(self):
        for headers in ({"Origin": "https://example.com"}, {"Origin": "null"},
                        {"Origin": "http://["}, {"Host": "example.com"},
                        {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.post({"action": "backup"}, headers)[0], 403)
        self.server.ledger.backup.assert_not_called()
        self.server.ledger.backup.return_value = self.root / "backups" / "test.sqlite3"
        self.assertEqual(self.post({"action": "backup"}, {"Origin": f"http://127.0.0.1:{self.server.server_port}"})[0], 200)

    def test_json_and_positive_bounded_length_required(self):
        self.assertEqual(self.post({"action": "backup"}, {"Content-Type": "text/plain"})[0], 415)
        for length in ("0", "-1", "broken", str(control_panel.MAX_REQUEST_BYTES + 1)):
            self.assertIn(self.post({"action": "backup"}, {"Content-Length": length})[0], {400, 413})
        self.assertEqual(self.post(["backup"])[0], 400)
        self.server.ledger.backup.assert_not_called()

    def test_file_endpoint_serves_only_reports(self):
        report = self.root / "reports" / "safe.xlsx"
        report.write_bytes(b"workbook")
        (self.root / "reports" / "secret.sqlite3").write_bytes(b"database")
        (self.root / "private.py").write_text("private", encoding="utf-8")
        self.assertEqual(self.request(path="/file?" + urlencode({"name": "reports/safe.xlsx"}))[2], b"workbook")
        for name in ("private.py", "reports/secret.sqlite3", "reports/../private.py", "fonts/private.ttf", "reports/x\x00.xlsx"):
            self.assertEqual(self.request(path="/file?" + urlencode({"name": name}))[0], 404)

    def test_removed_font_endpoint_is_not_served(self):
        self.assertEqual(self.request(path="/font.ttf")[0], 404)

    def test_creation_and_reports_default_to_english(self):
        workbook = self.root / "daily" / "Daily_2026-10-15_en.xlsx"
        with patch.object(control_panel, "create_daily", return_value=workbook) as create, patch.object(control_panel.os, "startfile", create=True):
            status, _, body = self.post({"action": "new", "date": "2026-10-15"})
        self.assertEqual(status, 200)
        create.assert_called_once_with("2026-10-15", "en", folder=self.root / "daily")
        self.assertNotRegex(body.decode("utf-8"), r"[\u0980-\u09ff]")
        for action, function, suffix in (("combined", "make_period_excel", ".xlsx"), ("report", "make_report", ".pdf"), ("printable", "make_printable_report", ".html")):
            report = self.root / "reports" / ("English_report" + suffix)
            with self.subTest(action=action), patch.object(control_panel, function, return_value=report) as export:
                status, _, _ = self.post({"action": action, "start": "2026-10-01", "end": "2026-10-15"})
                self.assertEqual(status, 200)
                export.assert_called_once_with(self.root / "daily", "2026-10-01", "2026-10-15", "en", company="SmartBus", counter=None, report_folder=self.root / "reports")

    def test_printable_html_has_nonce_and_rejects_arbitrary_html(self):
        path = self.root / 'reports/printable.html'
        path.write_text('<meta name="smartbus-report" content="1"><style>body{color:black}</style><script data-smartbus-print>window.print();</script>', encoding='utf-8')
        status, headers, body = self.request(path='/file?'+urlencode({'name':'reports/printable.html'}))
        self.assertEqual(status,200)
        self.assertIn('text/html',headers['Content-Type'])
        self.assertIn('<style nonce="',body.decode())
        self.assertIn('<script nonce="',body.decode())
        self.assertNotIn('unsafe-inline',headers['Content-Security-Policy'])
        path.write_text('<script>alert(1)</script>',encoding='utf-8')
        self.assertEqual(self.request(path='/file?'+urlencode({'name':'reports/printable.html'}))[0],404)

    def test_non_english_requests_are_rejected_before_actions(self):
        for language in ("bn", "fr", "", None, [], {}):
            with self.subTest(language=language), patch.object(control_panel, "create_daily") as create:
                status, _, body = self.post({"action": "new", "date": "2026-10-15", "language": language})
                self.assertEqual(status, 400)
                self.assertIn("Only English is supported", body.decode("utf-8"))
                create.assert_not_called()
        for action in ("combined", "report", "backup"):
            self.assertEqual(self.post({"action": action, "language": "bn"})[0], 400)
        self.server.ledger.backup.assert_not_called()

    def test_only_english_daily_files_are_listed_and_opened(self):
        english = self.root / "daily" / "Daily_2026-10-16_en.xlsx"
        unsupported = self.root / "daily" / "Daily_2026-10-16_other.xlsx"
        english.write_bytes(b"workbook")
        unsupported.write_bytes(b"workbook")
        status, _, body = self.request(path="/api/status", headers={"X-SmartBus-Token": self.server.token})
        self.assertEqual(status, 200)
        self.assertIn(english.name, json.loads(body)["files"])
        self.assertNotIn(unsupported.name, json.loads(body)["files"])
        with patch.object(control_panel.os, "startfile", create=True) as launch:
            self.assertEqual(self.post({"action": "open", "name": unsupported.name})[0], 400)
            self.assertEqual(self.post({"action": "ledger_import", "name": unsupported.name})[0], 400)
            launch.assert_not_called()
        self.server.ledger.import_workbook.assert_not_called()

    def test_daily_path_blocks_traversal_before_native_launch(self):
        with patch.object(control_panel.os, "startfile", create=True) as launch:
            self.assertEqual(self.post({"action": "open", "name": "../private.py"})[0], 400)
            self.assertEqual(self.post({"action": "ledger_import", "name": "C:\\private.xlsx"})[0], 400)
            launch.assert_not_called()
        self.server.ledger.import_workbook.assert_not_called()

    def test_workflow_routes_actor_and_reason(self):
        workbook = self.root / "daily" / "Daily_2026-10-13_en.xlsx"
        workbook.write_bytes(b"workbook")
        self.server.ledger.import_workbook.return_value = {"day": "2026-10-13", "status": "draft"}
        status, _, _ = self.post({"action": "ledger_import", "name": workbook.name, "actor": "Finance intern"})
        self.assertEqual(status, 200)
        self.server.ledger.import_workbook.assert_called_once_with(workbook.resolve(), actor="Finance intern")
        self.server.ledger.begin_correction.return_value = {"status": "correction"}
        status, _, _ = self.post({"action": "ledger_correct", "day": "2026-10-13", "actor": "Reviewer", "reason": "Receipt corrected"})
        self.assertEqual(status, 200)
        self.server.ledger.begin_correction.assert_called_once_with("2026-10-13", actor="Reviewer", reason="Receipt corrected")

    def test_unknown_failure_does_not_expose_traceback_or_local_path(self):
        self.server.ledger.backup.side_effect = RuntimeError("secret C:\\finance\\ledger.sqlite3")
        with patch.object(control_panel.LOGGER, "exception"):
            status, _, body = self.post({"action": "backup"})
        self.assertEqual(status, 500)
        self.assertNotIn(b"secret", body)
        self.assertNotIn(b"Traceback", body)
        self.assertNotIn(b"finance", body)

    def test_mutations_are_serialized(self):
        active = 0
        peak = 0
        counter_lock = threading.Lock()

        def backup():
            nonlocal active, peak
            with counter_lock:
                active += 1
                peak = max(peak, active)
            time.sleep(.03)
            with counter_lock:
                active -= 1
            return self.root / "backups" / "test.sqlite3"

        self.server.ledger.backup.side_effect = backup
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.post({"action": "backup"})[0], range(4)))
        self.assertEqual(results, [200] * 4)
        self.assertEqual(peak, 1)

    def test_restore_rejects_path_and_requires_reason_for_correction(self):
        self.assertEqual(self.post({"action": "restore", "name": "../ledger.sqlite3"})[0], 400)
        self.assertEqual(self.post({"action": "ledger_correct", "day": "2026-10-13", "reason": " "})[0], 400)
        self.server.ledger.restore_backup.assert_not_called()
        self.server.ledger.begin_correction.assert_not_called()

    def test_recovery_state_still_lists_backups_when_audit_is_unavailable(self):
        backups = self.root / "backups"
        backups.mkdir(exist_ok=True)
        backups.joinpath("recovery.sqlite3").write_bytes(b"backup")
        self.server.ledger.status.return_value = [{"day": "", "status": "recovery_required"}]
        self.server.ledger.audit.side_effect = RuntimeError("Ledger damaged")
        status, _, body = self.request(path="/api/status", headers={"X-SmartBus-Token": self.server.token})
        self.assertEqual(status, 200)
        state = json.loads(body)
        self.assertEqual(state["days"][0]["status"], "recovery_required")
        self.assertIn("recovery.sqlite3", state["backups"])
        with patch.object(control_panel.LOGGER, "exception"):
            self.assertEqual(self.request(path="/api/audit", headers={"X-SmartBus-Token": self.server.token})[0], 500)

    def test_open_file_uses_native_launcher_only_after_validation(self):
        workbook = self.root / "daily" / "Daily_2026-10-14_en.xlsx"
        workbook.write_bytes(b"workbook")
        with patch.object(control_panel.os, "startfile", create=True) as launch:
            status, _, _ = self.post({"action": "open", "name": workbook.name})
        self.assertEqual(status, 200)
        launch.assert_called_once_with(workbook.resolve())


class MemorySocket:
    """The request parser and response writer see the same interface as a socket."""

    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = io.BytesIO()

    def makefile(self, *_args, **_kwargs):
        return self.input

    def sendall(self, value):
        self.output.write(value)


if __name__ == "__main__":
    unittest.main()
