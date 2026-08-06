"""Shared test fixtures: fixture loading, mock HTTP transport, configs."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from usc_catalog_scraper import acquisition, config

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def cfg(tmp_path: Path) -> config.ScraperConfig:
    return config.ScraperConfig(
        workdir=tmp_path,
        delay_min=0.0,
        delay_max=0.01,
        max_retries=2,
        allow_browser=False,
        save_failure_screenshots=False,
        verbose=False,
    )


# poid -> (fixture file, optional (old, new) title replacement)
PROGRAM_FIXTURES: dict[str, tuple[str, tuple[str, str] | None]] = {
    "101": ("program_simple.html", None),
    "102": ("program_tables.html", None),
    "103": ("program_tracks.html", None),
    "104": ("program_simple.html", ("Philosophy (BA)", "Economics/Mathematics (BA)")),
    "106": ("program_combined.html", None),
    "107": ("program_minor.html", None),
    "109": ("program_accordion.html", None),
    "110": ("program_simple.html", ("Philosophy (BA)", "Music Performance (BM)")),
    "201": ("program_simple.html", ("Philosophy (BA)", "History (MA)")),
}

HTML_HEADERS = {"content-type": "text/html; charset=UTF-8"}


def build_handler(calls: list[str] | None = None, overrides: dict | None = None):
    """Standard fixture-site handler routing catalogue URLs to fixture files."""
    overrides = overrides or {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if calls is not None:
            calls.append(url)
        path = request.url.path
        params = dict(request.url.params)
        for key, responder in overrides.items():
            if key in url:
                return responder(request)
        if path.endswith("/misc/catalog_list.php"):
            return httpx.Response(
                200, text=load_fixture("catalogue_list.html"), headers=HTML_HEADERS
            )
        if path.endswith("/index.php"):
            return httpx.Response(
                200, text=load_fixture("catalogue_home.html"), headers=HTML_HEADERS
            )
        if path.endswith("/content.php") and params.get("navoid") == "9396":
            return httpx.Response(200, text=load_fixture("index_normal.html"), headers=HTML_HEADERS)
        if path.endswith("/preview_program.php"):
            entry = PROGRAM_FIXTURES.get(params.get("poid", ""))
            if entry:
                text = load_fixture(entry[0])
                if entry[1]:
                    text = text.replace(*entry[1])
                return httpx.Response(200, text=text, headers=HTML_HEADERS)
            return httpx.Response(
                404,
                text="<html><head><title>Not Found</title></head><body>missing</body></html>",
                headers=HTML_HEADERS,
            )
        return httpx.Response(404, text="not found", headers=HTML_HEADERS)

    return handler


def patch_http(monkeypatch, handler) -> None:
    """Route the application's httpx.Client through a MockTransport."""
    real_client = httpx.Client

    def client_factory(**kwargs):
        return real_client(
            transport=httpx.MockTransport(handler),
            headers=kwargs.get("headers"),
            follow_redirects=True,
        )

    monkeypatch.setattr(acquisition.httpx, "Client", client_factory)


@pytest.fixture
def mock_site(monkeypatch) -> list[str]:
    """Patch HTTP to the standard fixture site; returns the request log."""
    calls: list[str] = []
    patch_http(monkeypatch, build_handler(calls))
    return calls
