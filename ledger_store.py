"""Versioned local accounting ledger, daily controls, and verified SQLite backups.

Excel remains the input surface. A closed revision is the source for final reports.
Operator names are attribution labels, not authenticated identities.
"""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import uuid
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

VERSION = "1.2.0"
SCHEMA_VERSION = 1
DAILY_NAME = re.compile(r"^Daily_(\d{4}-\d{2}-\d{2})_en\.xlsx$")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _encode(value):
    if isinstance(value, Decimal):
        return {"__smartbus_decimal__": str(value)}
    if isinstance(value, datetime):
        return {"__smartbus_datetime__": value.isoformat()}
    raise TypeError(f"Unsupported ledger value: {type(value).__name__}")


def _decode(value):
    if set(value) == {"__smartbus_decimal__"}:
        return Decimal(value["__smartbus_decimal__"])
    if set(value) == {"__smartbus_datetime__"}:
        return datetime.fromisoformat(value["__smartbus_datetime__"])
    return value


def serialize(book):
    return json.dumps(book, default=_encode, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def deserialize(raw):
    return json.loads(raw, object_hook=_decode)


def _label(value, field="Operator", limit=120):
    value = str(value or "").strip()
    if not value or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError(f"{field} must contain 1–{limit} printable characters.")
    return value


def _day(value):
    return date.fromisoformat(str(value)).isoformat()


def _review_errors(book):
    from daily_system import validate_book
    validate_book(book)
    messages = []
    for trip in book["trips"]:
        if not trip["counter_count"]:
            messages.append(f"Trip {trip['trip']}: enter its counter sales before review.")
        if trip["pending_counters"]:
            messages.append(f"Trip {trip['trip']}: received deposits are blank; enter known zero explicitly.")
    if messages:
        raise ValueError("Review blocked: " + " ".join(messages))


def freeze_workbook(path, book, backup_folder):
    """Pin saved transaction identifiers and master values without changing totals.

    Backup first, stage in the same directory, verify the staged book, then replace.
    New untouched formula rows continue to work with the current masters.
    """
    import daily_system as daily
    path = Path(path)
    before_hash = digest(path)
    backup_folder = Path(backup_folder)
    backup_folder.mkdir(parents=True, exist_ok=True)
    backup = backup_folder / f"{path.stem}_{uuid.uuid4().hex[:12]}.xlsx"
    shutil.copy2(path, backup)
    with ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    parts = daily.workbook_parts(files)
    trees = {name: ET.fromstring(files[parts[name]])
             for name in ("Settings", "Trips", "Collections")}
    styles = {name: {c.get("r"): c.get("s") for c in tree.findall(".//s:c", daily.NS)}
              for name, tree in trees.items()}
    raw = daily.read_book(path)
    trip_rows = [r for r in range(6, 106) if raw["Trips"].get(f"B{r}") not in (None, "")]
    for row, trip in zip(trip_rows, book["trips"]):
        for column, value in (("A", trip["trip"]), ("D", trip["route"]), ("G", trip["driver"])):
            daily.set_cell(trees["Trips"], f"{column}{row}", value)
    line_rows = [r for r in range(6, 506)
                 if any(raw["Collections"].get(f"{c}{r}") not in (None, "") for c in "EGM")]
    if len(line_rows) != len(book["lines"]):
        raise ValueError("Collection rows could not be pinned safely. Check all collection entries.")
    for row, line in zip(line_rows, book["lines"]):
        for column, value in (("D", line["trip"]), ("F", line["kind"]),
                              ("H", float(line["fare"]) if line["fare"] is not None else None)):
            daily.set_cell(trees["Collections"], f"{column}{row}", value)
    daily.set_cell(trees["Settings"], "B18", "SMARTBUS_FROZEN_V1")
    for name, tree in trees.items():
        for cell in tree.findall(".//s:c", daily.NS):
            style = styles[name].get(cell.get("r"))
            if style is not None:
                cell.set("s", style)
        files[parts[name]] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
    # Freeze must survive the next Excel load; regenerate any remaining formulas.
    workbook = ET.fromstring(files["xl/workbook.xml"])
    calc = workbook.find("s:calcPr", daily.NS)
    if calc is None:
        calc = ET.SubElement(workbook, daily.tag("calcPr"))
    calc.attrib.update(fullCalcOnLoad="1", forceFullCalc="1", calcMode="auto")
    files["xl/workbook.xml"] = ET.tostring(workbook, encoding="utf-8", xml_declaration=True)
    handle, temporary = tempfile.mkstemp(prefix=".smartbus_", suffix=".xlsx", dir=path.parent)
    os.close(handle)
    staged = Path(temporary)
    try:
        with ZipFile(staged, "w", ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        verified = daily.calculate(staged)
        # Compare the complete calculated accounts, not just the grand total.
        original = {k: v for k, v in book.items() if k not in ("path", "route_list", "bus_master", "counter_master")}
        after = {k: v for k, v in verified.items() if k not in ("path", "route_list", "bus_master", "counter_master")}
        if serialize(original) != serialize(after):
            raise ValueError("Pinning changed calculated accounts; import cancelled. Original workbook retained.")
        if digest(path) != before_hash:
            raise ValueError("Workbook changed during import. Save and close Excel, then retry.")
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)
    return backup


class LedgerStore:
    """Short-lived SQLite connections plus a process lock for restore safety."""

    def __init__(self, root=None, *, create=True):
        if root is None:
            from daily_system import ROOT
            root = ROOT
        self.root = Path(root).resolve()
        self.data_dir = self.root / "data"
        self.path = self.data_dir / "ledger.sqlite3"
        self.backups = self.root / "backups"
        self.recovery_error = None
        if create:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if self.path.is_file():
                try:
                    with closing(sqlite3.connect(self.path)) as check:
                        check.execute("PRAGMA user_version").fetchone()
                except sqlite3.DatabaseError:
                    self.recovery_error = "Ledger is damaged. Restore a verified backup using Backup and recovery."
                    return
            with self._guard(), self._connect() as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version not in (0, SCHEMA_VERSION):
                    raise ValueError("This ledger was created by a different application version.")
                connection.executescript("""
                    CREATE TABLE IF NOT EXISTS days (
                        day TEXT PRIMARY KEY,
                        status TEXT NOT NULL CHECK(status IN ('draft','reviewed','closed')),
                        revision INTEGER NOT NULL CHECK(revision > 0),
                        published_revision INTEGER,
                        source_name TEXT NOT NULL,
                        correction_reason TEXT NOT NULL DEFAULT '',
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS revisions (
                        day TEXT NOT NULL REFERENCES days(day), revision INTEGER NOT NULL,
                        source_sha256 TEXT NOT NULL, snapshot_json TEXT NOT NULL,
                        snapshot_sha256 TEXT NOT NULL, imported_at TEXT NOT NULL,
                        actor TEXT NOT NULL, closed_at TEXT,
                        PRIMARY KEY(day, revision)
                    );
                    CREATE TABLE IF NOT EXISTS trips (
                        day TEXT NOT NULL, revision INTEGER NOT NULL, record_id TEXT NOT NULL,
                        trip_label TEXT NOT NULL, gross TEXT NOT NULL, commission TEXT NOT NULL,
                        due TEXT NOT NULL, actual TEXT, outstanding TEXT NOT NULL,
                        PRIMARY KEY(day, revision, record_id), UNIQUE(day, revision, trip_label),
                        FOREIGN KEY(day, revision) REFERENCES revisions(day, revision)
                    );
                    CREATE TABLE IF NOT EXISTS settlements (
                        day TEXT NOT NULL, revision INTEGER NOT NULL, trip_record_id TEXT NOT NULL,
                        counter TEXT NOT NULL, due TEXT, actual TEXT, outstanding TEXT,
                        PRIMARY KEY(day, revision, trip_record_id, counter),
                        FOREIGN KEY(day, revision, trip_record_id) REFERENCES trips(day, revision, record_id)
                    );
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at TEXT NOT NULL,
                        actor TEXT NOT NULL, action TEXT NOT NULL, day TEXT,
                        revision INTEGER, details_json TEXT NOT NULL
                    );
                    CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events
                    BEGIN SELECT RAISE(ABORT, 'Audit events cannot be edited through SQL updates'); END;
                    CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events
                    BEGIN SELECT RAISE(ABORT, 'Audit events cannot be deleted through SQL deletes'); END;
                """)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @contextmanager
    def _guard(self):
        """All application writers, backup and restore use the same local lock."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with (self.data_dir / ".ledger.lock").open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError("Ledger is busy. Wait for the current operation and retry.") from exc
            try:
                yield
            finally:
                lock.seek(0)
                if os.name == "nt":
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def _connect(self):
        if not self.path.exists():
            # Creation is explicit through __init__; normal connections create the initial file.
            self.data_dir.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=15)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
        except Exception:
            connection.close()
            raise
        return _ClosingConnection(connection)

    @staticmethod
    def _event(connection, actor, action, day=None, revision=None, **details):
        connection.execute(
            "INSERT INTO audit_events(occurred_at,actor,action,day,revision,details_json) VALUES(?,?,?,?,?,?)",
            (utc_now(), actor, action, day, revision, json.dumps(details, ensure_ascii=False, sort_keys=True)))

    @staticmethod
    def _get_day(connection, day):
        row = connection.execute("SELECT * FROM days WHERE day=?", (_day(day),)).fetchone()
        if row is None:
            raise ValueError("Import this daily workbook before reviewing or closing it.")
        return row

    @staticmethod
    def _snapshot(connection, day, revision):
        row = connection.execute("SELECT * FROM revisions WHERE day=? AND revision=?", (day, revision)).fetchone()
        if row is None:
            raise ValueError("This revision has no imported workbook. Import the corrected file first.")
        raw = row["snapshot_json"]
        if hashlib.sha256(raw.encode("utf-8")).hexdigest() != row["snapshot_sha256"]:
            raise ValueError(f"Ledger snapshot integrity failed for {day}; restore a verified backup.")
        return deserialize(raw), row

    def _source_unchanged(self, row, revision):
        source = self.root / "daily" / row["source_name"]
        if not source.is_file() or digest(source) != revision["source_sha256"]:
            raise ValueError("Source workbook changed or is missing. Save, close Excel and import again before review/close.")

    def import_workbook(self, path, actor="Local operator", reason=""):
        from daily_system import calculate, validate_book
        actor = _label(actor)
        path = Path(path).resolve()
        daily_folder = (self.root / "daily").resolve()
        match = DAILY_NAME.fullmatch(path.name)
        if path.parent != daily_folder or not match or not path.is_file():
            raise ValueError("Import a Daily_YYYY-MM-DD_en.xlsx file from this project's daily folder.")
        if path.with_name("~$" + path.name).exists():
            raise ValueError("This workbook is open in Excel. Save and close it before importing.")
        day = _day(match[1])
        with self._guard(), self._connect() as connection:
            current = connection.execute("SELECT * FROM days WHERE day=?", (day,)).fetchone()
            source_hash = digest(path)
            if current is not None:
                old = connection.execute("SELECT source_sha256 FROM revisions WHERE day=? AND revision=?",
                                         (day, current["revision"])).fetchone()
                if current["source_name"] != path.name:
                    raise ValueError("A different language/file is already registered for this date.")
                if old and old["source_sha256"] == source_hash:
                    return dict(day=day, status=current["status"], revision=current["revision"], unchanged=True)
                if current["status"] == "closed":
                    raise ValueError("This day is closed. Start a correction with a reason before importing changes.")
            book = calculate(path)
            if book["day"] != day or book["dataset"] != "LIVE":
                raise ValueError("Only LIVE workbooks whose internal date matches the filename can be imported.")
            validate_book(book)
            self._backup_unlocked(connection)
            workbook_backup = freeze_workbook(path, book, self.backups / "workbooks")
            source_hash = digest(path)
            book = calculate(path)
            validate_book(book)
            now = utc_now()
            revision = (current["revision"] + 1 if old else current["revision"]) if current else 1
            previous_ids = {r["trip_label"]: r["record_id"] for r in connection.execute(
                "SELECT trip_label,record_id FROM trips WHERE day=? ORDER BY revision", (day,))}
            for trip in book["trips"]:
                trip["record_id"] = previous_ids.get(trip["trip"]) or str(uuid.uuid4())
            book["path"] = str(path)
            raw = serialize(book)
            if current:
                connection.execute("UPDATE days SET status='draft',revision=?,updated_at=? WHERE day=?", (revision, now, day))
            else:
                connection.execute("INSERT INTO days(day,status,revision,source_name,updated_at) VALUES(?,'draft',?,?,?)",
                                   (day, revision, path.name, now))
            connection.execute("INSERT INTO revisions(day,revision,source_sha256,snapshot_json,snapshot_sha256,imported_at,actor) VALUES(?,?,?,?,?,?,?)",
                               (day, revision, source_hash, raw, hashlib.sha256(raw.encode("utf-8")).hexdigest(), now, actor))
            for trip in book["trips"]:
                connection.execute("INSERT INTO trips VALUES(?,?,?,?,?,?,?,?,?)",
                                   (day, revision, trip["record_id"], trip["trip"], str(trip["gross"]), str(trip["commission"]),
                                    str(trip["due"]), str(trip["actual"]) if trip["actual"] is not None else None, str(trip["outstanding"])))
            trip_ids = {trip["trip"]: trip["record_id"] for trip in book["trips"]}
            for group in book["counter_groups"]:
                connection.execute("INSERT INTO settlements VALUES(?,?,?,?,?,?,?)",
                                   (day, revision, trip_ids[group["trip"]], str(group["counter"]),
                                    str(group["due"]), str(group["actual"]) if group["actual"] is not None else None, str(group["outstanding"])))
            self._event(connection, actor, "import", day, revision, source_name=path.name,
                        source_sha256=source_hash, workbook_backup=workbook_backup.name, reason=str(reason)[:1000])
        return dict(day=day, status="draft", revision=revision, unchanged=False)

    def review_day(self, day, actor="Local operator"):
        actor = _label(actor)
        with self._guard(), self._connect() as connection:
            row = self._get_day(connection, day)
            if row["status"] != "draft":
                raise ValueError("Only a draft day can be reviewed.")
            book, revision = self._snapshot(connection, row["day"], row["revision"])
            self._source_unchanged(row, revision)
            _review_errors(book)
            connection.execute("UPDATE days SET status='reviewed',updated_at=? WHERE day=?", (utc_now(), row["day"]))
            self._event(connection, actor, "review", row["day"], row["revision"])
        return dict(day=row["day"], status="reviewed", revision=row["revision"])

    def close_day(self, day, actor="Local operator"):
        actor = _label(actor)
        with self._guard(), self._connect() as connection:
            row = self._get_day(connection, day)
            if row["status"] != "reviewed":
                raise ValueError("Review this day before closing it.")
            book, revision = self._snapshot(connection, row["day"], row["revision"])
            self._source_unchanged(row, revision)
            _review_errors(book)
            self._backup_unlocked(connection)
            now = utc_now()
            connection.execute("UPDATE days SET status='closed',published_revision=revision,updated_at=? WHERE day=?", (now, row["day"]))
            connection.execute("UPDATE revisions SET closed_at=? WHERE day=? AND revision=?", (now, row["day"], row["revision"]))
            self._event(connection, actor, "close", row["day"], row["revision"])
        return dict(day=row["day"], status="closed", revision=row["revision"])

    def begin_correction(self, day, actor="Local operator", reason=""):
        actor = _label(actor)
        reason = _label(reason, "Correction reason", 1000)
        with self._guard(), self._connect() as connection:
            row = self._get_day(connection, day)
            if row["status"] != "closed":
                raise ValueError("Only a closed day can start a correction.")
            self._backup_unlocked(connection)
            revision = row["revision"] + 1
            connection.execute("UPDATE days SET status='draft',revision=?,correction_reason=?,updated_at=? WHERE day=?",
                               (revision, reason, utc_now(), row["day"]))
            self._event(connection, actor, "begin_correction", row["day"], revision, reason=reason,
                        previous_published_revision=row["published_revision"])
        return dict(day=row["day"], status="draft", revision=revision, published_revision=row["published_revision"])

    def status(self):
        if not self.path.is_file():
            return []
        try:
            with self._guard(), self._connect() as connection:
                return self._status_rows(connection)
        except sqlite3.DatabaseError:
            return [dict(day='', status='recovery_required', revision=0, published_revision=None,
                         source_name='', stale=True, needs_import=False,
                         warnings=['Ledger is damaged. Restore a verified backup.'], errors=['Ledger integrity failure.'])]

    def _status_rows(self, connection):
        result = []
        for row in connection.execute("SELECT * FROM days ORDER BY day DESC"):
            item = dict(row)
            rev = connection.execute("SELECT source_sha256 FROM revisions WHERE day=? AND revision=?",
                                     (row["day"], row["revision"])).fetchone()
            source = self.root / "daily" / row["source_name"]
            item["stale"] = bool(rev and (not source.is_file() or digest(source) != rev["source_sha256"]))
            item["needs_import"] = rev is None
            item["warnings"] = []
            if item["stale"]:
                item["warnings"].append("Workbook changed or missing; closed reports retain the published revision.")
            if rev:
                try:
                    book, _ = self._snapshot(connection, row['day'], row['revision'])
                except (ValueError, json.JSONDecodeError) as error:
                    item['errors'] = [str(error)]
                    item['warnings'].append('Snapshot integrity failure; restore a verified backup.')
                    result.append(item)
                    continue
                item["trip_count"] = len(book["trips"])
                item["pending_counters"] = sum(t["pending_counters"] for t in book["trips"])
                item["gross"] = str(sum((t["gross"] for t in book["trips"]), Decimal(0)))
                item["outstanding"] = str(sum((t["outstanding"] for t in book["trips"]), Decimal(0)))
                if item["pending_counters"]:
                    item["warnings"].append("Blank received deposits must be resolved before review.")
            result.append(item)
        return result

    def audit(self, limit=100):
        limit = int(limit)
        if not 1 <= limit <= 1000:
            raise ValueError("Audit limit must be between 1 and 1000.")
        with self._guard(), self._connect() as connection:
            result = []
            for row in connection.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)):
                item = dict(row)
                item["details"] = json.loads(item.pop("details_json"))
                result.append(item)
            return result

    def published_books(self, start, end):
        start, end = _day(start), _day(end)
        if start > end:
            raise ValueError("Start date must be on or before end date.")
        if not self.path.is_file():
            raise ValueError("Import, review and close your daily files before creating final reports.")
        with self._guard(), self._connect() as connection:
            result = []
            for row in connection.execute("SELECT * FROM days WHERE day BETWEEN ? AND ? AND published_revision IS NOT NULL ORDER BY day", (start, end)):
                book, rev = self._snapshot(connection, row["day"], row["published_revision"])
                book["ledger"] = dict(revision=row["published_revision"], status="closed", closed_at=rev["closed_at"],
                                      source_sha256=rev["source_sha256"], snapshot_sha256=rev["snapshot_sha256"],
                                      correction_pending=row["status"] != "closed")
                result.append(book)
            return result

    @staticmethod
    def _verify_backup(path):
        try:
            with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)) as connection:
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup integrity check failed.")
                if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                    raise ValueError("Unsupported backup schema version.")
                if connection.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Backup contains broken record references.")
                expected = {"days", "revisions", "trips", "settlements", "audit_events"}
                tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not expected <= tables:
                    raise ValueError("This is not a SmartBus ledger backup.")
                for raw, checksum in connection.execute("SELECT snapshot_json,snapshot_sha256 FROM revisions"):
                    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != checksum:
                        raise ValueError("Backup snapshot integrity check failed.")
                    deserialize(raw)
        except (sqlite3.DatabaseError, json.JSONDecodeError, TypeError, KeyError) as exc:
            raise ValueError("Invalid or damaged SmartBus backup.") from exc

    def _backup_unlocked(self, connection):
        self.backups.mkdir(parents=True, exist_ok=True)
        name = f"SmartBus_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid.uuid4().hex[:10]}.sqlite3"
        target = self.backups / name
        with closing(sqlite3.connect(target)) as destination:
            connection.backup(destination)
        try:
            self._verify_backup(target)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target

    def backup(self):
        with self._guard(), self._connect() as connection:
            target = self._backup_unlocked(connection)
            self._event(connection, "Local operator", "backup", name=target.name)
        return target

    def restore_backup(self, name, actor="Local operator"):
        actor = _label(actor)
        name = str(name)
        target = (self.backups / name).resolve()
        if target.parent != self.backups.resolve() or target.name != name or target.suffix != ".sqlite3" or not target.is_file():
            raise ValueError("Choose an existing SQLite backup from this project's backups folder.")
        with self._guard():
            self._verify_backup(target)
            prior_events = []
            try:
                with self._connect() as current:
                    safety = self._backup_unlocked(current)
                    prior_events = [dict(r) for r in current.execute("SELECT * FROM audit_events ORDER BY id")]
            except (ValueError, sqlite3.DatabaseError):
                # Recovery must also work when the current database is damaged.
                # Retain an exact forensic copy; do not list it as a valid backup.
                safety = self.backups / f"Damaged_{uuid.uuid4().hex}.sqlite3.damaged"
                shutil.copy2(self.path, safety)
                try:
                    with self._connect() as current:
                        prior_events = [dict(r) for r in current.execute("SELECT * FROM audit_events ORDER BY id")]
                except sqlite3.DatabaseError:
                    prior_events = []
            handle, temporary = tempfile.mkstemp(prefix=".restore_", suffix=".sqlite3", dir=self.data_dir)
            os.close(handle)
            staged = Path(temporary)
            try:
                with closing(sqlite3.connect(target.as_uri() + "?mode=ro", uri=True)) as source, \
                        closing(sqlite3.connect(staged)) as destination, destination:
                    source.backup(destination)
                    # Preserve events after the selected backup as recovery history.
                    existing = {tuple(row) for row in destination.execute("SELECT occurred_at,actor,action,day,revision,details_json FROM audit_events")}
                    for event in prior_events:
                        values = tuple(event[key] for key in ("occurred_at", "actor", "action", "day", "revision", "details_json"))
                        if values not in existing:
                            destination.execute("INSERT INTO audit_events(occurred_at,actor,action,day,revision,details_json) VALUES(?,?,?,?,?,?)", values)
                    self._event(destination, actor, "restore", backup=target.name, safety_backup=safety.name)
                self._verify_backup(staged)
                os.replace(staged, self.path)
            finally:
                staged.unlink(missing_ok=True)
        return dict(restored=target.name, safety_backup=safety.name)


class _ClosingConnection:
    """sqlite3's native context manager commits but does not close connections."""
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, kind, value, traceback):
        try:
            if kind is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        finally:
            self.connection.close()


