"""Output generation: filenames, atomic writes, metadata headers, indexes, manifest."""

from __future__ import annotations

import csv
import json
import os
import platform
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

from usc_catalog_scraper import APP_NAME, __version__, config
from usc_catalog_scraper.models import Classification, ProgramMetadata
from usc_catalog_scraper.state import StateDB

_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

MANUAL_REVIEW_RECOMMENDED_ACTION = (
    "Open the source URL, confirm the awarded credential, then either add the "
    "program to the include set (rerun with resume) or record why it is excluded."
)


def slugify(text: str, max_len: int = 70) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    text = re.sub(r"_{2,}", "_", text)
    if not text:
        text = "program"
    if text in _RESERVED:
        text = f"program_{text}"
    return text[:max_len].rstrip("_")


def build_filename(
    sequence: int,
    title: str,
    credential: str,
    poid: str,
    taken: set[str],
) -> str:
    base_title, _ = _split_credential_for_name(title)
    cred_slug = slugify(credential, 12) if credential else ""
    stem = f"{sequence:03d}_{slugify(base_title)}"
    if cred_slug and not stem.endswith(cred_slug):
        stem = f"{stem}_{cred_slug}"
    stem = stem[:100].rstrip("_")
    candidate = f"{stem}.txt"
    if candidate in taken:
        candidate = f"{stem}_poid{slugify(poid, 12)}.txt"
    return candidate


def _split_credential_for_name(title: str) -> tuple[str, str]:
    from usc_catalog_scraper.classification import extract_credential_field

    return extract_credential_field(title)


