"""Regression tests for defects found by the adversarial review agents.

Each test reproduces a reviewed attack and asserts the repaired behavior.
Finding numbers reference the Phase-5 adversarial review reports.
"""

from bs4 import BeautifulSoup

from usc_catalog_scraper.classification import classify_title
from usc_catalog_scraper.discovery import _is_interface_link, discover_program_links
from usc_catalog_scraper.extraction import select_main_container
from usc_catalog_scraper.models import Classification
from usc_catalog_scraper.text_renderer import render_text

BASE = "https://catalogue.usc.edu/content.php?catoid=22&navoid=9396"


def _poids(links):
    return [link.poid for link in links]


def _page(body: str) -> str:
    return f"<html><head><title>Programs - USC Catalogue 2026-2027</title></head><body>{body}</body></html>"


# ------------------------------------------------- finding 9b: <nav> container
def test_nav_element_cannot_win_container_selection(cfg):
    html = _page(
        """
        <nav id="content">
          <h2>Undergraduate Programs</h2>
          <a href="preview_program.php?catoid=22&poid=320">NavLink (BA)</a>
          <a href="preview_program.php?catoid=22&poid=321">NavLink2 (BS)</a>
        </nav>
        <td class="block_content">
          <h1>Programs</h1>
          <p>Real content region with the actual listing for the catalogue year.</p>
          <h2>Undergraduate Programs</h2>
          <ul><li><a href="preview_program.php?catoid=22&poid=330">Real (BA)</a></li></ul>
          <h2>Graduate Programs</h2>
        </td>
        """
    )
    soup = BeautifulSoup(html, "lxml")
    container, _evidence = select_main_container(soup, cfg)
    assert container.name != "nav"
    links, _, _, _ = discover_program_links(html, BASE, cfg, strict=True)
    assert _poids(links) == ["330"]


# --------------------------------- finding 9a: sidebar heading hijacks boundary
def test_sidebar_nav_copy_of_heading_does_not_hijack_boundary(cfg):
    html = _page(
        """
        <main>
          <nav class="sidebar">
            <h2>Undergraduate Programs</h2>
            <a href="preview_program.php?catoid=22&poid=300">QuickLink One (BA)</a>
            <a href="preview_program.php?catoid=22&poid=301">QuickLink Two (BS)</a>
            <h2>Graduate Programs</h2>
          </nav>
          <td class="block_content">
            <p>The full official listing of degree programs follows below.</p>
            <h2>Undergraduate Programs</h2>
            <ul>
              <li><a href="preview_program.php?catoid=22&poid=310">Real One (BA)</a></li>
              <li><a href="preview_program.php?catoid=22&poid=311">Real Two (BS)</a></li>
              <li><a href="preview_program.php?catoid=22&poid=312">Real Three (BFA)</a></li>
            </ul>
            <h2>Graduate Programs</h2>
            <a href="preview_program.php?catoid=22&poid=390">Grad (MA)</a>
          </td>
        </main>
        """
    )
    links, _evidence, _, _ = discover_program_links(html, BASE, cfg, strict=True)
    assert _poids(links) == ["310", "311", "312"]


# ------------------------- finding V1/V2: vendor badges as false terminators
def test_vendor_credential_badge_does_not_terminate_native_section(cfg):
    html = _page(
        """
        <td class="block_content">
          <h1>Programs</h1>
          <h2>Undergraduate Programs</h2>
          <a href="preview_program.php?catoid=22&poid=70">First (BA)</a>
          <span class="degree-type">Bachelor of Science</span>
          <a href="preview_program.php?catoid=22&poid=71">Second (BS)</a>
          <p class="filter_heading">Show: All | A | B | C</p>
          <a href="preview_program.php?catoid=22&poid=72">Third (BFA)</a>
          <h2>Graduate Programs</h2>
          <a href="preview_program.php?catoid=22&poid=79">Grad (MS)</a>
        </td>
        """
    )
    links, evidence, _, _ = discover_program_links(html, BASE, cfg, strict=True)
    assert _poids(links) == ["70", "71", "72"]
    assert evidence.terminating_heading.text == "Graduate Programs"


def test_vendor_heading_still_terminates_vendor_started_section(cfg):
    # No regression: pages whose headings are ALL vendor-class still bound.
    from tests.conftest import load_fixture

    links, evidence, _, _ = discover_program_links(
        load_fixture("index_vendor_headings.html"), BASE, cfg, strict=True
    )
    assert _poids(links) == ["101", "102"]
    assert evidence.terminating_heading.text == "Graduate Programs"


# ------------------------------------- finding F1: interface-link substrings
def test_program_links_with_fragments_or_returnto_survive(cfg):
    assert not _is_interface_link(
        "preview_program.php?catoid=22&poid=90&returnto=9396#requirements"
    )
    assert not _is_interface_link("preview_program.php?catoid=22&poid=91&returnto=portfolio.php")
    assert _is_interface_link("#top")
    assert _is_interface_link("javascript:void(0)")
    assert _is_interface_link("portfolio.php?catoid=22")
    assert _is_interface_link("/portfolio_nopop.php?x=1")
    html = _page(
        """
        <td class="block_content">
          <h2>Undergraduate Programs</h2>
          <a href="preview_program.php?catoid=22&poid=90&returnto=9396#requirements">Frag (BA)</a>
          <a href="preview_program.php?catoid=22&poid=91">Plain (BS)</a>
          <h2>Graduate Programs</h2>
        </td>
        """
    )
    links, _, _, _ = discover_program_links(html, BASE, cfg, strict=True)
    assert _poids(links) == ["90", "91"]


