"""Filenames, atomic writes, headers, CSV/manifest generation and idempotence."""

import csv
import json

from usc_catalog_scraper import config
from usc_catalog_scraper.models import (
    Classification,
    ClassificationResult,
    DiscoveredLink,
    ExtractionStatus,
    ProgramMetadata,
)
from usc_catalog_scraper.output import (
    EXCLUDED_COLUMNS,
    INDEX_COLUMNS,
    MANUAL_REVIEW_COLUMNS,
    atomic_write_text,
    build_filename,
    compose_program_file,
    metadata_header,
    regenerate_all,
    slugify,
    write_excluded_csv,
    write_index_csv,
    write_manifest,
    write_manual_review_csv,
)
from usc_catalog_scraper.state import StateDB, sha256_file


def test_slugify_safety():
    assert slugify("Philosophy (BA)*") == "philosophy_ba"
    assert slugify("Économie & Société!!") == "economie_societe"
    assert slugify("con") == "program_con"
    assert slugify("") == "program"
    assert len(slugify("x" * 500)) <= 70


def test_build_filename_stable_and_collision_safe():
    taken: set[str] = set()
    a = build_filename(1, "Accounting (BS)", "BS", "102", taken)
    assert a == "001_accounting_bs.txt"
    taken.add(a)
    b = build_filename(1, "Accounting (BS)", "BS", "999", taken)
    assert b == "001_accounting_bs_poid999.txt"  # stable identifier, not random
    assert b != a


def test_atomic_write_and_trailing_newline(tmp_path):
    path = tmp_path / "sub" / "file.txt"
    atomic_write_text(path, "hello\n")
    assert path.read_text(encoding="utf-8") == "hello\n"
    assert not list(tmp_path.glob("**/.tmp_*"))  # temp file cleaned up


def test_metadata_header_fields():
    meta = ProgramMetadata(
        program_name="Philosophy (BA)",
        credential="BA",
        school="Dornsife College",
        catalogue_year="2026-2027",
        catalogue_identifier="catoid=22",
        program_identifier="poid=101",
        source_url="https://catalogue.usc.edu/preview_program.php?catoid=22&poid=101",
        canonical_url="https://catalogue.usc.edu/preview_program.php?catoid=22&poid=101",
        acquisition_mode="direct_html",
        retrieved_at="2026-07-09T00:00:00Z",
        content_sha256="ab" * 32,
        extraction_status="complete",
    )
    header = metadata_header(meta)
    for field in (
        "Program Name:",
        "Credential:",
        "School or Academic Unit:",
        "Catalogue Year:",
        "Catalogue Identifier:",
        "Program Identifier:",
        "Source URL:",
        "Canonical URL:",
        "Acquisition Mode:",
        "Retrieved At:",
        "Content SHA-256:",
        "Extraction Status:",
    ):
        assert field in header
    assert header.rstrip("\n").endswith("OFFICIAL CATALOGUE CONTENT")
    composed = compose_program_file(meta, "BODY TEXT\n")
    assert composed.endswith("BODY TEXT\n")


def _seed_db(tmp_path) -> StateDB:
    db = StateDB(tmp_path / "state" / "s.sqlite3")
    rows = [
        (1, "101", "Philosophy (BA)", Classification.INCLUDED),
        (2, "106", "Chemistry (BS/MS)", Classification.EXCLUDED_COMBINED),
        (3, "105", "Interdisciplinary Studies", Classification.MANUAL_REVIEW),
    ]
    for seq, poid, title, cls in rows:
        db.upsert_link(
            DiscoveredLink(
                sequence=seq,
                title=title,
                href=f"preview_program.php?catoid=22&poid={poid}",
                absolute_url=f"https://catalogue.usc.edu/preview_program.php?catoid=22&poid={poid}",
                canonical_url=f"https://catalogue.usc.edu/preview_program.php?catoid=22&poid={poid}",
                catoid="22",
                poid=poid,
                returnto="9396",
                section_heading="Undergraduate Programs",
                dom_path="a",
            ),
            "run1",
        )
        db.record_classification(
            "22", poid, ClassificationResult(cls, f"reason for {title}", {"t": title})
        )
    db.ensure_program_row("22", "101")
    return db


def test_csv_generation_columns_and_rows(tmp_path):
    db = _seed_db(tmp_path)
    root = tmp_path / "out"
    root.mkdir()
    programs = root / "programs"
    fname = db.reserve_filename("22", "101", "001_philosophy_ba.txt")
    atomic_write_text(
        programs / fname, "Program Name: Philosophy (BA)\n\nOFFICIAL CATALOGUE CONTENT\n\nbody\n"
    )
    db.mark_program(
        "22",
        "101",
        ExtractionStatus.COMPLETE,
        program_name="Philosophy (BA)",
        credential="BA",
        school="Dornsife",
        catalogue_year="2026-2027",
        acquisition_mode="direct_html",
        retrieved_at="2026-07-09T00:00:00Z",
        content_sha256=sha256_file(programs / fname),
        source_html_sha256="s" * 64,
        rendered_dom_sha256="",
        char_count=4,
        line_count=1,
    )
    assert write_index_csv(db, root) == 1
    assert write_excluded_csv(db, root) == 1
    assert write_manual_review_csv(db, root) == 1

    with open(root / "index.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == INDEX_COLUMNS
        row = next(reader)
        assert row["program_name"] == "Philosophy (BA)"
        assert row["output_filename"] == "001_philosophy_ba.txt"
        assert row["classification_status"] == "included"
    with open(root / "excluded_programs.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == EXCLUDED_COLUMNS
        row = next(reader)
        assert row["program_name"] == "Chemistry (BS/MS)"
        assert row["exclusion_reason"]
    with open(root / "manual_review.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == MANUAL_REVIEW_COLUMNS
        row = next(reader)
        assert row["program_name"] == "Interdisciplinary Studies"
        assert row["recommended_action"]
    db.close()


def test_manifest_counts_and_idempotence(tmp_path):
    db = _seed_db(tmp_path)
    root = tmp_path / "out"
    root.mkdir()
    cfg = config.ScraperConfig(workdir=tmp_path)
    db.start_run("run1", {})
    manifest = write_manifest(db, root, "run1", cfg)
    assert manifest["included_count"] == 1
    assert manifest["excluded_count"] == 1
    assert manifest["manual_review_count"] == 1
    assert manifest["application_name"] == "usc-catalog-scraper"

    first = regenerate_all(db, root, "run1", cfg)
    index_bytes = (root / "index.csv").read_bytes()
    second = regenerate_all(db, root, "run1", cfg)
    assert first["index_rows"] == second["index_rows"]
    assert (root / "index.csv").read_bytes() == index_bytes  # idempotent
    data = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert data["included_count"] == 1
    db.close()
