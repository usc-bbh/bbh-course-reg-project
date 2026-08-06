"""Regression tests for the 2026-07-30 contaminated-output incident.

Symptom: `107_environmental_science_and_health_ba.txt` contained site
navigation, the page header table flattened as "TABLE: / Row 1: / Row 2:", the
programme blurb repeated 8 times, and a literal <script> tag — while the file
claimed `Extraction Status: complete`. 158 of 470 outputs were affected.

Proven cause: container selection was purely score-based, so on pages whose
programme content is short relative to the page chrome the whole <body>
outscored `td.block_content` (poid=31805: body 305.0 vs content region 304.7 —
a 0.3-point margin) and the renderer then flattened the page-layout table.
Nothing validated the extracted text, so the result was saved as valid.

The fixtures are the real live pages captured during the investigation:
  program_107_...html  reproduces the defect (short content, big chrome)
  program_106_...html  the neighbouring page that always worked
"""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from conftest import load_fixture
from usc_catalog_scraper import config
from usc_catalog_scraper.extraction import (
    ContentRegionNotFound,
    clean_content,
    select_main_container,
)
from usc_catalog_scraper.output_validation import validate_extracted_text
from usc_catalog_scraper.text_renderer import render_text

F107 = "program_107_environmental_science_health_ba.html"
F106 = "program_106_environmental_engineering_bs.html"

CONTAMINATION_MARKERS = (
    "Skip to Navigation",
    "Row 1:",
    "Begin Responsive",
    "<script",
    "| University of Southern California",
)


def _cfg() -> config.ScraperConfig:
    return config.ScraperConfig()


def _extract(fixture: str, *, strict: bool) -> tuple[str, str]:
    soup = BeautifulSoup(load_fixture(fixture), "lxml")
    container, evidence = select_main_container(soup, _cfg(), require_content_region=strict)
    return render_text(clean_content(container, _cfg()), _cfg()), evidence


# --------------------------------------------------------------- the defect
def test_107_unguarded_selection_still_picks_the_whole_page():
    """Documents the defect: without the guard, body wins on this page."""
    text, evidence = _extract(F107, strict=False)
    assert "document body fallback" in evidence, evidence
    assert any(m in text for m in CONTAMINATION_MARKERS)


def test_107_content_region_requirement_fixes_extraction():
    text, evidence = _extract(F107, strict=True)
    assert "block_content" in evidence, evidence
    # tier marker: the platform content region won, and the evidence must record
    # that the whole body outscored it yet was ineligible
    assert "[platform-content-region]" in evidence, evidence
    assert "outscored-but-ineligible: document body fallback" in evidence, evidence
    for marker in CONTAMINATION_MARKERS:
        assert marker not in text, f"contamination survived: {marker}"
    # and the real programme content is present
    assert text.lstrip().startswith("# Environmental Science and Health (BA)")
    assert "BISC 120Lg" in text
    assert "ENST 495" in text
    assert "Total units: 52" in text


def test_106_unaffected_by_the_guard():
    """The page that already worked must produce the same content region."""
    strict_text, strict_ev = _extract(F106, strict=True)
    loose_text, _ = _extract(F106, strict=False)
    assert "block_content" in strict_ev
    assert strict_text == loose_text
    assert strict_text.lstrip().startswith("# Environmental Engineering (BS)")


def test_no_content_region_raises_instead_of_using_the_document():
    soup = BeautifulSoup(
        "<html><body><nav>Skip to Navigation</nav>"
        "<table><tr><td>x</td><td>University of Southern California</td></tr></table>"
        "<p>Some page text that is not a catalogue content region at all.</p>"
        "</body></html>",
        "lxml",
    )
    with pytest.raises(ContentRegionNotFound) as excinfo:
        select_main_container(soup, _cfg(), require_content_region=True)
    assert excinfo.value.candidates_seen  # reports what it saw


# ----------------------------------------------------- output-text validation
def test_validator_rejects_the_exact_broken_107_body():
    broken = (
        "Skip to Navigation\n\nTABLE:\nRow 1:  | University of Southern California\n"
        "Row 2:  | / Jul 16, 2026 / Begin Responsive End Responsive / "
        "Environmental Science and Health (BA) The degree combines interdisciplinary "
        "courses on sustainability with traditional biology and chemistry content to "
        "provide options for students preparing for the health professions. ; "
        "Required Courses Total units: 52\n\n"
        '<script src="js/smlinks.js" type="text/javascript"></script>\n'
    )
    ok, ev = validate_extracted_text(broken, "Environmental Science and Health (BA)")
    assert not ok
    assert ev["fatal_patterns"]
    assert "no_program_title_heading_in_body" in ev["reasons"]
    assert ev["fatal_excerpts"]


