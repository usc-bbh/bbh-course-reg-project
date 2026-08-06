"""Latest-catalogue resolution tests."""

from tests.conftest import load_fixture

from usc_catalog_scraper import config
from usc_catalog_scraper.catalogue_resolver import (
    find_programs_navoid,
    parse_catalog_list,
    resolve_latest,
)
from usc_catalog_scraper.models import AcquisitionMode, FetchResult, PageKind


def test_parse_catalog_list_marks_archived():
    entries = parse_catalog_list(
        load_fixture("catalogue_list.html"), "https://catalogue.usc.edu/misc/catalog_list.php"
    )
    by_catoid = {e.catoid: e for e in entries}
    assert by_catoid["22"].year == "2026-2027" and not by_catoid["22"].archived
    assert by_catoid["21"].archived and by_catoid["21"].year == "2025-2026"
    assert by_catoid["18"].year == "2023-2024"  # catoid not contiguous with year


def test_find_programs_navoid_from_navigation():
    navoid = find_programs_navoid(
        load_fixture("catalogue_home.html"), "https://catalogue.usc.edu/index.php?catoid=22", "22"
    )
    assert navoid == "9396"


class _FakeOrch:
    """Duck-typed orchestrator serving fixtures for resolver tests."""

    def __init__(self, fail_list=False):
        self.fail_list = fail_list

    def acquire(self, url: str, kind: PageKind, label: str = "") -> FetchResult:
        r = FetchResult(url=url, page_kind=kind, method="httpx", final_url=url)
        if "catalog_list" in url:
            if self.fail_list:
                r.mode = AcquisitionMode.NETWORK_FAILURE
                r.error = "simulated failure"
                return r
            r.html = load_fixture("catalogue_list.html")
        elif "index.php" in url:
            r.html = load_fixture("catalogue_home.html")
        else:
            r.html = load_fixture("index_normal.html")
        r.mode = AcquisitionMode.DIRECT_HTML
        r.semantic_ok = True
        r.http_status = 200
        return r


def test_resolver_confirms_supplied_url_when_newest():
    cfg = config.ScraperConfig()
    result = resolve_latest(_FakeOrch(), cfg)
    assert result.verified
    assert result.catalogue.catoid == "22"
    assert result.catalogue.year == "2026-2027"
    assert result.resolved_url == "https://catalogue.usc.edu/content.php?catoid=22&navoid=9396"
    assert any("confirmed" in n for n in result.notes)


def test_resolver_upgrades_older_supplied_url():
    cfg = config.ScraperConfig(
        start_url="https://catalogue.usc.edu/content.php?catoid=21&navoid=8873"
    )
    result = resolve_latest(_FakeOrch(), cfg)
    assert result.verified
    assert result.catalogue.catoid == "22"  # newer current catalogue chosen
    assert "catoid=22" in result.resolved_url
    assert any("resolved newer/current catalogue" in n for n in result.notes)


def test_resolver_falls_back_when_list_unavailable():
    cfg = config.ScraperConfig()
    result = resolve_latest(_FakeOrch(fail_list=True), cfg)
    assert not result.verified
    assert result.resolved_url == cfg.start_url
    assert any("NOT verified" in n for n in result.notes)


def test_no_latest_resolution_forces_supplied():
    cfg = config.ScraperConfig(latest_resolution=False)
    result = resolve_latest(_FakeOrch(), cfg)
    assert not result.verified
    assert result.method == "supplied-url-forced"
    assert result.resolved_url == cfg.start_url