def atomic_write_text(path: Path, content: str) -> None:
    """Write via temp file + rename in the same directory; fsync for durability."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def metadata_header(meta: ProgramMetadata) -> str:
    lines = [
        f"Program Name: {meta.program_name}",
        f"Credential: {meta.credential}",
        f"School or Academic Unit: {meta.school}",
        f"Catalogue Year: {meta.catalogue_year}",
        f"Catalogue Identifier: {meta.catalogue_identifier}",
        f"Program Identifier: {meta.program_identifier}",
        f"Source URL: {meta.source_url}",
        f"Canonical URL: {meta.canonical_url}",
        f"Acquisition Mode: {meta.acquisition_mode}",
        f"Retrieved At: {meta.retrieved_at}",
        f"Content SHA-256: {meta.content_sha256}",
        f"Extraction Status: {meta.extraction_status}",
    ]
    if meta.breadcrumbs:
        lines.append(f"Breadcrumbs: {meta.breadcrumbs}")
    return "\n".join(lines) + "\n\nOFFICIAL CATALOGUE CONTENT\n\n"


def compose_program_file(meta: ProgramMetadata, content_text: str) -> str:
    body = content_text.rstrip("\n")
    return metadata_header(meta) + body + "\n"


# ---------------------------------------------------------------------------
# CSV / manifest generation (always regenerated from the state database)
# ---------------------------------------------------------------------------

INDEX_COLUMNS = [
    "sequence_number",
    "program_name",
    "credential",
    "school",
    "catalogue_year",
    "catalogue_identifier",
    "program_identifier",
    "source_url",
    "canonical_url",
    "acquisition_mode",
    "output_filename",
    "content_character_count",
    "content_line_count",
    "content_sha256",
    "source_html_sha256",
    "rendered_dom_sha256",
    "classification_status",
    "extraction_status",
    "retrieved_at",
]

EXCLUDED_COLUMNS = [
    "discovery_sequence",
    "program_name",
    "source_url",
    "canonical_url",
    "catalogue_identifier",
    "program_identifier",
    "section_found_in",
    "detected_credentials",
    "classification_evidence",
    "exclusion_reason",
    "classified_at",
]

MANUAL_REVIEW_COLUMNS = [
    "discovery_sequence",
    "program_name",
    "source_url",
    "program_identifier",
    "reason_for_review",
    "evidence",
    "recommended_action",
]

ERROR_COLUMNS = [
    "timestamp",
    "stage",
    "program_name",
    "source_url",
    "program_identifier",
    "attempt_number",
    "error_type",
    "error_message",
    "acquisition_mode",
    "retryable",
    "resolved",
]

FETCH_LOG_COLUMNS = [
    "timestamp",
    "url",
    "page_type",
    "attempt",
    "method",
    "acquisition_mode",
    "http_status",
    "content_type",
    "elapsed_seconds",
    "semantic_validation",
    "challenge_detected",
    "content_length",
    "raw_html_sha256",
    "rendered_dom_sha256",
    "result",
]


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    os.replace(tmp, path)


def write_index_csv(db: StateDB, root: Path) -> int:
    rows = []
    for r in db.program_rows():
        if r["classification"] != Classification.INCLUDED.value:
            continue
        rows.append(
            {
                "sequence_number": r["seq"],
                "program_name": r["program_name"] or r["title"],
                "credential": r["credential"] or "",
                "school": r["school"] or "",
                "catalogue_year": r["catalogue_year"] or "",
                "catalogue_identifier": f"catoid={r['catoid']}",
                "program_identifier": f"poid={r['poid']}",
                "source_url": r["absolute_url"],
                "canonical_url": r["canonical_url"],
                "acquisition_mode": r["acquisition_mode"] or "",
                "output_filename": r["filename"] or "",
                "content_character_count": r["char_count"] or 0,
                "content_line_count": r["line_count"] or 0,
                "content_sha256": r["content_sha256"] or "",
                "source_html_sha256": r["source_html_sha256"] or "",
                "rendered_dom_sha256": r["rendered_dom_sha256"] or "",
                "classification_status": r["classification"],
                "extraction_status": r["extraction_status"],
                "retrieved_at": r["retrieved_at"] or "",
            }
        )
    _write_csv(root / "index.csv", INDEX_COLUMNS, rows)
    return len(rows)


def write_excluded_csv(db: StateDB, root: Path) -> int:
    rows = []
    for r in db.all_links():
        cls = r["classification"] or ""
        if not cls.startswith("excluded_"):
            continue
        rows.append(
            {
                "discovery_sequence": r["seq"],
                "program_name": r["title"],
                "source_url": r["absolute_url"],
                "canonical_url": r["canonical_url"],
                "catalogue_identifier": f"catoid={r['catoid']}",
                "program_identifier": f"poid={r['poid']}",
                "section_found_in": r["section_heading"],
                "detected_credentials": r["detected_credentials"] or "[]",
                "classification_evidence": r["class_evidence"] or "{}",
                "exclusion_reason": r["class_reason"] or cls,
                "classified_at": r["classified_at"] or "",
            }
        )
    _write_csv(root / "excluded_programs.csv", EXCLUDED_COLUMNS, rows)
    return len(rows)


def write_manual_review_csv(db: StateDB, root: Path) -> int:
    rows = []
    for r in db.links_by_classification(Classification.MANUAL_REVIEW):
        rows.append(
            {
                "discovery_sequence": r["seq"],
                "program_name": r["title"],
                "source_url": r["absolute_url"],
                "program_identifier": f"poid={r['poid']}",
                "reason_for_review": r["class_reason"] or "",
                "evidence": r["class_evidence"] or "{}",
                "recommended_action": MANUAL_REVIEW_RECOMMENDED_ACTION,
            }
        )
    _write_csv(root / "manual_review.csv", MANUAL_REVIEW_COLUMNS, rows)
    return len(rows)


def write_errors_csv(db: StateDB, root: Path) -> int:
    rows = []
    for r in db.conn.execute("SELECT * FROM errors ORDER BY id"):
        rows.append(
            {
                "timestamp": r["ts"],
                "stage": r["stage"],
                "program_name": r["program_name"],
                "source_url": r["source_url"],
                "program_identifier": r["program_identifier"],
                "attempt_number": r["attempt_number"],
                "error_type": r["error_type"],
                "error_message": r["error_message"],
                "acquisition_mode": r["acquisition_mode"],
                "retryable": r["retryable"],
                "resolved": r["resolved"],
            }
        )
    _write_csv(root / "errors.csv", ERROR_COLUMNS, rows)
    return len(rows)


def write_fetch_log_csv(db: StateDB, root: Path) -> int:
    rows = []
    for r in db.conn.execute("SELECT * FROM fetch_log ORDER BY id"):
        rows.append(
            {
                "timestamp": r["ts"],
                "url": r["url"],
                "page_type": r["page_type"],
                "attempt": r["attempt"],
                "method": r["method"],
                "acquisition_mode": r["acquisition_mode"],
                "http_status": r["http_status"],
                "content_type": r["content_type"],
                "elapsed_seconds": r["elapsed_seconds"],
                "semantic_validation": r["semantic_validation"],
                "challenge_detected": r["challenge_detected"],
                "content_length": r["content_length"],
                "raw_html_sha256": r["raw_html_sha256"],
                "rendered_dom_sha256": r["rendered_dom_sha256"],
                "result": r["result"],
            }
        )
    _write_csv(root / "fetch_log.csv", FETCH_LOG_COLUMNS, rows)
    return len(rows)


def dependency_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for mod in ("httpx", "bs4", "lxml", "tenacity", "typer", "rich", "platformdirs", "playwright"):
        try:
            m = __import__(mod)
            out[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            out[mod] = "not installed"
    return out


def write_manifest(
    db: StateDB,
    root: Path,
    run_id: str,
    cfg: config.ScraperConfig,
    extra: dict | None = None,
) -> dict:
    counts = db.counts()
    boundary = db.latest_boundary() or {}
    resolution = db.latest_resolution()
    run = db.conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()

    included = counts.get(Classification.INCLUDED.value, 0)
    excluded = sum(v for k, v in counts.items() if k.startswith("excluded_"))
    manifest = {
        "application_name": APP_NAME,
        "application_version": __version__,
        "run_id": run_id,
        "run_started_at": run["started_at"] if run else "",
        "run_completed_at": (run["completed_at"] if run else "") or "",
        "reference_start_url": config.DEFAULT_START_URL,
        "resolved_catalogue_url": resolution["resolved_url"] if resolution else "",
        "catalogue_title": resolution["catalogue_title"] if resolution else "",
        "catalogue_year": resolution["catalogue_year"] if resolution else "",
        "catalogue_identifier": f"catoid={resolution['catoid']}" if resolution else "",
        "programs_page_url": resolution["resolved_url"] if resolution else "",
        "undergraduate_heading_text": boundary.get("undergraduate_heading_text"),
        "undergraduate_heading_level": boundary.get("undergraduate_heading_level"),
        "terminating_heading_text": boundary.get("terminating_heading_text"),
        "discovered_in_boundary": counts.get("links_total", 0),
        "included_count": included,
        "excluded_count": excluded,
        "manual_review_count": counts.get(Classification.MANUAL_REVIEW.value, 0),
        "duplicate_count": db.get_kv("duplicate_count", 0),
        "successful_count": counts.get("extraction_complete", 0),
        "failed_count": counts.get("extraction_failed", 0),
        "configuration": {k: str(v) for k, v in vars(cfg).items() if not k.startswith("_")},
        "python_version": sys.version.split()[0],
        "operating_system": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "dependency_versions": dependency_versions(),
        "playwright_browser_version": db.get_kv("playwright_browser_version", "not recorded"),
        "test_results": db.get_kv("test_results", "see AUDIT_REPORT.md"),
        "smoke_test_results": db.get_kv("smoke_test_results", "not run"),
        "full_run_results": db.get_kv("full_run_results", "not run"),
        "output_file_hashes": {
            str(r["filename"]): r["content_sha256"]
            for r in db.conn.execute(
                "SELECT filename, content_sha256 FROM programs "
                "WHERE extraction_status='complete' AND filename IS NOT NULL "
                "ORDER BY filename"
            )
        },
    }
    if extra:
        manifest.update(extra)
    path = root / "manifest.json"
    fd, tmp = tempfile.mkstemp(dir=str(root), prefix=".tmp_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)
        f.write("\n")
    os.replace(tmp, path)
    return manifest


def regenerate_all(db: StateDB, root: Path, run_id: str, cfg: config.ScraperConfig) -> dict:
    n_index = write_index_csv(db, root)
    n_excluded = write_excluded_csv(db, root)
    n_manual = write_manual_review_csv(db, root)
    n_errors = write_errors_csv(db, root)
    n_fetch = write_fetch_log_csv(db, root)
    manifest = write_manifest(db, root, run_id, cfg)
    return {
        "index_rows": n_index,
        "excluded_rows": n_excluded,
        "manual_review_rows": n_manual,
        "error_rows": n_errors,
        "fetch_log_rows": n_fetch,
        "manifest": bool(manifest),
    }


def write_output_readme(root: Path, catalogue_year: str) -> None:
    text = f"""USC UNDERGRADUATE CATALOGUE EXTRACTION — {catalogue_year}
