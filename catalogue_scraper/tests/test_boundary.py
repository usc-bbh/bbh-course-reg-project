"""Boundary detection tests: normalization, levels, termination, containment."""

import pytest
from bs4 import BeautifulSoup
from tests.conftest import load_fixture

from usc_catalog_scraper import config
from usc_catalog_scraper.boundary import (
    BoundaryNotProvableError,
    find_undergraduate_section,
    iter_heading_candidates,
    normalize_heading_text,
)
from usc_catalog_scraper.discovery import discover_program_links


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Undergraduate Programs", "undergraduate programs"),
        ("  Undergraduate Programs:  ", "undergraduate programs"),
        ("UNDERGRADUATE   PROGRAMS", "undergraduate programs"),
        ("• Undergraduate Programs •", "undergraduate programs"),
        ("Undergraduate&nbsp;Programs", "undergraduate programs"),
        ("Bachelor’s Degree", "bachelor's degree"),
        ("— Minors —", "minors"),
    ],
)
def test_heading_normalization(raw, expected):
    assert normalize_heading_text(raw) == expected


def _section(fixture: str, cfg=None, heading="Undergraduate Programs"):
    cfg = cfg or config.ScraperConfig(boundary_heading=heading)
    soup = BeautifulSoup(load_fixture(fixture), "lxml")
    container = (
        soup.find("td", class_="block_content")
        or soup.find("main")
        or soup.find(id="content")
        or soup.body
    )
    return find_undergraduate_section(container, cfg, strict=True)


def test_first_heading_detection_native():
    section = _section("index_normal.html")
    assert section.heading.info.text.replace("\xa0", " ") == "Undergraduate Programs"
    assert section.heading.info.level == 2
    assert section.heading.info.source == "native-h"


def test_same_level_termination():
    section = _section("index_normal.html")
    assert section.terminating is not None
    assert section.terminating.info.text == "Graduate Programs"
    assert section.terminating.info.level == 2
    assert section.evidence.terminated_by == "heading"


def test_lower_level_nested_headings_do_not_terminate():
    section = _section("index_normal.html")
    nested = [h["text"] for h in section.evidence.all_headings_seen if h["level"] == 3]
    assert "Bachelor's Degrees" in nested
    poids = {
        a["href"].split("poid=")[1].split("&")[0]
        for a in section.anchors
        if "poid=" in a.get("href", "")
    }
    # Links under nested h3s are still inside the section.
    assert {"101", "102", "109", "110"} <= poids


def test_no_links_before_heading_collected():
    section = _section("index_normal.html")
    poids = {
        a["href"].split("poid=")[1].split("&")[0]
        for a in section.anchors
        if "poid=" in a.get("href", "")
    }
    assert "999" not in poids  # featured link appears before the section heading


def test_no_links_after_terminating_heading():
    section = _section("index_normal.html")
    poids = {
        a["href"].split("poid=")[1].split("&")[0]
        for a in section.anchors
        if "poid=" in a.get("href", "")
    }
    assert poids.isdisjoint({"201", "202", "203", "301", "401"})


def test_higher_level_heading_terminates():
    section = _section("index_higher_level_term.html")
    assert section.heading.info.level == 3
    assert section.terminating.info.level == 2
    assert section.terminating.info.text == "Graduate and Professional Education"
    poids = {
        a["href"].split("poid=")[1].split("&")[0]
        for a in section.anchors
        if "poid=" in a.get("href", "")
    }
    assert poids == {"101", "102", "109"}


def test_role_based_headings():
    section = _section("index_role_headings.html")
    assert section.heading.info.source == "role-heading"
    assert section.heading.info.level == 2
    assert section.terminating.info.text == "Graduate Programs"
    poids = {
        a["href"].split("poid=")[1].split("&")[0]
        for a in section.anchors
        if "poid=" in a.get("href", "")
    }
    assert poids == {"101", "102", "109", "110"}  # nested aria-level=3 does not terminate


def test_vendor_class_headings():
    section = _section("index_vendor_headings.html")
    assert section.heading.info.source == "vendor:acalog-filter-heading"
    poids = {
        a["href"].split("poid=")[1].split("&")[0]
        for a in section.anchors
        if "poid=" in a.get("href", "")
    }
    assert poids == {"101", "102"}


def test_strong_label_structural_fallback():
    section = _section("index_strong_labels.html")
    assert section.heading.info.source == "strong-label"
    poids = {
        a["href"].split("poid=")[1].split("&")[0]
        for a in section.anchors
        if "poid=" in a.get("href", "")
    }
    assert poids == {"101", "102"}
    assert section.terminating.info.text == "Graduate Programs"


def test_missing_heading_raises_with_headings_seen():
    with pytest.raises(BoundaryNotProvableError) as exc:
        _section("index_shell.html")
    assert isinstance(exc.value.headings_seen, list)


def test_heading_candidates_report_effective_levels():
    soup = BeautifulSoup(load_fixture("index_role_headings.html"), "lxml")
    cands = iter_heading_candidates(soup.find("main"), config.ScraperConfig())
    levels = {c.info.text: c.info.level for c in cands}
    assert levels["Undergraduate Programs"] == 2
    assert levels["Nested note"] == 3


def test_discover_full_evidence(cfg):
    links, evidence, duplicates, _ = discover_program_links(
        load_fixture("index_normal.html"),
        "https://catalogue.usc.edu/content.php?catoid=22&navoid=9396",
        cfg,
        strict=True,
    )
    assert evidence.heading is not None
    assert evidence.terminating_heading.text == "Graduate Programs"
    assert evidence.links_in_section == len(links) == 9
    assert duplicates == 1
    assert links[0].title.startswith("Philosophy")
    assert evidence.first_included_title.startswith("Philosophy")
    assert evidence.last_included_title.startswith("Music Performance")