def test_validator_accepts_the_repaired_107_body():
    text, _ = _extract(F107, strict=True)
    ok, ev = validate_extracted_text(text, "Environmental Science and Health (BA)")
    assert ok, ev["reasons"]
    assert ev["title_heading_present"]
    assert ev["course_code_count"] > 10


@pytest.mark.parametrize(
    "body,expect_reason",
    [
        ("", "empty_extraction"),
        ("# Physics (BS)\n\nLoading...\n\nPHYS 151 Units: 4\n" + "x " * 300, "contaminated_text"),
        (
            '# Physics (BS)\n\n<div class="x">PHYS 151 Units: 4</div>\n' + "x " * 300,
            "contaminated_text",
        ),
        (
            "# Physics (BS)\n\nProse only, no courses at all.\n" + "word " * 200,
            "no_course_or_unit_content",
        ),
        ("PHYS 151 Units: 4\n" + "word " * 200, "no_program_title_heading_in_body"),
        ("# Physics (BS)\n\nPHYS 151 Units: 4\n", "body_under_200_chars"),
    ],
)
def test_validator_failure_modes(body, expect_reason):
    ok, ev = validate_extracted_text(body, "Physics (BS)")
    assert not ok
    assert any(r.startswith(expect_reason) for r in ev["reasons"]), ev["reasons"]


def test_validator_accepts_a_legitimately_short_programme():
    """Short pages pass on semantics (title + courses), not on length."""
    body = (
        "# Dance Minor\n\n---\n\nThe minor requires 20 units chosen with an adviser "
        "from the courses listed below, at least 12 of which must be upper division "
        "and completed in residence at the university.\n\n"
        "## Required Courses\n\n"
        "- DANC 101 Dance Technique Units: 2\n"
        "- DANC 240 Dance History Units: 4\n"
        "- DANC 380 Choreography Units: 4\n\n"
        "## Total units: 20\n"
    )
    ok, ev = validate_extracted_text(body, "Dance Minor")
    assert ok, ev["reasons"]


def test_validator_flags_rowspan_style_duplication():
    sentence = (
        "The Environmental Science and Health BA degree combines interdisciplinary "
        "courses on sustainability with traditional biology and chemistry content. "
    )
    body = "# Environmental Science and Health (BA)\n\nBISC 120 Units: 4\n\n" + sentence * 5
    ok, ev = validate_extracted_text(body, "Environmental Science and Health (BA)")
    assert not ok
    assert ev["max_repeated_sentence_count"] >= 3
    assert any(r.startswith("duplicated_sentence_x") for r in ev["reasons"])


# ------------------------------------------------- overwrite / resume safety
def test_resume_revalidates_existing_outputs(tmp_path):
    """A contaminated file with an intact hash must be queued for repair."""
    from usc_catalog_scraper.state import _existing_output_is_valid

    good = tmp_path / "good.txt"
    good.write_text(
        "Program Name: Environmental Engineering (BS)\n"
        "Extraction Status: complete\n\n"
        "OFFICIAL CATALOGUE CONTENT\n\n"
        "# Environmental Engineering (BS)\n\n"
        "- CE 108 Programming Units: 2\n- CE 110 Introduction Units: 2\n"
        "- ENE 200 Environmental Engineering Principles Units: 4\n\n"
        "## Total units: 130\n" + "detail " * 100,
        encoding="utf-8",
    )
    bad = tmp_path / "bad.txt"
    bad.write_text(
        "Program Name: Environmental Science and Health (BA)\n"
        "Extraction Status: complete\n\n"
        "OFFICIAL CATALOGUE CONTENT\n\n"
        "Skip to Navigation\n\nTABLE:\nRow 1:  | University of Southern California\n"
        + "filler "
        * 100,
        encoding="utf-8",
    )
    assert _existing_output_is_valid(good) is True
    assert _existing_output_is_valid(bad) is False
    assert _existing_output_is_valid(tmp_path / "missing.txt") is False


