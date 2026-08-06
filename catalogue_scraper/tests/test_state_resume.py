"""SQLite state and resume-behavior tests."""

from usc_catalog_scraper.models import (
    Classification,
    ClassificationResult,
    DiscoveredLink,
    ExtractionStatus,
)
from usc_catalog_scraper.output import atomic_write_text
from usc_catalog_scraper.state import StateDB, sha256_file


def _link(seq=1, poid="101", title="Philosophy (BA)") -> DiscoveredLink:
    return DiscoveredLink(
        sequence=seq,
        title=title,
        href=f"preview_program.php?catoid=22&poid={poid}",
        absolute_url=f"https://catalogue.usc.edu/preview_program.php?catoid=22&poid={poid}",
        canonical_url=f"https://catalogue.usc.edu/preview_program.php?catoid=22&poid={poid}",
        catoid="22",
        poid=poid,
        returnto="9396",
        section_heading="Undergraduate Programs",
        dom_path="td>ul>li>a",
    )


def _db(tmp_path) -> StateDB:
    return StateDB(tmp_path / "state.sqlite3")


def _valid_output_text(program_name: str = "Philosophy (BA)") -> str:
    """A body that passes output validation.

    needs_extraction() re-validates existing files (incident 2026-07-30:
    contaminated files had intact hashes and were therefore skipped forever),
    so resume fixtures must carry realistic content, not placeholders.
    """
    return (
        f"Program Name: {program_name}\n"
        "Extraction Status: complete\n\n"
        "OFFICIAL CATALOGUE CONTENT\n\n"
        f"# {program_name}\n\n"
        "---\n\n"
        "The major requires a minimum of 128 units, including the courses "
        "listed below, and a cumulative grade point average of C (2.0) in all "
        "upper-division course work applied toward the major.\n\n"
        "## Required Courses\n\n"
        "- PHIL 140g Ethics Units: 4\n"
        "- PHIL 240 Logic Units: 4\n"
        "- PHIL 350 Metaphysics Units: 4\n\n"
        "## Total units: 128\n"
    )


def test_upsert_keeps_sequence_stable(tmp_path):
    db = _db(tmp_path)
    assert db.upsert_link(_link(seq=7), "run1") == 7
    # Re-discovered later with a different sequence: original kept.
    assert db.upsert_link(_link(seq=2, title="Philosophy (BA)*"), "run2") == 7
    row = db.link("22", "101")
    assert row["seq"] == 7
    assert row["title"] == "Philosophy (BA)*"  # mutable fields refreshed
    assert db.conn.execute("SELECT COUNT(*) n FROM links").fetchone()["n"] == 1
    db.close()


def test_classification_and_program_rows(tmp_path):
    db = _db(tmp_path)
    db.upsert_link(_link(), "run1")
    db.record_classification(
        "22",
        "101",
        ClassificationResult(
            Classification.INCLUDED, "undergrad only", {"credential_field": "BA"}, ["BA"]
        ),
    )
    db.ensure_program_row("22", "101")
    db.ensure_program_row("22", "101")  # idempotent
    assert db.conn.execute("SELECT COUNT(*) n FROM programs").fetchone()["n"] == 1
    row = db.link("22", "101")
    assert row["classification"] == "included"
    assert "BA" in row["detected_credentials"]
    db.close()


def test_needs_extraction_skips_verified_complete(tmp_path):
    db = _db(tmp_path)
    programs_dir = tmp_path / "programs"
    db.upsert_link(_link(), "run1")
    db.record_classification("22", "101", ClassificationResult(Classification.INCLUDED, "ok", {}))
    db.ensure_program_row("22", "101")
    assert len(db.needs_extraction(programs_dir)) == 1  # pending

    fname = db.reserve_filename("22", "101", "001_philosophy_ba.txt")
    path = programs_dir / fname
    atomic_write_text(path, _valid_output_text())
    db.mark_program(
        "22",
        "101",
        ExtractionStatus.COMPLETE,
        content_sha256=sha256_file(path),
        char_count=4,
        line_count=1,
    )
    assert db.needs_extraction(programs_dir) == []  # verified complete -> skipped
    db.close()


def test_modified_output_detected_and_repending(tmp_path):
    db = _db(tmp_path)
    programs_dir = tmp_path / "programs"
    db.upsert_link(_link(), "run1")
    db.record_classification("22", "101", ClassificationResult(Classification.INCLUDED, "ok", {}))
    db.ensure_program_row("22", "101")
    fname = db.reserve_filename("22", "101", "001_philosophy_ba.txt")
    path = programs_dir / fname
    atomic_write_text(path, "original content\n")
    db.mark_program("22", "101", ExtractionStatus.COMPLETE, content_sha256=sha256_file(path))

    path.write_text("tampered content\n", encoding="utf-8")
    problems = db.verify_outputs(programs_dir)
    assert len(problems) == 1 and problems[0]["problem"] == "hash mismatch"
    assert len(db.needs_extraction(programs_dir)) == 1  # will be re-fetched
    db.close()


