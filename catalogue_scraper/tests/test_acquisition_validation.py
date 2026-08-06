"""Acquisition + semantic validation tests (MockTransport; no live network)."""

import httpx
import pytest
from tests.conftest import HTML_HEADERS, build_handler, load_fixture, patch_http

from usc_catalog_scraper import acquisition, config
from usc_catalog_scraper.acquisition import (
    AcquisitionOrchestrator,
    HttpFetcher,
    Pacer,
    RobotsDisallowedError,
    alternate_urls,
    check_robots_allowed,
)
from usc_catalog_scraper.models import AcquisitionMode, FetchResult, PageKind
from usc_catalog_scraper.semantic_validation import validate_page
from usc_catalog_scraper.state import StateDB

INDEX_URL = "https://catalogue.usc.edu/content.php?catoid=22&navoid=9396"


# ---------------------------------------------------------- semantic validation
def test_status_200_shell_fails_validation(cfg):
    ok, evidence = validate_page(PageKind.PROGRAMS_INDEX, load_fixture("index_shell.html"), cfg)
    assert not ok
    assert evidence["program_link_count"] == 0


def test_normal_index_passes_validation(cfg):
    ok, evidence = validate_page(PageKind.PROGRAMS_INDEX, load_fixture("index_normal.html"), cfg)
    assert ok
    assert evidence["program_link_count"] >= 5
    assert evidence["catalogue_title_found"]


def test_program_page_passes_validation(cfg):
    ok, evidence = validate_page(PageKind.PROGRAM_PAGE, load_fixture("program_simple.html"), cfg)
    assert ok
    assert evidence["course_code_count"] > 0


def test_incomplete_program_page_fails_validation(cfg):
    ok, _ = validate_page(PageKind.PROGRAM_PAGE, load_fixture("program_incomplete.html"), cfg)
    assert not ok


def test_challenge_page_fails_validation(cfg):
    ok, evidence = validate_page(PageKind.PROGRAMS_INDEX, load_fixture("challenge.html"), cfg)
    assert not ok
    assert evidence["challenge_detected"]


def test_empty_body_fails_validation(cfg):
    ok, evidence = validate_page(PageKind.PROGRAMS_INDEX, "", cfg)
    assert not ok
    assert evidence.get("empty_body")


# ------------------------------------------------------------------ robots
def test_robots_disallowed_paths_refused():
    for path in ("portfolio.php", "ajax/preview.php", "search_advanced.php"):
        with pytest.raises(RobotsDisallowedError):
            check_robots_allowed(f"https://catalogue.usc.edu/{path}?x=1")
    check_robots_allowed(INDEX_URL)  # allowed path does not raise


# ------------------------------------------------------------- http fetcher
def _fetcher(cfg, tmp_path) -> HttpFetcher:
    return HttpFetcher(cfg, tmp_path / "state", Pacer(cfg))


def test_direct_html_mode_selected(cfg, tmp_path, monkeypatch):
    patch_http(monkeypatch, build_handler())
    f = _fetcher(cfg, tmp_path)
    result = f.fetch(INDEX_URL, PageKind.PROGRAMS_INDEX)
    assert result.mode is AcquisitionMode.DIRECT_HTML
    assert result.ok
    assert result.http_status == 200
    f.close()


def test_shell_yields_invalid_content(cfg, tmp_path, monkeypatch):
    def handler(request):
        return httpx.Response(200, text=load_fixture("index_shell.html"), headers=HTML_HEADERS)

    patch_http(monkeypatch, handler)
    f = _fetcher(cfg, tmp_path)
    result = f.fetch(INDEX_URL, PageKind.PROGRAMS_INDEX)
    assert result.mode is AcquisitionMode.INVALID_CONTENT
    assert not result.ok
    f.close()


def test_challenge_yields_challenge_mode(cfg, tmp_path, monkeypatch):
    def handler(request):
        return httpx.Response(200, text=load_fixture("challenge.html"), headers=HTML_HEADERS)

    patch_http(monkeypatch, handler)
    f = _fetcher(cfg, tmp_path)
    result = f.fetch(INDEX_URL, PageKind.PROGRAMS_INDEX)
    assert result.mode is AcquisitionMode.CHALLENGE_PAGE
    assert result.challenge_detected
    f.close()


def test_server_errors_retry_then_network_failure(cfg, tmp_path, monkeypatch):
    attempts: list[int] = []

    def handler(request):
        attempts.append(1)
        return httpx.Response(503, text="unavailable", headers={"Retry-After": "0"})

    patch_http(monkeypatch, handler)
    f = _fetcher(cfg, tmp_path)
    result = f.fetch(INDEX_URL, PageKind.PROGRAMS_INDEX)
    assert result.mode is AcquisitionMode.NETWORK_FAILURE
    assert len(attempts) == cfg.max_retries  # bounded retries
    f.close()