def test_validator_accepts_a_prose_only_programme():
    """Interdisciplinary Studies (BA) has no course list — it is still valid.

    Live rejection during the corrected run 2026-07-30: the container was
    correct (td.block_content) and the body was 1,978 clean characters, but the
    first version of this validator demanded course codes. A self-designed major
    legitimately has none.
    """
    body = (
        "# Interdisciplinary Studies (BA)\n\n---\n\n"
        "## Interdisciplinary Major\n\n"
        "The interdisciplinary major allows students to create an individual, "
        "original major. It is a flexible option available when a combination of "
        "existing majors and academic minors does not adequately fulfill a "
        "student's educational goals.\n\n"
        "## Admission\n\n"
        "Admission to the interdisciplinary major is by application. Interested "
        "students must have a GPA of 3.0 or above.\n\n"
        "## Program Requirements\n\n"
        "Students establish an academic contract, which includes a minimum of "
        "nine (4-unit) upper-division courses, distributed in at least two "
        "fields, combined in a senior thesis.\n\n"
        "## Restrictions\n\n"
        "Course prerequisites cannot be waived.\n"
    )
    ok, ev = validate_extracted_text(body, "Interdisciplinary Studies (BA)")
    assert ok, ev["reasons"]
    assert ev["course_code_count"] == 0
    assert ev["prose_only_programme"] is True


def test_contaminated_body_still_rejected_even_with_section_words():
    """Relaxing the course rule must not let contamination through."""
    body = (
        "Skip to Navigation\n\nTABLE:\nRow 1:  | University of Southern California\n"
        "Admission requirement restriction elective curriculum thesis\n" + "filler " * 200
    )
    ok, ev = validate_extracted_text(body, "Interdisciplinary Studies (BA)")
    assert not ok
    assert ev["fatal_patterns"]


def test_validator_accepts_real_cross_reference_stub_pages():
    """Two live pages are ~300-450 chars because USC points elsewhere.

    Verified against catalogue.usc.edu 2026-07-30 (poid=31912, poid=32395): the
    extraction is complete and the page really is that short. Rejecting these
    would discard valid catalogue data.
    """
    nonprofits = (
        "# Nonprofits, Philanthropy and Volunteerism Interdisciplinary Minor\n\n---\n\n"
        "This four-course minor enables students to learn about the nonprofit sector "
        "— its organizations, philanthropy and voluntary action. See complete "
        "description in the USC Price School of Public Policy section.\n\n---\n"
    )
    consumer = (
        "# Consumer Behavior Interdisciplinary Minor\n\n---\n\n"
        "This interdisciplinary minor explores consumer thinking from the perspective "
        "of psychology, marketing, economics, anthropology, sociology and other "
        "departments interested in popular culture. Why do people form the attitudes "
        "and impressions they do? See USC Marshall School of Business .\n\n---\n"
    )
    for body, name in (
        (nonprofits, "Nonprofits, Philanthropy and Volunteerism Interdisciplinary Minor"),
        (consumer, "Consumer Behavior Interdisciplinary Minor"),
    ):
        ok, ev = validate_extracted_text(body, name)
        assert ok, (name, ev["reasons"])
        assert ev["cross_reference_stub"] is True


def test_stub_rule_does_not_admit_contaminated_or_empty_bodies():
    """The stub allowance must not become a hole in the gate."""
    contaminated = (
        "Skip to Navigation\n\nRow 1:  | University of Southern California\n"
        "See complete description in the USC Price School of Public Policy section.\n"
        + "filler "
        * 60
    )
    ok, _ = validate_extracted_text(contaminated, "Some Minor")
    assert not ok
    # a stub with no title heading of its own is still rejected
    ok2, _ = validate_extracted_text(
        "See complete description in the USC Price School section." + " x" * 200,
        "Some Minor",
    )
    assert not ok2
    # under the absolute floor, nothing passes
    ok3, _ = validate_extracted_text(
        "# Some Minor\n\nSee the USC Price School section.", "Some Minor"
    )
    assert not ok3