def test_missing_output_detected(tmp_path):
    db = _db(tmp_path)
    programs_dir = tmp_path / "programs"
    db.upsert_link(_link(), "run1")
    db.record_classification("22", "101", ClassificationResult(Classification.INCLUDED, "ok", {}))
    db.ensure_program_row("22", "101")
    db.reserve_filename("22", "101", "001_philosophy_ba.txt")
    db.mark_program("22", "101", ExtractionStatus.COMPLETE, content_sha256="0" * 64)
    problems = db.verify_outputs(programs_dir)
    assert problems and problems[0]["problem"] == "missing file"
    assert len(db.needs_extraction(programs_dir)) == 1
    db.close()


def test_filename_reservation_stable(tmp_path):
    db = _db(tmp_path)
    db.upsert_link(_link(), "run1")
    db.ensure_program_row("22", "101")
    first = db.reserve_filename("22", "101", "001_philosophy_ba.txt")
    second = db.reserve_filename("22", "101", "999_other_name.txt")
    assert first == second == "001_philosophy_ba.txt"
    db.close()


def test_fetch_and_error_logging(tmp_path):
    db = _db(tmp_path)
    db.log_fetch(
        url="https://x",
        page_type="program_page",
        method="httpx",
        acquisition_mode="direct_html",
        http_status=200,
        result="ok",
    )
    db.log_error(
        stage="extraction",
        source_url="https://x",
        error_type="Boom",
        error_message="failed",
        retryable=True,
    )
    assert db.conn.execute("SELECT COUNT(*) n FROM fetch_log").fetchone()["n"] == 1
    assert db.conn.execute("SELECT COUNT(*) n FROM errors").fetchone()["n"] == 1
    db.mark_errors_resolved("https://x")
    assert db.conn.execute("SELECT resolved FROM errors").fetchone()["resolved"] == 1
    db.close()


def test_kv_and_boundary_roundtrip(tmp_path):
    db = _db(tmp_path)
    db.set_kv("duplicate_count", 3)
    assert db.get_kv("duplicate_count") == 3
    db.save_boundary("run1", {"undergraduate_heading_text": "Undergraduate Programs"})
    assert db.latest_boundary()["undergraduate_heading_text"] == "Undergraduate Programs"
    db.close()


def test_interrupted_run_recovery(tmp_path):
    """Simulate a crash mid-run: one complete, one pending. Resume picks only pending."""
    db = _db(tmp_path)
    programs_dir = tmp_path / "programs"
    for seq, poid in ((1, "101"), (2, "102")):
        db.upsert_link(_link(seq=seq, poid=poid), "run1")
        db.record_classification(
            "22", poid, ClassificationResult(Classification.INCLUDED, "ok", {})
        )
        db.ensure_program_row("22", poid)
    fname = db.reserve_filename("22", "101", "001_a.txt")
    path = programs_dir / fname
    atomic_write_text(path, _valid_output_text())
    db.mark_program("22", "101", ExtractionStatus.COMPLETE, content_sha256=sha256_file(path))
    # 102 was mid-flight when the run died: still pending.
    pending = db.needs_extraction(programs_dir)
    assert [str(r["poid"]) for r in pending] == ["102"]
    db.close()


def test_contaminated_but_unmodified_output_is_repended(tmp_path):
    """Incident 2026-07-30: an intact hash must not certify bad content."""
    db = _db(tmp_path)
    programs_dir = tmp_path / "programs"
    db.upsert_link(_link(), "run1")
    db.record_classification("22", "101", ClassificationResult(Classification.INCLUDED, "ok", {}))
    db.ensure_program_row("22", "101")
    fname = db.reserve_filename("22", "101", "001_philosophy_ba.txt")
    path = programs_dir / fname
    atomic_write_text(
        path,
        "Program Name: Philosophy (BA)\n"
        "Extraction Status: complete\n\n"
        "OFFICIAL CATALOGUE CONTENT\n\n"
        "Skip to Navigation\n\nTABLE:\nRow 1:  | University of Southern California\n"
        + "filler "
        * 100,
    )
    # hash matches perfectly: the file is unmodified, just wrong
    db.mark_program("22", "101", ExtractionStatus.COMPLETE, content_sha256=sha256_file(path))
    assert db.verify_outputs(programs_dir) == []  # no hash problem
    pending = db.needs_extraction(programs_dir)
    assert [str(r["poid"]) for r in pending] == ["101"], "contaminated file must be repaired"
    db.close()
