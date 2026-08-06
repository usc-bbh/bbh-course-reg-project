"""URL canonicalization, program-link identification, deduplication."""

from bs4 import BeautifulSoup

from usc_catalog_scraper.discovery import (
    canonicalize_url,
    collect_links_from_anchors,
    is_program_link,
)

BASE = "https://catalogue.usc.edu/content.php?catoid=22&navoid=9396"


def test_relative_link_resolution(cfg):
    absolute, _canonical, params = canonicalize_url(
        BASE, "preview_program.php?catoid=22&poid=102&returnto=9396", cfg
    )
    assert absolute.startswith("https://catalogue.usc.edu/preview_program.php")
    assert params["poid"] == "102"


def test_canonicalization_strips_tracking_and_returnto(cfg):
    _, canonical, _ = canonicalize_url(
        BASE,
        "https://CATALOGUE.usc.edu/preview_program.php?returnto=9396&poid=103&catoid=22&utm_source=carousel#requirements",
        cfg,
    )
    assert canonical == "https://catalogue.usc.edu/preview_program.php?catoid=22&poid=103"


def test_canonicalization_sorts_params_deterministically(cfg):
    _, c1, _ = canonicalize_url(BASE, "preview_program.php?poid=5&catoid=22", cfg)
    _, c2, _ = canonicalize_url(BASE, "preview_program.php?catoid=22&poid=5", cfg)
    assert c1 == c2


def test_is_program_link_requires_identifiers(cfg):
    assert is_program_link("https://catalogue.usc.edu/preview_program.php?catoid=22&poid=1", cfg)
    assert not is_program_link("https://catalogue.usc.edu/preview_program.php?catoid=22", cfg)
    assert not is_program_link("https://catalogue.usc.edu/content.php?catoid=22&navoid=9396", cfg)
    assert not is_program_link(
        "https://catalogue.usc.edu/preview_course_nopop.php?catoid=22&coid=5", cfg
    )


def _anchors(html: str):
    return BeautifulSoup(html, "lxml").find_all("a")


def test_duplicates_removed_by_stable_identifier(cfg):
    html = """
    <a href="preview_program.php?catoid=22&poid=101&returnto=9396">Philosophy (BA)</a>
    <a href="https://catalogue.usc.edu/preview_program.php?catoid=22&poid=101">Philosophy (BA) again</a>
    <a href="preview_program.php?catoid=22&poid=102">Accounting (BS)</a>
    """
    links, duplicates = collect_links_from_anchors(
        _anchors(html), BASE, "Undergraduate Programs", cfg
    )
    assert [lk.poid for lk in links] == ["101", "102"]
    assert duplicates == 1


def test_similar_titles_different_poids_not_merged(cfg):
    html = """
    <a href="preview_program.php?catoid=22&poid=501">Communication (BA)</a>
    <a href="preview_program.php?catoid=22&poid=502">Communication (BA)</a>
    """
    links, duplicates = collect_links_from_anchors(
        _anchors(html), BASE, "Undergraduate Programs", cfg
    )
    assert len(links) == 2 and duplicates == 0


def test_interface_and_non_program_links_skipped(cfg):
    html = """
    <a href="portfolio.php?catoid=22">My Portfolio</a>
    <a href="#top">Back to Top</a>
    <a href="javascript:void(0)">Print</a>
    <a href="mailto:x@usc.edu">Email</a>
    <a href="content.php?catoid=22&navoid=9385">Viterbi School of Engineering</a>
    <a href="preview_course_nopop.php?catoid=22&coid=55501">CSCI 103</a>
    <a href="preview_program.php?catoid=22&poid=109&returnto=9396">Design (BFA)</a>
    """
    links, _ = collect_links_from_anchors(_anchors(html), BASE, "Undergraduate Programs", cfg)
    assert [lk.poid for lk in links] == ["109"]


def test_discovered_link_records_required_fields(cfg):
    html = (
        '<a href="preview_program.php?catoid=22&poid=110&returnto=9396">Music Performance (BM)</a>'
    )
    links, _ = collect_links_from_anchors(_anchors(html), BASE, "Undergraduate Programs", cfg)
    link = links[0]
    assert link.sequence == 1
    assert link.title == "Music Performance (BM)"
    assert link.catoid == "22" and link.poid == "110" and link.returnto == "9396"
    assert link.section_heading == "Undergraduate Programs"
    assert link.canonical_url.endswith("catoid=22&poid=110")
    assert link.dom_path  # concise selector recorded
