"""End-to-end pipeline tests against the fixture site (MockTransport, no network).

Covers: resolution, boundary, discovery, classification, extraction, rendering,
output files, indexes, manifest, audit, resume (no refetch), tamper repair,
interruption recovery, and idempotent indexes.
"""

import csv
import json
from pathlib import Path

from usc_catalog_scraper import config
from usc_catalog_scraper.audit import run_audit, write_audit_report
from usc_catalog_scraper.pipeline import run_pipeline
from usc_catalog_scraper.state import StateDB, sha256_file


def _cfg(tmp_path: Path, **kw) -> config.ScraperConfig:
    base = dict(
        workdir=tmp_path,
        delay_min=0.0,
        delay_max=0.01,
        max_retries=2,
        allow_browser=False,
        save_failure_screenshots=False,
        save_raw_html=True,
    )
    base.update(kw)
    return config.ScraperConfig(**base)


def _root(tmp_path: Path) -> Path:
    return tmp_path / "usc_undergraduate_catalogue_2026_2027"


def _program_fetches(calls: list[str]) -> list[str]:
    return [c for c in calls if "preview_program.php" in c]


def test_full_pipeline_and_resume_lifecycle(tmp_path, mock_site):
    cfg = _cfg(tmp_path)

    # ---------------------------------------------------------- first run
    outcome = run_pipeline(cfg, smoke=False)
    root = _root(tmp_path)
    assert outcome.stopped_reason == ""
    assert outcome.output_root == root
    assert outcome.catalogue_year == "2026-2027"
    assert outcome.resolved_url.endswith("catoid=22&navoid=9396")
    assert outcome.included == 6
    assert outcome.excluded == 2
    assert outcome.manual_review == 1
    assert outcome.duplicates == 1
    assert outcome.succeeded == 6 and outcome.failed == 0

    programs = sorted(p.name for p in (root / "programs").glob("*.txt"))
    assert programs == [
        "001_philosophy_ba.txt",
        "002_accounting_bs.txt",
        "003_computer_science_and_business_administration_bs.txt",
        "004_economics_mathematics_ba.txt",
        "008_design_bfa.txt",
        "009_music_performance_bm.txt",
    ]

    # File content: metadata header + official content, requirements preserved.
    sample = (root / "programs" / "002_accounting_bs.txt").read_text(encoding="utf-8")
    assert sample.startswith("Program Name: Accounting (BS)")
    assert "OFFICIAL CATALOGUE CONTENT" in sample
    assert "TABLE: Required Accounting Core" in sample
    assert "Row 1: ACCT 410 | Foundations of Accounting | 4" in sample
    assert "Row 2: Audit | ACCT 463 | Internal Audit | 4" in sample  # rowspan expanded
    assert "Add to Portfolio" not in sample
    assert sample.endswith("\n") and "\r" not in sample

    accordion = (root / "programs" / "008_design_bfa.txt").read_text(encoding="utf-8")
    assert "DES 320 Interaction Design (4 units)" in accordion  # hidden content kept

    # Boundary evidence recorded.
    boundary = json.loads(
        (root / "audit_evidence" / "index_boundary.json").read_text(encoding="utf-8")
    )
    assert boundary["undergraduate_heading_text"].replace("\xa0", " ") == "Undergraduate Programs"
    assert boundary["undergraduate_heading_level"] == 2
    assert boundary["terminating_heading_text"] == "Graduate Programs"
    assert boundary["links_in_section"] == 9
    assert boundary["first_included_title"].startswith("Philosophy")
    assert boundary["last_included_title"].startswith("Music Performance")
    assert (root / "audit_evidence" / "index_boundary.html").exists()

    # Indexes and manifest.
    with open(root / "index.csv", encoding="utf-8") as f:
        index_rows = list(csv.DictReader(f))
    assert len(index_rows) == 6
    assert all(r["extraction_status"] == "complete" for r in index_rows)
    assert all(r["content_sha256"] for r in index_rows)
    with open(root / "excluded_programs.csv", encoding="utf-8") as f:
        excluded_rows = list(csv.DictReader(f))
    assert {r["program_name"] for r in excluded_rows} == {"Chemistry (BS/MS)", "Spanish Minor"}
    assert all(r["exclusion_reason"] for r in excluded_rows)
    with open(root / "manual_review.csv", encoding="utf-8") as f:
        manual_rows = list(csv.DictReader(f))
    assert [r["program_name"] for r in manual_rows] == ["Interdisciplinary Studies"]
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["included_count"] == 6
    assert manifest["successful_count"] == 6
    assert manifest["duplicate_count"] == 1
    assert manifest["undergraduate_heading_text"].replace("\xa0", " ") == "Undergraduate Programs"
    assert len(manifest["output_file_hashes"]) == 6
    assert (root / "README.txt").exists()
    assert (root / "run_log.txt").exists()

    # Grad/minor/cert links from later sections never entered the link set.
    db = StateDB(config.OutputLayout(root=root).db_path)
    poids = {str(r["poid"]) for r in db.all_links()}
    assert poids == {"101", "102", "103", "104", "105", "106", "107", "109", "110"}
    assert "201" not in poids and "301" not in poids and "999" not in poids
    db.close()

    # Fetch log recorded direct_html attempts.
    first_run_program_fetches = len(_program_fetches(mock_site))
    assert first_run_program_fetches == 6

    hashes_before = {p.name: sha256_file(p) for p in (root / "programs").glob("*.txt")}

    # ------------------------------------------------------------- resume run
    mock_site.clear()
    outcome2 = run_pipeline(_cfg(tmp_path), smoke=False)
    assert outcome2.stopped_reason == ""
    assert outcome2.processed == 0  # nothing pending
    assert _program_fetches(mock_site) == []  # completed programs NOT refetched
    hashes_after = {p.name: sha256_file(p) for p in (root / "programs").glob("*.txt")}
    assert hashes_after == hashes_before  # files untouched, filenames stable
    with open(root / "index.csv", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 6  # no duplicate rows
    db = StateDB(config.OutputLayout(root=root).db_path)
    assert db.conn.execute("SELECT COUNT(*) n FROM links").fetchone()["n"] == 9
    assert db.conn.execute("SELECT COUNT(*) n FROM programs").fetchone()["n"] == 6
    db.close()

    # -------------------------------------------------- tamper detection+repair
    tampered = root / "programs" / "002_accounting_bs.txt"
    tampered.write_text("corrupted\n", encoding="utf-8")
    mock_site.clear()
    outcome3 = run_pipeline(_cfg(tmp_path), smoke=False)
    assert outcome3.processed == 1 and outcome3.succeeded == 1
    fetched = _program_fetches(mock_site)
    assert len(fetched) == 1 and "poid=102" in fetched[0]  # only the tampered one
    repaired = tampered.read_text(encoding="utf-8")
    assert "TABLE: Required Accounting Core" in repaired

    # Deterministic apart from the retrieval timestamp (a real re-fetch happened).
    def _stable(text: str) -> str:
        return "\n".join(
            ln
            for ln in text.split("\n")
            if not ln.startswith(("Retrieved At:", "Content SHA-256:"))
        )

    assert _stable(repaired) == _stable(sample)
    # Database hash matches the repaired file again.
    db = StateDB(config.OutputLayout(root=root).db_path)
    assert db.verify_outputs(root / "programs") == []
    db.close()

    # ------------------------------------------------ interruption recovery
    db = StateDB(config.OutputLayout(root=root).db_path)
    with db.tx() as c:
        c.execute("UPDATE programs SET extraction_status='pending' WHERE poid='109'")
    db.close()
    (root / "programs" / "008_design_bfa.txt").unlink()
    mock_site.clear()
    outcome4 = run_pipeline(_cfg(tmp_path), smoke=False)
    assert outcome4.succeeded == 1
    assert (root / "programs" / "008_design_bfa.txt").exists()
    fetched = _program_fetches(mock_site)
    assert len(fetched) == 1 and "poid=109" in fetched[0]

    # -------------------------------------------------------------- audit
    passed, report = run_audit(root, _cfg(tmp_path))
    assert passed, report["checks"]
    report_path = write_audit_report(tmp_path, root, report, _cfg(tmp_path))
    text = report_path.read_text(encoding="utf-8")
    assert "Overall audit result: PASS" in text
    assert "Undergraduate Programs" in text

    # Audit catches tampering.
    tampered.write_text("bad\n", encoding="utf-8")
    passed_bad, report_bad = run_audit(root, _cfg(tmp_path))
    assert not passed_bad
    assert any(not c["ok"] and c["check"] == "output_hashes_verify" for c in report_bad["checks"])


def test_max_programs_limits_work(tmp_path, mock_site):
    outcome = run_pipeline(_cfg(tmp_path, max_programs=2), smoke=True)
    assert outcome.processed == 2 and outcome.succeeded == 2
    root = _root(tmp_path)
    assert len(list((root / "programs").glob("*.txt"))) == 2
    # Second smoke run continues where the first stopped.
    outcome2 = run_pipeline(_cfg(tmp_path, max_programs=10), smoke=True)
    assert outcome2.succeeded == 4
    assert len(list((root / "programs").glob("*.txt"))) == 6
    db = StateDB(config.OutputLayout(root=root).db_path)
    smoke_results = db.get_kv("smoke_test_results")
    assert smoke_results["succeeded"] == 4
    db.close()


def test_boundary_failure_stops_run_without_scraping(tmp_path, monkeypatch):
    import httpx
    from tests.conftest import HTML_HEADERS, build_handler, load_fixture, patch_http

    def shell_index(request):
        return httpx.Response(200, text=load_fixture("index_shell.html"), headers=HTML_HEADERS)

    calls: list[str] = []
    patch_http(monkeypatch, build_handler(calls, overrides={"navoid=9396": shell_index}))
    outcome = run_pipeline(_cfg(tmp_path), smoke=False)
    assert outcome.stopped_reason
    assert "could not be acquired" in outcome.stopped_reason
    assert not _program_fetches(calls)  # refused to scrape anything


def test_wrong_boundary_heading_fails_loudly(tmp_path, mock_site):
    cfg = _cfg(tmp_path, boundary_heading="Nonexistent Section")
    outcome = run_pipeline(cfg, smoke=False)
    assert "BOUNDARY NOT PROVABLE" in outcome.stopped_reason
    root = _root(tmp_path)
    evidence = json.loads(
        (root / "audit_evidence" / "index_boundary.json").read_text(encoding="utf-8")
    )
    assert evidence["error"]
    assert evidence["headings_seen"]  # candidate headings reported for the user
    assert not list((root / "programs").glob("*.txt"))


def test_failed_program_recorded_and_retryable(tmp_path, monkeypatch):
    import httpx
    from tests.conftest import HTML_HEADERS, build_handler, load_fixture, patch_http

    def broken_program(request):
        if dict(request.url.params).get("poid") == "102":
            return httpx.Response(
                200, text=load_fixture("program_incomplete.html"), headers=HTML_HEADERS
            )
        return build_handler()(request)

    patch_http(monkeypatch, build_handler(overrides={"preview_program.php": broken_program}))
    outcome = run_pipeline(_cfg(tmp_path), smoke=False)
    assert outcome.succeeded == 5 and outcome.failed == 1
    root = _root(tmp_path)
    with open(root / "errors.csv", encoding="utf-8") as f:
        errors = list(csv.DictReader(f))
    assert any("102" in e["program_identifier"] for e in errors)
    db = StateDB(config.OutputLayout(root=root).db_path)
    row = db.program("22", "102")
    assert row["extraction_status"] in ("failed", "incomplete")
    # The failure remains pending for the next resume run.
    assert any(str(r["poid"]) == "102" for r in db.needs_extraction(root / "programs"))
    db.close()