def collect_closed(folder, start, end):
    """Final reports use published revisions, even if Excel has been edited/deleted."""
    from datetime import timedelta
    folder = Path(folder).resolve()
    start, end = date.fromisoformat(str(start)), date.fromisoformat(str(end))
    if start > end:
        raise ValueError("Start date must be on or before end date.")
    store = LedgerStore(folder.parent, create=False)
    books = store.published_books(start, end)
    published = {book["day"] for book in books}
    unclosed = {row['source_name'] for row in store.status()
                if str(start) <= row['day'] <= str(end) and row['published_revision'] is None}
    for path in folder.glob("Daily_*.xlsx"):
        match = DAILY_NAME.fullmatch(path.name)
        if match:
            try:
                day = date.fromisoformat(match[1])
            except ValueError:
                continue
            if start <= day <= end and str(day) not in published:
                unclosed.add(path.name)
    if unclosed:
        raise ValueError("Final reports require closed days. Import, review and close: " + ", ".join(sorted(unclosed)))
    if not books:
        raise ValueError("No closed daily records found in the selected date range.")
    missing = [str(start + timedelta(days=i)) for i in range((end - start).days + 1)
               if str(start + timedelta(days=i)) not in published]
    return books, missing, []


def main():
    parser = argparse.ArgumentParser(description="SmartBus Professional local accounting ledger")
    parser.add_argument("--root", type=Path, help="Project folder (defaults to this application)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    imp = sub.add_parser("import")
    imp.add_argument("path", type=Path)
    imp.add_argument("--actor", default="Local operator")
    for command in ("review", "close", "correct"):
        child = sub.add_parser(command)
        child.add_argument("day")
        child.add_argument("--actor", default="Local operator")
        if command == "correct":
            child.add_argument("--reason", required=True)
    sub.add_parser("backup")
    restore = sub.add_parser("restore")
    restore.add_argument("name")
    restore.add_argument("--actor", default="Local operator")
    audit = sub.add_parser("audit")
    audit.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    try:
        store = LedgerStore(args.root, create=args.command != 'restore')
        if args.command == "status":
            result = store.status()
        elif args.command == "import":
            result = store.import_workbook(args.path, args.actor)
        elif args.command == "review":
            result = store.review_day(args.day, args.actor)
        elif args.command == "close":
            result = store.close_day(args.day, args.actor)
        elif args.command == "correct":
            result = store.begin_correction(args.day, args.actor, args.reason)
        elif args.command == "backup":
            result = {"backup": str(store.backup())}
        elif args.command == "restore":
            result = store.restore_backup(args.name, args.actor)
        else:
            result = store.audit(args.limit)
        print(json.dumps(result, ensure_ascii=True, indent=2))
    except (ValueError, OSError, sqlite3.DatabaseError) as exc:
        parser.exit(1, f"SmartBus: {exc}\n")


if __name__ == "__main__":
    main()
