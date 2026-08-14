"""Regression tests for the 2026-08-13 unit-annotation-loss incident.

Symptom: four of the five `browser_rendered_dom` files in the 2026-2027 corpus
carried course lists whose unit counts were gone —

    - PPD 225 Solving Public Problems          (committed)
    PPD 225 Solving Public Problems Units: 4   (live page)

58 course lines across 212_addiction_science_minor, 318_gender_and_social_
justice_minor, 365_law_and_public_policy_minor and 450_southeast_asia_and_its_
people_minor. Every gate passed them: title heading present, course codes
present, no contamination, ample length. Units are precisely what the
degree-audit engine consumes, so the loss was silent and load-bearing.

Proven cause: acalog renders a course line as

    <li class="acalog-course"><span><a ...>PPD 225 …</a> Units: 4</span></li>

where the unit count is a TEXT NODE attached after the anchor during acalog's
JS enhancement pass. The browser readiness gate was `h1 present &&
body.innerText.length > 400` — both true well before that pass runs — so
`_stabilize()` saw two identical polls of the half-built DOM and accepted it.
The direct-HTML path was never affected: the raw markup already carries the
text node. The renderer was never at fault.

Two fixes, both covered here:
  1. `PROGRAM_PAGE_READY_JS` refuses a DOM that has course links but no
     rendered unit annotation.
  2. `validate_extracted_text` rejects a body whose course bullets have lost
     their units, so such an extraction can never be written again.

The fixtures are the real Law and Public Policy Minor page (poid=32309),
captured live 2026-08-13, in both states.
"""

from __future__ import annotations

import hashlib
import re

import pytest
from bs4 import BeautifulSoup

from conftest import load_fixture
from usc_catalog_scraper import config
from usc_catalog_scraper.acquisition import (
    IS_COURSE_DETAIL_TOGGLE_JS,
    PROGRAM_PAGE_READY_JS,
)
from usc_catalog_scraper.extraction import clean_content, select_main_container
from usc_catalog_scraper.models import ProgramMetadata
from usc_catalog_scraper.output import INDEX_COLUMNS, compose_program_file
from usc_catalog_scraper.output_validation import (
    course_bullet_unit_coverage,
    unit_annotation_loss,
    validate_extracted_text,
)
from usc_catalog_scraper.text_renderer import render_text

RENDERED = "program_units_rendered.html"
MISSING = "program_units_missing.html"
PROGRAM = "Law and Public Policy Minor"

# The six Required Courses, each 4 units on the live page.
EXPECTED_COURSES = (
    "PPD 225",
    "PPD 314",
    "PPD 315",
    "POSC 340",
    "LAW 300",
    "PPD 357",
)


def _body(fixture: str) -> str:
    cfg = config.ScraperConfig()
    soup = BeautifulSoup(load_fixture(fixture), "lxml")
    container, _reason = select_main_container(soup, cfg)
    return render_text(clean_content(container, cfg), cfg)


# --------------------------------------------------------------- the fixtures


def test_fixtures_differ_only_in_unit_text_nodes() -> None:
    """The two fixtures must isolate the defect and nothing else."""
    rendered = re.sub(r"<!--.*?-->", "", load_fixture(RENDERED), flags=re.S)
    missing = re.sub(r"<!--.*?-->", "", load_fixture(MISSING), flags=re.S)
    assert rendered != missing
    assert re.sub(r"</a> Units: \d+", "</a>", rendered) == missing


# ------------------------------------------------------- extraction behaviour


def test_units_survive_extraction_when_rendered() -> None:
    """A fully-rendered acalog course list keeps every unit count."""
    body = _body(RENDERED)
    for code in EXPECTED_COURSES:
        assert code in body, f"{code} missing from extracted body"
    with_units, without_units = course_bullet_unit_coverage(body)
    assert with_units >= len(EXPECTED_COURSES)
    assert without_units == 0


def test_or_conjunction_preserved_alongside_units() -> None:
    """'Units: 4 or' must not lose the 'or' that carries requirement logic."""
    body = _body(RENDERED)
    assert re.search(r"POSC 340 Constitutional Law\s+Units:\s*4\s+or", body)


def test_mid_enhancement_dom_loses_units() -> None:
    """Reproduces the defect: the same page, captured too early."""
    body = _body(MISSING)
    for code in EXPECTED_COURSES:
        assert code in body, "course titles survive — only the units are lost"
    with_units, without_units = course_bullet_unit_coverage(body)
    assert with_units == 0
    assert without_units >= len(EXPECTED_COURSES)


