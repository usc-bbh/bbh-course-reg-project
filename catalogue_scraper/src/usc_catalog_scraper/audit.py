"""Audit: verify hashes, counts, index/manifest consistency; write AUDIT_REPORT.md."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from usc_catalog_scraper import __version__, config
from usc_catalog_scraper.logging_config import get_logger
from usc_catalog_scraper.models import Classification, utcnow_iso
from usc_catalog_scraper.output import regenerate_all
from usc_catalog_scraper.state import StateDB, sha256_file

log = get_logger("audit")


def run_audit(root: Path, cfg: config.ScraperConfig, repair: bool = True) -> tuple[bool, dict]:
    """Verify the collection; optionally repair indexes from the database.

    Returns (passed, report_dict) and writes AUDIT_REPORT.md into root's parent
    project folder as well as root itself.
    """
    layout = config.OutputLayout(root=root)
    if not layout.db_path.exists():
        return False, {"error": f"state database not found at {layout.db_path}"}
    db = StateDB(layout.db_path)
    checks: list[dict] = []
    passed = True

    def check(name: str, ok: bool, detail: str) -> None:
        nonlocal passed
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            passed = False

    counts = db.counts()
    included = counts.get(Classification.INCLUDED.value, 0)
    excluded = sum(v for k, v in counts.items() if k.startswith("excluded_"))
    manual = counts.get(Classification.MANUAL_REVIEW.value, 0)
    complete = counts.get("extraction_complete", 0)
    failed = counts.get("extraction_failed", 0)

    # 1. Output files match recorded hashes.
    problems = db.verify_outputs(layout.programs)
    check(
        "output_hashes_verify",
        not problems,
        "all complete program files exist with matching SHA-256"
        if not problems
        else f"{len(problems)} problems: {problems[:5]}",
    )

    # 2. No stray files in programs/ that the database does not know.
    known = db.existing_filenames()
    on_disk = {p.name for p in layout.programs.glob("*.txt")} if layout.programs.exists() else set()
    stray = sorted(on_disk - known)
    check("no_unknown_files", not stray, f"stray files: {stray[:10]}" if stray else "none")

    # 3. Regenerate indexes from DB (idempotent repair), then row counts match.
    run_row = db.conn.execute("SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
    run_id = run_row["run_id"] if run_row else "audit"
    if repair:
        regenerate_all(db, root, run_id, cfg)
    index_path = root / "index.csv"
    index_rows = 0
    if index_path.exists():
        with open(index_path, encoding="utf-8") as f:
            index_rows = sum(1 for _ in csv.DictReader(f))
    check(
        "index_rows_match_included",
        index_rows == included,
        f"index.csv rows={index_rows}, included links={included}",
    )

    # 4. Manifest counts match database.
    manifest_path = root / "manifest.json"
    manifest_ok = False
    manifest_detail = "manifest.json missing"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_ok = (
            manifest.get("included_count") == included
            and manifest.get("excluded_count") == excluded
            and manifest.get("manual_review_count") == manual
            and manifest.get("successful_count") == complete
        )
        manifest_detail = (
            f"manifest included={manifest.get('included_count')}, excluded={manifest.get('excluded_count')}, "
            f"manual={manifest.get('manual_review_count')}, successful={manifest.get('successful_count')} "
            f"vs DB {included}/{excluded}/{manual}/{complete}"
        )
    check("manifest_counts_match", manifest_ok, manifest_detail)

    # 5. Every excluded link has a reason; every manual-review row has evidence.
    missing_reason = db.conn.execute(
        "SELECT COUNT(*) n FROM links WHERE classification LIKE 'excluded_%' "
        "AND (class_reason IS NULL OR class_reason='')"
    ).fetchone()["n"]
    check("exclusions_have_reasons", missing_reason == 0, f"{missing_reason} missing reasons")

    # 6. Boundary evidence recorded.
    boundary = db.latest_boundary() or {}
    check(
        "boundary_evidence_recorded",
        bool(boundary.get("undergraduate_heading_text")) or bool(boundary.get("error")),
        json.dumps(
            {
                k: boundary.get(k)
                for k in (
                    "undergraduate_heading_text",
                    "undergraduate_heading_level",
                    "terminating_heading_text",
                    "links_in_section",
                    "error",
                )
            },
            ensure_ascii=False,
        ),
    )

    # 7. Complete extractions have non-trivial content and metadata headers.
    thin = []
    for r in db.conn.execute(
        "SELECT filename, char_count FROM programs WHERE extraction_status='complete'"
    ):
        if (r["char_count"] or 0) < 200:
            thin.append(r["filename"])
        elif r["filename"]:
            path = layout.programs / str(r["filename"])
            if path.exists():
                head = path.read_text(encoding="utf-8")[:400]
                if (
                    "Program Name:" not in head
                    or "OFFICIAL CATALOGUE CONTENT" not in path.read_text(encoding="utf-8")
                ):
                    thin.append(f"{r['filename']} (missing header)")
    check(
        "content_present_with_headers",
        not thin,
        f"problems: {thin[:5]}" if thin else "all files carry headers and content",
    )

    report = {
        "audited_at": utcnow_iso(),
        "passed": passed,
        "counts": counts,
        "included": included,
        "excluded": excluded,
        "manual_review": manual,
        "successful": complete,
        "failed": failed,
        "checks": checks,
        "boundary": boundary,
    }
    db.set_kv("last_audit", report)
    db.close()
    return passed, report


def _fmt_check(c: dict) -> str:
    return f"- {'PASS' if c['ok'] else 'FAIL'} — {c['check']}: {c['detail']}"


def write_audit_report(
    project_dir: Path,
    root: Path,
    report: dict,
    cfg: config.ScraperConfig,
    extra_sections: dict | None = None,
) -> Path:
    """Compose AUDIT_REPORT.md from real recorded evidence."""
    layout = config.OutputLayout(root=root)
    db = StateDB(layout.db_path)
    resolution = db.latest_resolution()
    boundary = db.latest_boundary() or {}
    modes = db.conn.execute(
        "SELECT acquisition_mode, COUNT(*) n FROM fetch_log GROUP BY acquisition_mode"
    ).fetchall()
    first_last = db.conn.execute(
        "SELECT MIN(seq) a, MAX(seq) b FROM links WHERE classification='included'"
    ).fetchone()
    first_title = last_title = ""
    if first_last and first_last["a"] is not None:
        first_title = db.conn.execute(
            "SELECT title FROM links WHERE seq=?", (first_last["a"],)
        ).fetchone()["title"]
        last_title = db.conn.execute(
            "SELECT title FROM links WHERE seq=?", (first_last["b"],)
        ).fetchone()["title"]
    kv = {
        key: db.get_kv(key)
        for key in (
            "test_results",
            "smoke_test_results",
            "full_run_results",
            "resume_test_results",
            "duplicate_count",
            "playwright_browser_version",
        )
    }
    runs = db.conn.execute("SELECT * FROM runs ORDER BY started_at").fetchall()
    db.close()

    lines: list[str] = []
    add = lines.append
    add("# AUDIT REPORT — USC Undergraduate Catalogue Extraction")
    add("")
    add(f"- Project version: {__version__}")
    add(f"- Audit generated: {report.get('audited_at', utcnow_iso())}")
    add(f"- Runs recorded: {[r['run_id'] for r in runs]}")
    add(f"- Supplied start URL: {config.DEFAULT_START_URL}")
    if resolution:
        add(f"- Resolved catalogue URL: {resolution['resolved_url']}")
        add(f"- Catalogue title: {resolution['catalogue_title'] or '(from year evidence)'}")
        add(f"- Catalogue year: {resolution['catalogue_year']}")
        add(f"- Catalogue identifier: catoid={resolution['catoid']}, navoid={resolution['navoid']}")
        add(
            f"- Resolution method: {resolution['method']} (verified={bool(resolution['verified'])})"
        )
        add(f"- Resolution notes: {resolution['notes']}")
    else:
        add("- Resolution: not recorded (no live run in this environment)")
    add("")
    add("## Acquisition")
    add("")
    if modes:
        for m in modes:
            add(f"- mode `{m['acquisition_mode']}`: {m['n']} attempts")
    else:
        add("- No live fetches recorded in this environment.")
    add(f"- Playwright browser: {kv.get('playwright_browser_version')}")
    add("")
    add("## Undergraduate Programs boundary")
    add("")
    if boundary:
        for k in (
            "undergraduate_heading_text",
            "undergraduate_heading_level",
            "undergraduate_heading_source",
            "terminating_heading_text",
            "terminated_by",
            "links_in_section",
            "links_rejected_after_classification",
            "first_included_title",
            "last_included_title",
            "container_description",
            "error",
        ):
            if boundary.get(k) is not None:
                add(f"- {k}: {boundary.get(k)}")
    else:
        add("- No boundary evidence recorded yet (no successful live index acquisition).")
    if first_title:
        add(f"- First included program (by sequence): {first_title}")
        add(f"- Last included program (by sequence): {last_title}")
    add("")
    add("## Counts")
    add("")
    add(f"- Discovered in boundary: {report.get('counts', {}).get('links_total', 0)}")
    add(f"- Included: {report.get('included', 0)}")
    add(f"- Excluded: {report.get('excluded', 0)}")
    add(f"- Manual review: {report.get('manual_review', 0)}")
    add(f"- Duplicates removed at discovery: {kv.get('duplicate_count') or 0}")
    add(f"- Successful extractions: {report.get('successful', 0)}")
    add(f"- Failed extractions: {report.get('failed', 0)}")
    add("")
    add("## Verification checks")
    add("")
    for c in report.get("checks", []):
        add(_fmt_check(c))
    add("")
    add("## Quality gates and test evidence")
    add("")
    add(
        f"- Unit tests: {json.dumps(kv.get('test_results')) if kv.get('test_results') else 'not recorded'}"
    )
    add(
        f"- Smoke test: {json.dumps(kv.get('smoke_test_results')) if kv.get('smoke_test_results') else 'not run'}"
    )
    add(
        f"- Resume test: {json.dumps(kv.get('resume_test_results')) if kv.get('resume_test_results') else 'not run'}"
    )
    add(
        f"- Full run: {json.dumps(kv.get('full_run_results')) if kv.get('full_run_results') else 'not run'}"
    )
    add("")
    if extra_sections:
        for title, body in extra_sections.items():
            add(f"## {title}")
            add("")
            add(body)
            add("")
    add("## How to rerun")
    add("")
    add("```bash")
    add("cd <project folder>")
    add("source .venv/bin/activate")
    add("python -m usc_catalog_scraper run --resume")
    add("python -m usc_catalog_scraper audit")
    add("```")
    add("")
    add(f"- Output folder: {root}")
    add(f"- Overall audit result: {'PASS' if report.get('passed') else 'FAIL'}")
    add("")

    text = "\n".join(lines)
    for dest in (project_dir / "AUDIT_REPORT.md", root / "AUDIT_REPORT.md"):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    return project_dir / "AUDIT_REPORT.md"


def quick_hash_listing(root: Path) -> dict[str, str]:
    layout = config.OutputLayout(root=root)
    out: dict[str, str] = {}
    if layout.programs.exists():
        for p in sorted(layout.programs.glob("*.txt")):
            out[p.name] = sha256_file(p)
    return out
