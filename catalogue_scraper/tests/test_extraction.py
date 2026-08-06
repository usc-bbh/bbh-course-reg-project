"""Main-content selection, noise removal, metadata extraction."""

from bs4 import BeautifulSoup
from tests.conftest import load_fixture

from usc_catalog_scraper.extraction import (
    capture_breadcrumbs,
    clean_content,
    extract_metadata,
    select_main_container,
)
from usc_catalog_scraper.text_renderer import render_text


def _soup(name: str) -> BeautifulSoup:
    return BeautifulSoup(load_fixture(name), "lxml")


def test_main_content_scoring_picks_block_content(cfg):
    soup = _soup("program_simple.html")
    container, evidence = select_main_container(soup, cfg)
    assert container.name == "td"
    assert "block_content" in " ".join(container.get("class") or [])
    assert "score=" in evidence  # winning method recorded


def test_navigation_removed_but_requirements_kept(cfg):
    soup = _soup("program_simple.html")
    container, _ = select_main_container(soup, cfg)
    cleaned = clean_content(container, cfg)
    text = render_text(cleaned, cfg)
    assert "PHIL 340 Ancient Philosophy" in text
    assert "Add to Portfolio" not in text
    assert "Print-Friendly Page" not in text
    assert "Catalogue Home" not in text


def test_hidden_accordion_requirements_survive_cleaning(cfg):
    soup = _soup("program_accordion.html")
    container, _ = select_main_container(soup, cfg)
    cleaned = clean_content(container, cfg)
    text = render_text(cleaned, cfg)
    assert "DES 320 Interaction Design (4 units)" in text
    assert "DES 440 Senior Studio" in text
    assert "minimum grade of B-" in text


def test_metadata_extraction(cfg):
    soup = _soup("program_simple.html")
    container, _ = select_main_container(soup, cfg)
    meta = extract_metadata(
        soup,
        container,
        url="https://catalogue.usc.edu/preview_program.php?catoid=22&poid=101&returnto=9396",
        canonical_url="https://catalogue.usc.edu/preview_program.php?catoid=22&poid=101",
        catoid="22",
        poid="101",
        catalogue_year="2026-2027",
        cfg=cfg,
    )
    assert meta.program_name == "Philosophy (BA)"
    assert meta.credential == "BA"
    assert "Dornsife College of Letters" in meta.school
    assert meta.catalogue_identifier == "catoid=22"
    assert meta.program_identifier == "poid=101"


def test_breadcrumbs_captured(cfg):
    soup = _soup("program_simple.html")
    crumbs = capture_breadcrumbs(soup)
    assert "Programs, Minors and Certificates" in crumbs
