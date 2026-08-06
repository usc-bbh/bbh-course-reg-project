"""Real Playwright browser-layer integration tests against a localhost server.

Serves the fixture site where the programs index is a JavaScript shell that
only renders content client-side — forcing the layered orchestrator to
escalate from direct HTTP to the browser and prove the rendered-DOM path,
mixed acquisition modes, challenge screenshots, and human-verification handoff.

Skipped automatically when Playwright Chromium is not installed.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest
from tests.conftest import PROGRAM_FIXTURES, load_fixture

from usc_catalog_scraper import config
from usc_catalog_scraper.acquisition import (
    AcquisitionOrchestrator,
    HumanVerificationRequired,
)
from usc_catalog_scraper.models import AcquisitionMode, PageKind
from usc_catalog_scraper.pipeline import run_pipeline
from usc_catalog_scraper.state import StateDB


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            return Path(pw.chromium.executable_path).exists()
    except Exception:
        return False


CHROMIUM_OK = _chromium_available()
pytestmark = pytest.mark.skipif(
    not CHROMIUM_OK, reason="Playwright Chromium is not installed in this environment"
)

# Stub X libraries built for the CI sandbox; harmless elsewhere.
if Path("/tmp/xlibs/libXdamage.so.1").exists():
    os.environ["LD_LIBRARY_PATH"] = ("/tmp/xlibs:" + os.environ.get("LD_LIBRARY_PATH", "")).rstrip(
        ":"
    )


def _body_of(html: str) -> str:
    start = html.find("<body>") + len("<body>")
    end = html.find("</body>")
    return html[start:end]


JS_SHELL_TEMPLATE = """<!DOCTYPE html>
<html><head><title>Programs, Minors and Certificates - University of Southern California</title>
<script>
window.addEventListener('DOMContentLoaded', function () {{
  setTimeout(function () {{
    document.getElementById('app').innerHTML = {payload};
  }}, 500);
}});
</script></head>
<body>
<noscript>Javascript is currently not supported, or is disabled by this browser.</noscript>
<div id="app"><div class="loading-spinner">Loading…</div></div>
</body></html>"""


class _FixtureSiteHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence
        pass

    def do_GET(self):
        parts = urlsplit(self.path)
        params = dict(parse_qsl(parts.query))
        path = parts.path
        if path.endswith("/misc/catalog_list.php"):
            body = load_fixture("catalogue_list.html")
        elif path.endswith("/index.php"):
            body = load_fixture("catalogue_home.html")
        elif path.endswith("/content.php") and params.get("navoid") == "9396":
            # JavaScript shell: content only exists after client-side render.
            # Absolute catalogue URLs are rewritten to this test host so the
            # fixture's absolute-link case stays testable offline.
            inner = _body_of(load_fixture("index_normal.html")).replace(
                "https://catalogue.usc.edu/", f"http://{self.headers['Host']}/"
            )
            body = JS_SHELL_TEMPLATE.format(payload=json.dumps(inner))
        elif path.endswith("/challenge.php"):
            body = load_fixture("challenge.html")
        elif path.endswith("/preview_program.php"):
            entry = PROGRAM_FIXTURES.get(params.get("poid", ""))
            if entry:
                body = load_fixture(entry[0])
                if entry[1]:
                    body = body.replace(*entry[1])
            else:
                body = "<html><head><title>Not Found</title></head><body>missing</body></html>"
        else:
            body = "<html><body>not found</body></html>"
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture(scope="module")
def fixture_site():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureSiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _cfg(tmp_path: Path, base: str) -> config.ScraperConfig:
    return config.ScraperConfig(
        workdir=tmp_path,
        start_url=f"{base}/content.php?catoid=22&navoid=9396",
        delay_min=0.0,
        delay_max=0.01,
        max_retries=2,
        allow_browser=True,
        chromium_sandbox=False,  # container has no user namespaces
        save_failure_screenshots=True,
        readiness_timeout_ms=15_000,
        stabilization_polls=2,
        stabilization_interval_ms=300,
    )


def test_browser_fallback_renders_js_shell_index(tmp_path, fixture_site):
    cfg = _cfg(tmp_path, fixture_site)
    db = StateDB(tmp_path / "state" / "s.sqlite3")
    orch = AcquisitionOrchestrator(
        cfg, db, state_dir=tmp_path / "state", screenshots_dir=tmp_path / "shots"
    )
    try:
        result = orch.acquire(cfg.start_url, PageKind.PROGRAMS_INDEX, label="index")
        assert result.mode is AcquisitionMode.BROWSER_RENDERED_DOM
        assert result.ok
        assert result.semantic_evidence["program_link_count"] >= 5
        # Raw pre-render HTML differs from the rendered DOM.
        assert "loading-spinner" in result.raw_html
        assert "Philosophy (BA)" in result.html
        modes = [
            r["acquisition_mode"]
            for r in db.conn.execute("SELECT acquisition_mode FROM fetch_log ORDER BY id")
        ]
        assert "invalid_content" in modes  # direct + alternate failed semantically
        assert modes[-1] == "browser_rendered_dom"
    finally:
        orch.close()
        db.close()


def test_full_pipeline_with_real_browser_mixed_modes(tmp_path, fixture_site):
    cfg = _cfg(tmp_path, fixture_site)
    outcome = run_pipeline(cfg, smoke=True)
    assert outcome.stopped_reason == ""
    assert outcome.included == 6
    assert outcome.succeeded == 6
    root = outcome.output_root
    assert root is not None
    files = sorted(p.name for p in (root / "programs").glob("*.txt"))
    assert len(files) == 6
    boundary = json.loads(
        (root / "audit_evidence" / "index_boundary.json").read_text(encoding="utf-8")
    )
    assert boundary["acquisition_mode"] == "browser_rendered_dom"
    assert boundary["links_in_section"] == 9
    db = StateDB(config.OutputLayout(root=root).db_path)
    program_modes = {
        str(r["acquisition_mode"]) for r in db.conn.execute("SELECT acquisition_mode FROM programs")
    }
    assert program_modes == {"direct_html"}  # program pages were server-rendered
    db.close()
    sample = (root / "programs" / files[0]).read_text(encoding="utf-8")
    assert "OFFICIAL CATALOGUE CONTENT" in sample


def test_challenge_page_screenshot_and_handoff(tmp_path, fixture_site):
    cfg = _cfg(tmp_path, fixture_site)
    db = StateDB(tmp_path / "state" / "s.sqlite3")
    shots = tmp_path / "shots"
    orch = AcquisitionOrchestrator(cfg, db, state_dir=tmp_path / "state", screenshots_dir=shots)
    try:
        with pytest.raises(HumanVerificationRequired) as exc:
            orch.acquire(f"{fixture_site}/challenge.php", PageKind.PROGRAMS_INDEX, label="chal")
        assert "--headed" in exc.value.instructions
        assert list(shots.glob("*.png")), "failure screenshot should be saved"
        row = db.conn.execute(
            "SELECT challenge_detected, acquisition_mode FROM fetch_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row["challenge_detected"] == 1
        assert row["acquisition_mode"] == "challenge_page"
    finally:
        orch.close()
        db.close()


def test_program_page_accordion_expansion_clicks(tmp_path, fixture_site):
    cfg = _cfg(tmp_path, fixture_site)
    db = StateDB(tmp_path / "state" / "s.sqlite3")
    orch = AcquisitionOrchestrator(
        cfg, db, state_dir=tmp_path / "state", screenshots_dir=tmp_path / "shots"
    )
    try:
        result = orch.browser.fetch(
            f"{fixture_site}/preview_program.php?catoid=22&poid=109", PageKind.PROGRAM_PAGE
        )
        assert result.mode is AcquisitionMode.BROWSER_RENDERED_DOM
        assert result.semantic_evidence.get("expand_clicks", 0) >= 1
        assert "DES 320 Interaction Design" in result.html
    finally:
        orch.close()
        db.close()