# ------------------------------------------- self-review findings (2026-07-31)
def test_title_heading_is_not_a_substring_match():
    """Short programme names must not match unrelated headings.

    Self-review finding: `_norm(stem) in _norm(line)` matched "Art" inside
    "## Departmental Requirements" (dep-ART-mental) and "## Chart of Accounts",
    so a body with no title heading of its own passed the single most reliable
    contamination check.
    """
    from usc_catalog_scraper.output_validation import title_heading_present

    assert not title_heading_present("## Departmental Requirements\n", "Art (BA)")
    assert not title_heading_present("## Chart of Accounts\n", "Art (BA)")
    assert not title_heading_present("### Smart Manufacturing\n", "Art (BA)")
    # genuine matches still work, including footnote markers and slash titles
    assert title_heading_present("# Art (BA)\n", "Art (BA)")
    assert title_heading_present("# Art History (BA)\n", "Art History (BA)")
    assert title_heading_present("# Philosophy (BA)*\n", "Philosophy (BA)*")
    assert title_heading_present("# Economics/Mathematics (BA)*\n", "Economics/Mathematics (BA)*")
    # and the end-to-end effect: no own title -> rejected
    body = "## Departmental Requirements\n\nART 101 Drawing Units: 4\n" + "filler. " * 60
    ok, ev = validate_extracted_text(body, "Art (BA)")
    assert not ok
    assert "no_program_title_heading_in_body" in ev["reasons"]


def test_ineligible_note_uses_identity_not_tag_equality():
    """bs4 Tag.__eq__ is a deep structural comparison.

    Self-review finding: the evidence note used `t not in eligible`, so two
    distinct but identically-marked-up candidates compared equal and the
    "outscored-but-ineligible" note could be wrongly suppressed. Identity is
    the correct test.
    """
    soup = BeautifulSoup(
        "<html><body>"
        "<div class='wrap'><p>identical filler paragraph for structure</p></div>"
        "<td class='block_content'><h1>Physics (BS)</h1>"
        "<p>PHYS 151 Units: 4 and more requirement prose to give this weight.</p>"
        "</td>"
        "<div class='wrap'><p>identical filler paragraph for structure</p></div>"
        "</body></html>",
        "lxml",
    )
    container, evidence = select_main_container(soup, _cfg(), require_content_region=True)
    assert "block_content" in evidence
    assert container.get("class") == ["block_content"]


def test_tier2_recovers_a_renamed_content_region_without_admitting_chrome():
    """Future-layout safety: unfamiliar selector must not lose the whole page.

    Self-review 2026-07-31: a clean region behind an unknown selector was never
    even a candidate, so the page was refused outright (total data loss). Tier 2
    derives structural candidates from the page's own <h1> and accepts only
    chrome-free ones; <body> can never qualify.
    """
    clean = (
        "<h1>Physics (BS)</h1><p>The programme requires a minimum of 128 units and a "
        "grade of C or better in all upper-division work applied toward the major.</p>"
        "<h2>Required Courses</h2><ul>"
        "<li>PHYS 151Lg Fundamentals of Physics I <em>Units: 4</em></li>"
        "<li>MATH 226g Calculus III <em>Units: 4</em></li></ul><h2>Total units: 128</h2>"
    )
    for html, want_tag in (
        (f"<html><body><div class='program-body'>{clean}</div></body></html>", "div"),
        (f"<html><body><td class='content_block'>{clean}</td></body></html>", "td"),
    ):
        soup = BeautifulSoup(html, "lxml")
        el, ev = select_main_container(soup, _cfg(), require_content_region=True)
        assert "chrome-free-fallback" in ev, ev
        assert el.name == want_tag, (el.name, ev)
        text = render_text(clean_content(el, _cfg()), _cfg())
        ok, evd = validate_extracted_text(text, "Physics (BS)")
        assert ok, evd["reasons"]
        for marker in CONTAMINATION_MARKERS:
            assert marker not in text


def test_tier2_never_admits_the_body_even_when_it_is_the_only_candidate():
    from usc_catalog_scraper.extraction import has_page_chrome

    soup = BeautifulSoup(
        "<html><body><a href='#n'>Skip to Navigation</a>"
        "<table><tr><td></td><td>University of Southern California</td></tr></table>"
        "<h1>Physics (BS)</h1><p>PHYS 151 Units: 4</p></body></html>",
        "lxml",
    )
    assert has_page_chrome(soup.body) is True
    with pytest.raises(ContentRegionNotFound):
        select_main_container(soup, _cfg(), require_content_region=True)