=========================================================

WHAT IS IN THIS FOLDER

programs/            One UTF-8 plain-text file per standalone undergraduate
                     degree program. Each file starts with a metadata header,
                     then the line OFFICIAL CATALOGUE CONTENT, then the
                     program's catalogue content (requirements, courses,
                     tables, footnotes) rendered as readable text.
index.csv            One row per included program with hashes and counts.
excluded_programs.csv  Every link found in the Undergraduate Programs section
                     that was excluded, with the reason and evidence.
manual_review.csv    Programs the classifier could not settle confidently.
                     They were NOT silently dropped; review them by hand.
errors.csv           Every recorded error, with retry/resolution status.
fetch_log.csv        One row per page acquisition attempt.
manifest.json        Machine-readable summary of the whole run.
audit_evidence/      Boundary evidence, DOM snapshots, screenshots,
                     sample comparisons used for verification.
state/               SQLite database and browser profile that make safe
                     resume possible. Do not edit by hand.
AUDIT_REPORT.md      Human-readable audit of the run (in the project folder).

HOW TO RE-RUN OR RESUME

Use run_scraper.command (macOS double-click) in the project folder, or:
    python -m usc_catalog_scraper run --resume

Resume skips programs whose output file still matches its recorded hash,
re-fetches anything missing or changed, and never duplicates rows or files.
"""
    atomic_write_text(root / "README.txt", text)