# ------------------------------------------------------------ orchestration
def _orchestrator(cfg, tmp_path) -> AcquisitionOrchestrator:
    db = StateDB(tmp_path / "state" / "test.sqlite3")
    return AcquisitionOrchestrator(
        cfg, db, state_dir=tmp_path / "state", screenshots_dir=tmp_path / "shots"
    )


def test_alternate_first_party_selected_when_primary_invalid(cfg, tmp_path, monkeypatch):
    def handler(request):
        if "print" in dict(request.url.params) or "print" in str(request.url.query):
            return httpx.Response(200, text=load_fixture("index_normal.html"), headers=HTML_HEADERS)
        return httpx.Response(200, text=load_fixture("index_shell.html"), headers=HTML_HEADERS)

    patch_http(monkeypatch, handler)
    orch = _orchestrator(cfg, tmp_path)
    result = orch.acquire(INDEX_URL, PageKind.PROGRAMS_INDEX, label="test")
    assert result.mode is AcquisitionMode.ALTERNATE_FIRST_PARTY_HTML
    assert result.ok
    rows = orch.db.conn.execute("SELECT method, result FROM fetch_log").fetchall()
    assert len(rows) >= 2  # both attempts logged
    orch.close()


class _FakeBrowser:
    def __init__(self, html: str):
        self.html = html
        self.screenshots_dir = None

    def fetch(self, url, kind, attempt_base=3, wait_for_human=False):
        r = FetchResult(url=url, page_kind=kind, method="playwright", attempt=attempt_base)
        r.html = self.html
        r.final_url = url
        r.http_status = 200
        r.semantic_ok = True
        r.mode = AcquisitionMode.BROWSER_RENDERED_DOM
        r.rendered_dom_sha256 = "f" * 64
        return r

    def cookies(self):
        return [{"name": "session", "value": "x", "domain": "catalogue.usc.edu", "path": "/"}]

    def save_storage_state(self, path):
        pass

    def browser_version(self):
        return "fake-chromium"

    def close(self):
        pass


def test_browser_fallback_selected_when_http_layers_fail(cfg, tmp_path, monkeypatch):
    def handler(request):
        return httpx.Response(200, text=load_fixture("index_shell.html"), headers=HTML_HEADERS)

    patch_http(monkeypatch, handler)
    cfg.allow_browser = True
    orch = _orchestrator(cfg, tmp_path)
    orch._browser = _FakeBrowser(load_fixture("index_normal.html"))
    result = orch.acquire(INDEX_URL, PageKind.PROGRAMS_INDEX, label="test")
    assert result.mode is AcquisitionMode.BROWSER_RENDERED_DOM
    assert result.ok
    modes = [
        r["acquisition_mode"]
        for r in orch.db.conn.execute("SELECT acquisition_mode FROM fetch_log")
    ]
    assert "invalid_content" in modes and "browser_rendered_dom" in modes
    orch.close()


def test_headless_challenge_raises_human_verification(cfg, tmp_path, monkeypatch):
    def handler(request):
        return httpx.Response(200, text=load_fixture("challenge.html"), headers=HTML_HEADERS)

    patch_http(monkeypatch, handler)
    cfg.allow_browser = True
    orch = _orchestrator(cfg, tmp_path)

    class _ChallengedBrowser(_FakeBrowser):
        def fetch(self, url, kind, attempt_base=3, wait_for_human=False):
            r = FetchResult(url=url, page_kind=kind, method="playwright", attempt=attempt_base)
            r.html = load_fixture("challenge.html")
            r.challenge_detected = True
            r.mode = AcquisitionMode.CHALLENGE_PAGE
            return r

    orch._browser = _ChallengedBrowser("")
    with pytest.raises(acquisition.HumanVerificationRequired) as exc:
        orch.acquire(INDEX_URL, PageKind.PROGRAMS_INDEX, label="test")
    assert "--headed" in exc.value.instructions
    orch.close()


def test_alternate_urls_builder():
    alts = alternate_urls(INDEX_URL, PageKind.PROGRAMS_INDEX)
    assert alts == [INDEX_URL + "&print"]
    assert alternate_urls("https://catalogue.usc.edu/x.php", PageKind.PROGRAM_PAGE) == [
        "https://catalogue.usc.edu/x.php?print"
    ]


def test_no_browser_config_returns_http_failure(cfg, tmp_path, monkeypatch):
    def handler(request):
        return httpx.Response(200, text=load_fixture("index_shell.html"), headers=HTML_HEADERS)

    patch_http(monkeypatch, handler)
    orch = _orchestrator(cfg, tmp_path)  # cfg.allow_browser is False
    result = orch.acquire(INDEX_URL, PageKind.PROGRAMS_INDEX, label="test")
    assert not result.ok
    assert result.mode is AcquisitionMode.INVALID_CONTENT
    orch.close()


def test_config_delay_range_ordering():
    c = config.ScraperConfig(delay_min=5.0, delay_max=2.0)
    lo, hi = c.http_delay_range()
    assert lo == 2.0 and hi == 5.0