# --------------------------- finding 2b: anchor wrapping terminating heading
def test_anchor_wrapping_terminator_is_not_collected(cfg):
    html = _page(
        """
        <td class="block_content">
          <h2>Undergraduate Programs</h2>
          <p><a href="preview_program.php?catoid=22&poid=20">Good (BA)</a></p>
          <a href="preview_program.php?catoid=22&poid=21"><h2>Graduate Programs</h2></a>
          <a href="preview_program.php?catoid=22&poid=22">Grad Link (MA)</a>
        </td>
        """
    )
    links, evidence, _, _ = discover_program_links(html, BASE, cfg, strict=True)
    assert _poids(links) == ["20"]
    assert evidence.terminating_heading.text == "Graduate Programs"


# ----------------------------------- classification findings (minor/composite)
def test_asia_minor_studies_is_not_a_minor():
    result = classify_title("Asia Minor Studies (BA)")
    assert result.classification is Classification.INCLUDED, result.reason


def test_trailing_minor_still_excluded():
    assert classify_title("Spanish Minor").classification is Classification.EXCLUDED_MINOR
    assert classify_title("Minor in Data Science").classification is Classification.EXCLUDED_MINOR


def test_composite_bs_ms_title_excluded_as_combined():
    result = classify_title("Chemistry (BS) / Chemistry (MS)")
    assert result.classification is Classification.EXCLUDED_COMBINED, result.reason
    result = classify_title("Business of Cinematic Arts (BS) and Communication (MA)")
    assert result.classification is Classification.EXCLUDED_COMBINED, result.reason


def test_unknown_credential_token_never_included():
    result = classify_title("Physician Assistant Practice (MPAP)")
    assert result.classification is not Classification.INCLUDED
    assert result.classification is Classification.MANUAL_REVIEW


# --------------------------------------- renderer findings 12/13: table cells
def _render(html: str) -> str:
    soup = BeautifulSoup(f"<div id='root'>{html}</div>", "lxml")
    return render_text(soup.find(id="root"))


def test_lists_inside_table_cells_preserved():
    out = _render(
        "<table><tr><th>Requirement</th><th>Courses</th></tr>"
        "<tr><td>Pick one</td><td><ul>"
        "<li>HIST 200 History A (4 units)</li>"
        "<li>HIST 201 History B (4 units)</li>"
        "</ul></td></tr></table>"
    )
    assert "HIST 200 History A (4 units)" in out
    assert "HIST 201 History B (4 units)" in out
    assert "HIST 200 History A (4 units) ; HIST 201 History B (4 units)" in out


def test_ordered_list_in_cell_keeps_numbering():
    # Two columns so this is a real data table; single-cell tables are layout
    # and render their content as normal flow (see next test).
    out = _render(
        "<table><tr><td>Requirement</td>"
        "<td><ol><li>BISC 120 (4 units)</li><li>BISC 220 (4 units)</li></ol></td></tr></table>"
    )
    assert "1. BISC 120 (4 units) ; 2. BISC 220 (4 units)" in out


def test_single_column_layout_table_unwraps_to_block_flow():
    # The live 2026-2027 catalogue nests all content in single-column
    # table_default scaffolding; flattening it into one table row destroyed
    # page structure (live finding 2026-07-13).
    out = _render(
        "<table><tr><td><h2>Admission</h2><p>Apply early.</p>"
        "<ol><li>BISC 120 (4 units)</li><li>BISC 220 (4 units)</li></ol></td></tr></table>"
    )
    assert "TABLE:" not in out
    assert "## Admission" in out
    assert "Apply early." in out
    assert "1. BISC 120 (4 units)" in out
    assert "2. BISC 220 (4 units)" in out


def test_mixed_cell_text_and_list_all_preserved():
    out = _render(
        "<table><tr><td>Intro text <ul><li>EE 109 Digital Systems (4 units)</li></ul> trailing text</td></tr></table>"
    )
    assert "Intro text" in out
    assert "EE 109 Digital Systems (4 units)" in out
    assert "trailing text" in out


def test_nested_table_does_not_collide_with_column_delimiter():
    out = _render(
        "<table><tr><td>Cell text<table><tr><td>inner A</td><td>inner B</td></tr></table></td>"
        "<td>plain</td></tr></table>"
    )
    row = next(ln for ln in out.split("\n") if ln.startswith("Row 1:"))
    # Exactly one outer column separator: two outer cells.
    assert row.count(" | ") == 1
    assert "inner A / inner B" in row


def test_dl_inside_cell_preserved():
    out = _render(
        "<table><tr><td><dl><dt>Core</dt><dd>CHEM 105 (4 units)</dd></dl></td></tr></table>"
    )
    assert "CHEM 105 (4 units)" in out


def test_sup_footnotes_bracketed_and_connected():
    out = _render(
        "<p>PHIL 430 Ethics (4 units) <sup>1</sup></p><p><sup>1</sup> Requires junior standing.</p>"
    )
    assert "PHIL 430 Ethics (4 units) [1]" in out
    assert "[1] Requires junior standing." in out
