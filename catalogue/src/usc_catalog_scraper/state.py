"""Durable SQLite state: runs, links, programs, fetch log, errors, boundary.

A program is complete only after page acquisition, extraction, atomic file
write, hash calculation, database commit, and index update. Resume relies on
this table plus on-disk hash verification, never on file existence alone.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from usc_catalog_scraper.models import (
    Classification,
    ClassificationResult,
    DiscoveredLink,
    ExtractionStatus,
    utcnow_iso,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    args TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS resolution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    supplied_url TEXT,
    resolved_url TEXT,
    catalogue_title TEXT,
    catalogue_year TEXT,
    catoid TEXT,
    navoid TEXT,
    method TEXT,
    verified INTEGER,
    notes TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS links (
    catoid TEXT NOT NULL,
    poid TEXT NOT NULL,
    seq INTEGER NOT NULL,
    title TEXT,
    href TEXT,
    absolute_url TEXT,
    canonical_url TEXT UNIQUE,
    returnto TEXT,
    section_heading TEXT,
    dom_path TEXT,
    classification TEXT,
    class_reason TEXT,
    class_evidence TEXT,
    detected_credentials TEXT,
    first_seen_run TEXT,
    classified_at TEXT,
    PRIMARY KEY (catoid, poid)
);
CREATE TABLE IF NOT EXISTS programs (
    catoid TEXT NOT NULL,
    poid TEXT NOT NULL,
    filename TEXT UNIQUE,
    program_name TEXT,
    credential TEXT,
    school TEXT,
    catalogue_year TEXT,
    acquisition_mode TEXT,
    retrieved_at TEXT,
    content_sha256 TEXT,
    source_html_sha256 TEXT,
    rendered_dom_sha256 TEXT,
    char_count INTEGER,
    line_count INTEGER,
    extraction_status TEXT NOT NULL DEFAULT 'pending',
    breadcrumbs TEXT,
    updated_at TEXT,
    PRIMARY KEY (catoid, poid)
);
CREATE TABLE IF NOT EXISTS fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, url TEXT, page_type TEXT, attempt INTEGER, method TEXT,
    acquisition_mode TEXT, http_status INTEGER, content_type TEXT,
    elapsed_seconds REAL, semantic_validation TEXT, challenge_detected INTEGER,
    content_length INTEGER, raw_html_sha256 TEXT, rendered_dom_sha256 TEXT,
    result TEXT
);
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, stage TEXT, program_name TEXT, source_url TEXT,
    program_identifier TEXT, attempt_number INTEGER, error_type TEXT,
    error_message TEXT, acquisition_mode TEXT, retryable INTEGER,
    resolved INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS boundary (
    run_id TEXT PRIMARY KEY,
    payload TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _existing_output_is_valid(path: Path) -> bool:
    """True when an already-written output still passes output validation."""
    from usc_catalog_scraper.output_validation import validate_extracted_text

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    marker = "OFFICIAL CATALOGUE CONTENT"
    program_name = ""
    body = text
    if marker not in text:
        # Every file this app writes carries the marker. Without it the file is
        # malformed (hand-edited or truncated) and must be re-extracted rather
        # than validated as if the metadata header were body content.
        return False
    if marker in text:
        head, body = text.split(marker, 1)
        for line in head.splitlines():
            if line.startswith("Program Name:"):
                program_name = line.split(":", 1)[1].strip()
                break
    ok, _evidence = validate_extracted_text(body.strip("\n"), program_name)
    return ok


class StateDB:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ------------------------------------------------------------ runs
    def start_run(self, run_id: str, args: dict) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO runs(run_id, started_at, args) VALUES (?,?,?)",
                (run_id, utcnow_iso(), json.dumps(args, default=str)),
            )

    def complete_run(self, run_id: str, notes: str = "") -> None:
        with self.tx() as c:
            c.execute(
                "UPDATE runs SET completed_at=?, notes=? WHERE run_id=?",
                (utcnow_iso(), notes, run_id),
            )

    # ------------------------------------------------------ resolution
    def save_resolution(self, run_id: str, **fields) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT INTO resolution(run_id, supplied_url, resolved_url,
                   catalogue_title, catalogue_year, catoid, navoid, method,
                   verified, notes, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    fields.get("supplied_url", ""),
                    fields.get("resolved_url", ""),
                    fields.get("catalogue_title", ""),
                    fields.get("catalogue_year", ""),
                    fields.get("catoid", ""),
                    fields.get("navoid", ""),
                    fields.get("method", ""),
                    int(bool(fields.get("verified"))),
                    json.dumps(fields.get("notes", []), default=str),
                    utcnow_iso(),
                ),
            )

    def latest_resolution(self) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM resolution ORDER BY id DESC LIMIT 1").fetchone()

    # ------------------------------------------------------------ links
    def upsert_link(self, link: DiscoveredLink, run_id: str) -> int:
        """Insert new link or refresh mutable fields. Sequence numbers are
        stable: an existing (catoid, poid) keeps its original seq."""
        with self.tx() as c:
            row = c.execute(
                "SELECT seq FROM links WHERE catoid=? AND poid=?",
                (link.catoid, link.poid),
            ).fetchone()
            if row:
                c.execute(
                    """UPDATE links SET title=?, href=?, absolute_url=?,
                       canonical_url=?, returnto=?, section_heading=?, dom_path=?
                       WHERE catoid=? AND poid=?""",
                    (
                        link.title,
                        link.href,
                        link.absolute_url,
                        link.canonical_url,
                        link.returnto,
                        link.section_heading,
                        link.dom_path,
                        link.catoid,
                        link.poid,
                    ),
                )
                return int(row["seq"])
            c.execute(
                """INSERT INTO links(catoid, poid, seq, title, href, absolute_url,
                   canonical_url, returnto, section_heading, dom_path, first_seen_run)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    link.catoid,
                    link.poid,
                    link.sequence,
                    link.title,
                    link.href,
                    link.absolute_url,
                    link.canonical_url,
                    link.returnto,
                    link.section_heading,
                    link.dom_path,
                    run_id,
                ),
            )
            return link.sequence

    def record_classification(self, catoid: str, poid: str, result: ClassificationResult) -> None:
        with self.tx() as c:
            c.execute(
                """UPDATE links SET classification=?, class_reason=?,
                   class_evidence=?, detected_credentials=?, classified_at=?
                   WHERE catoid=? AND poid=?""",
                (
                    result.classification.value,
                    result.reason,
                    json.dumps(result.evidence, default=str),
                    json.dumps(result.detected_credentials),
                    utcnow_iso(),
                    catoid,
                    poid,
                ),
            )

    def links_by_classification(self, classification: Classification) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM links WHERE classification=? ORDER BY seq",
            (classification.value,),
        ).fetchall()

    def all_links(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM links ORDER BY seq").fetchall()

    def link(self, catoid: str, poid: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM links WHERE catoid=? AND poid=?", (catoid, poid)
        ).fetchone()

    # --------------------------------------------------------- programs
    def ensure_program_row(self, catoid: str, poid: str) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT OR IGNORE INTO programs(catoid, poid, extraction_status, updated_at)
                   VALUES (?,?,?,?)""",
                (catoid, poid, ExtractionStatus.PENDING.value, utcnow_iso()),
            )

    def reserve_filename(self, catoid: str, poid: str, filename: str) -> str:
        """Persist the chosen filename (stable across resumes)."""
        with self.tx() as c:
            row = c.execute(
                "SELECT filename FROM programs WHERE catoid=? AND poid=?", (catoid, poid)
            ).fetchone()
            if row and row["filename"]:
                return str(row["filename"])
            c.execute(
                "UPDATE programs SET filename=?, updated_at=? WHERE catoid=? AND poid=?",
                (filename, utcnow_iso(), catoid, poid),
            )
            return filename

    def existing_filenames(self) -> set[str]:
        rows = self.conn.execute(
            "SELECT filename FROM programs WHERE filename IS NOT NULL"
        ).fetchall()
        return {str(r["filename"]) for r in rows}

    def mark_program(
        self,
        catoid: str,
        poid: str,
        status: ExtractionStatus,
        **fields,
    ) -> None:
        cols = [
            "program_name",
            "credential",
            "school",
            "catalogue_year",
            "acquisition_mode",
            "retrieved_at",
            "content_sha256",
            "source_html_sha256",
            "rendered_dom_sha256",
            "char_count",
            "line_count",
            "breadcrumbs",
        ]
        sets = ["extraction_status=?", "updated_at=?"]
        vals: list = [status.value, utcnow_iso()]
        for col in cols:
            if col in fields:
                sets.append(f"{col}=?")
                vals.append(fields[col])
        vals.extend([catoid, poid])
        with self.tx() as c:
            c.execute(
                f"UPDATE programs SET {', '.join(sets)} WHERE catoid=? AND poid=?",
                vals,
            )

    def program(self, catoid: str, poid: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM programs WHERE catoid=? AND poid=?", (catoid, poid)
        ).fetchone()

    def program_rows(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT p.*, l.seq, l.title, l.absolute_url, l.canonical_url,
                      l.classification, l.section_heading
               FROM programs p JOIN links l ON p.catoid=l.catoid AND p.poid=l.poid
               ORDER BY l.seq"""
        ).fetchall()

    def counts(self) -> dict:
        out: dict = {}
        for cls in Classification:
            row = self.conn.execute(
                "SELECT COUNT(*) n FROM links WHERE classification=?", (cls.value,)
            ).fetchone()
            if row and row["n"]:
                out[cls.value] = int(row["n"])
        for status in ExtractionStatus:
            row = self.conn.execute(
                "SELECT COUNT(*) n FROM programs WHERE extraction_status=?",
                (status.value,),
            ).fetchone()
            out[f"extraction_{status.value}"] = int(row["n"]) if row else 0
        row = self.conn.execute("SELECT COUNT(*) n FROM links").fetchone()
        out["links_total"] = int(row["n"]) if row else 0
        return out

    # -------------------------------------------------------- fetch log
    def log_fetch(self, **f) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT INTO fetch_log(ts, url, page_type, attempt, method,
                   acquisition_mode, http_status, content_type, elapsed_seconds,
                   semantic_validation, challenge_detected, content_length,
                   raw_html_sha256, rendered_dom_sha256, result)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    f.get("ts", utcnow_iso()),
                    f.get("url"),
                    f.get("page_type"),
                    f.get("attempt", 1),
                    f.get("method"),
                    f.get("acquisition_mode"),
                    f.get("http_status"),
                    f.get("content_type"),
                    f.get("elapsed_seconds", 0.0),
                    f.get("semantic_validation"),
                    int(bool(f.get("challenge_detected"))),
                    f.get("content_length", 0),
                    f.get("raw_html_sha256", ""),
                    f.get("rendered_dom_sha256", ""),
                    f.get("result", ""),
                ),
            )

    # ----------------------------------------------------------- errors
    def log_error(self, **f) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT INTO errors(ts, stage, program_name, source_url,
                   program_identifier, attempt_number, error_type, error_message,
                   acquisition_mode, retryable, resolved)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    f.get("ts", utcnow_iso()),
                    f.get("stage"),
                    f.get("program_name", ""),
                    f.get("source_url", ""),
                    f.get("program_identifier", ""),
                    f.get("attempt_number", 1),
                    f.get("error_type", ""),
                    f.get("error_message", "")[:2000],
                    f.get("acquisition_mode", ""),
                    int(bool(f.get("retryable", False))),
                    int(bool(f.get("resolved", False))),
                ),
            )

    def mark_errors_resolved(self, source_url: str) -> None:
        with self.tx() as c:
            c.execute("UPDATE errors SET resolved=1 WHERE source_url=?", (source_url,))

    # --------------------------------------------------------- boundary
    def save_boundary(self, run_id: str, payload: dict) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO boundary(run_id, payload, created_at) VALUES (?,?,?)",
                (run_id, json.dumps(payload, default=str), utcnow_iso()),
            )

    def latest_boundary(self) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM boundary ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    # --------------------------------------------------------------- kv
    def set_kv(self, key: str, value) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO kv(key, value) VALUES (?,?)",
                (key, json.dumps(value, default=str)),
            )

    def get_kv(self, key: str, default=None):
        row = self.conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    # ------------------------------------------------------------ resume
    def needs_extraction(self, programs_dir: Path) -> list[sqlite3.Row]:
        """Included links whose output file is missing, hash-mismatched, or
        whose extraction is not complete. Completed+verified rows are skipped."""
        pending: list[sqlite3.Row] = []
        rows = self.conn.execute(
            """SELECT l.*, p.filename, p.content_sha256, p.extraction_status
               FROM links l LEFT JOIN programs p
                 ON l.catoid=p.catoid AND l.poid=p.poid
               WHERE l.classification=? ORDER BY l.seq""",
            (Classification.INCLUDED.value,),
        ).fetchall()
        for row in rows:
            status = row["extraction_status"]
            filename = row["filename"]
            if status == ExtractionStatus.COMPLETE.value and filename:
                path = programs_dir / str(filename)
                # A matching hash proves the file is unmodified — it does NOT
                # prove the content is good. Files written before the
                # 2026-07-30 fix are intact copies of contaminated
                # extractions, so re-validate the body and repair rather than
                # skip. (Cheap: a read + regex scan per file.)
                if (
                    path.exists()
                    and sha256_file(path) == row["content_sha256"]
                    and _existing_output_is_valid(path)
                ):
                    continue
            pending.append(row)
        return pending

    def verify_outputs(self, programs_dir: Path) -> list[dict]:
        """Report every completed program whose file is missing or modified."""
        problems: list[dict] = []
        rows = self.conn.execute(
            "SELECT * FROM programs WHERE extraction_status='complete'"
        ).fetchall()
        for row in rows:
            filename = row["filename"]
            if not filename:
                problems.append({"poid": row["poid"], "problem": "no filename recorded"})
                continue
            path = programs_dir / str(filename)
            if not path.exists():
                problems.append(
                    {"poid": row["poid"], "filename": filename, "problem": "missing file"}
                )
                continue
            actual = sha256_file(path)
            if actual != row["content_sha256"]:
                problems.append(
                    {
                        "poid": row["poid"],
                        "filename": filename,
                        "problem": "hash mismatch",
                        "expected": row["content_sha256"],
                        "actual": actual,
                    }
                )
        return problems