# ---------------------------------------------------------- the write gate


def test_validator_rejects_unit_annotation_loss() -> None:
    """The defective body must never reach disk again."""
    ok, evidence = validate_extracted_text(_body(MISSING), PROGRAM)
    assert ok is False
    assert evidence["unit_annotation_loss"] is True
    assert any(r.startswith("course_units_missing") for r in evidence["reasons"])


def test_validator_accepts_the_rendered_body() -> None:
    """The fix must not reject the correct extraction."""
    ok, evidence = validate_extracted_text(_body(RENDERED), PROGRAM)
    assert ok is True, evidence["reasons"]
    assert evidence["unit_annotation_loss"] is False


@pytest.mark.parametrize(
    "text, expected",
    [
        # Course RANGES legitimately carry no single unit value; one such line
        # among many normal ones must not trip the rule (241/275/276/332).
        ("\n".join([f"- CHEM {200 + i} Course Units: 4" for i in range(20)] + ["- DANC 180-189c Dance Technique Courses*"]), False),
        # Prose-only programme: no course bullets at all (Interdisciplinary Studies).
        ("# Interdisciplinary Studies (BA)\n\nA self-designed major.", False),
        # Below the 3-bullet floor: too little evidence to judge.
        ("- PPD 225 Solving Public Problems\n- PPD 314 Public Policy and Law", False),
        # The defect: every bullet stripped.
        ("\n".join(f"- PPD {300 + i} Some Course" for i in range(6)), True),
    ],
)
def test_unit_loss_rule_boundaries(text: str, expected: bool) -> None:
    assert unit_annotation_loss(text) is expected


# ------------------------------------------------------------ readiness gate


def test_readiness_js_requires_units_when_courses_present() -> None:
    """The gate must key on rendered units, not just an h1 and some text."""
    assert "Units" in PROGRAM_PAGE_READY_JS
    assert "showCourse" in PROGRAM_PAGE_READY_JS
    assert "block_content" in PROGRAM_PAGE_READY_JS


def test_course_toggle_predicate_targets_acalog_course_controls() -> None:
    """The predicate must recognise every form of course-detail toggle."""
    for marker in ("li.acalog-course", "showCourse", "hideCatalogData", "preview_td"):
        assert marker in IS_COURSE_DETAIL_TOGGLE_JS


# --------------------------------------------------------- hash semantics


def test_index_publishes_content_and_file_hashes_separately() -> None:
    """content_sha256 tracks USC's text; file_sha256 tracks the whole file.

    They must be distinct columns: the file carries `Retrieved At`, so its hash
    changes on every run. Publishing the file hash under the content name made
    change-detection report a change on every scrape.
    """
    assert "content_sha256" in INDEX_COLUMNS
    assert "file_sha256" in INDEX_COLUMNS

    meta = ProgramMetadata(
        program_name=PROGRAM,
        catalogue_year="2026-2027",
        program_identifier="poid=32309",
        retrieved_at="2026-08-13T00:00:00Z",
        extraction_status="complete",
    )
    body = "# Law and Public Policy Minor\n\n- PPD 225 Solving Public Problems Units: 4"
    meta.content_sha256 = hashlib.sha256(body.encode()).hexdigest()
    composed = compose_program_file(meta, body)

    # The header reports the CONTENT hash...
    assert f"Content SHA-256: {meta.content_sha256}" in composed
    # ...which is not the hash of the file that contains it.
    assert hashlib.sha256(composed.encode()).hexdigest() != meta.content_sha256


def test_retrieved_at_changes_file_hash_but_not_content_hash() -> None:
    """The exact property a consumer relies on to detect changed text."""
    body = "# Latin Minor\n\n- LAT 222 Intermediate Latin Units: 4"
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    composed = [
        compose_program_file(
            ProgramMetadata(
                program_name="Latin Minor",
                retrieved_at=stamp,
                extraction_status="complete",
                content_sha256=content_hash,
            ),
            body,
        )
        for stamp in ("2026-08-13T00:00:00Z", "2026-09-01T12:34:56Z")
    ]
    assert composed[0] != composed[1]
    file_hashes = {hashlib.sha256(c.encode()).hexdigest() for c in composed}
    assert len(file_hashes) == 2, "file hash must change with Retrieved At"
    # The content hash is identical across both runs — the text did not change.
    for c in composed:
        assert f"Content SHA-256: {content_hash}" in c
