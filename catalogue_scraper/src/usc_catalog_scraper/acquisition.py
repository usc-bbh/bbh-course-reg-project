"""Layered page acquisition.

Layer 1: direct HTTP (httpx) with pacing, retries, cookies, semantic validation.
Layer 2: first-party alternate representations (print variants) exposed by the site.
Layer 3: Playwright Chromium with a persistent profile, semantic readiness,
         accordion expansion, and DOM stabilization.
Layer 4: human verification handoff (headed browser, never automated bypass).

Every attempt is logged. HTTP 200 alone is never success; validation is semantic.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from usc_catalog_scraper import config
from usc_catalog_scraper.challenge_detection import detect_challenge
from usc_catalog_scraper.logging_config import get_logger
from usc_catalog_scraper.models import AcquisitionMode, FetchResult, PageKind, utcnow_iso
from usc_catalog_scraper.semantic_validation import validate_page
from usc_catalog_scraper.state import StateDB, sha256_text

log = get_logger("acquisition")


class RobotsDisallowedError(RuntimeError):
    pass


class HumanVerificationRequired(RuntimeError):
    def __init__(self, url: str, instructions: str):
        super().__init__(instructions)
        self.url = url
        self.instructions = instructions


class _RetryableStatus(RuntimeError):
    def __init__(self, status: int):
        super().__init__(f"retryable HTTP status {status}")
        self.status = status


def check_robots_allowed(url: str) -> None:
    path = urlsplit(url).path or "/"
    for disallowed in config.ROBOTS_DISALLOWED_PATHS:
        if path.startswith(disallowed) or (disallowed.endswith("/") and disallowed in path):
            raise RobotsDisallowedError(
                f"Refusing to fetch {url}: path {disallowed!r} is disallowed by robots.txt"
            )


def _title_of(html: str) -> str:
    import re

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


class Pacer:
    """Conservative randomized pacing shared by all layers."""

    def __init__(self, cfg: config.ScraperConfig):
        self.cfg = cfg
        self._last: float | None = None

    def wait(self) -> None:
        lo, hi = self.cfg.http_delay_range()
        if self._last is None:
            self._last = time.monotonic()
            return
        target_gap = random.uniform(lo, hi)
        elapsed = time.monotonic() - self._last
        if elapsed < target_gap:
            time.sleep(target_gap - elapsed)
        self._last = time.monotonic()


class HttpFetcher:
    """Layer 1: persistent httpx client."""

    def __init__(self, cfg: config.ScraperConfig, state_dir: Path, pacer: Pacer):
        self.cfg = cfg
        self.state_dir = state_dir
        self.pacer = pacer
        self.cookie_path = state_dir / "http_cookies.json"
        self.client = httpx.Client(
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=httpx.Timeout(
                connect=cfg.connect_timeout,
                read=cfg.read_timeout,
                write=cfg.write_timeout,
                pool=cfg.pool_timeout,
            ),
            limits=httpx.Limits(
                max_connections=cfg.max_connections,
                max_keepalive_connections=cfg.max_connections,
            ),
            follow_redirects=True,
            trust_env=True,
        )
        self._load_cookies()

    def close(self) -> None:
        self._save_cookies()
        self.client.close()

    # -------------------------------------------------------------- cookies
    def _load_cookies(self) -> None:
        if not self.cookie_path.exists():
            return
        try:
            data = json.loads(self.cookie_path.read_text(encoding="utf-8"))
            for c in data:
                self.client.cookies.set(
                    c["name"], c["value"], domain=c.get("domain", ""), path=c.get("path", "/")
                )
        except Exception as e:
            log.debug("cookie load failed: %s", e)

    def _save_cookies(self) -> None:
        try:
            jar = []
            for cookie in self.client.cookies.jar:
                jar.append(
                    {
                        "name": cookie.name,
                        "value": cookie.value,
                        "domain": cookie.domain,
                        "path": cookie.path,
                    }
                )
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.cookie_path.write_text(json.dumps(jar, indent=1), encoding="utf-8")
        except Exception as e:
            log.debug("cookie save failed: %s", e)

    def adopt_browser_cookies(self, cookies: list[dict]) -> None:
        for c in cookies:
            with contextlib.suppress(Exception):
                self.client.cookies.set(
                    c.get("name", ""),
                    c.get("value", ""),
                    domain=c.get("domain", ""),
                    path=c.get("path", "/"),
                )
        self._save_cookies()

    # ---------------------------------------------------------------- fetch
    def fetch(self, url: str, kind: PageKind, attempt_base: int = 1) -> FetchResult:
        check_robots_allowed(url)
        self.pacer.wait()
        start = time.monotonic()
        result = FetchResult(url=url, page_kind=kind, method="httpx", attempt=attempt_base)

        @retry(
            retry=retry_if_exception_type((httpx.TransportError, _RetryableStatus)),
            wait=wait_random_exponential(multiplier=1.6, max=45),
            stop=stop_after_attempt(max(1, self.cfg.max_retries)),
            reraise=True,
        )
        def _do() -> httpx.Response:
            r = self.client.get(url)
            if r.status_code in (429, 500, 502, 503, 504):
                retry_after = r.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    time.sleep(min(int(retry_after), 90))
                raise _RetryableStatus(r.status_code)
            return r

        try:
            resp = _do()
        except Exception as e:
            result.mode = AcquisitionMode.NETWORK_FAILURE
            result.error = f"{type(e).__name__}: {e}"
            result.elapsed_seconds = time.monotonic() - start
            return result

        result.elapsed_seconds = time.monotonic() - start
        result.final_url = str(resp.url)
        result.http_status = resp.status_code
        result.content_type = resp.headers.get("content-type", "")
        result.html = resp.text
        result.raw_html = resp.text
        result.raw_html_sha256 = sha256_text(resp.text)
        result.page_title = _title_of(resp.text)
        challenged, challenge_evidence = detect_challenge(resp.text, result.page_title)
        waf_action = resp.headers.get("x-amzn-waf-action", "")
        if waf_action:
            challenged = True
            challenge_evidence = [f"x-amzn-waf-action header: {waf_action!r}", *challenge_evidence]
        result.challenge_detected = challenged
        result.challenge_evidence = challenge_evidence
        ok, evidence = validate_page(kind, resp.text, self.cfg)
        result.semantic_ok = ok
        result.semantic_evidence = evidence
        if challenged:
            result.mode = AcquisitionMode.CHALLENGE_PAGE
        elif ok and resp.status_code == 200:
            result.mode = AcquisitionMode.DIRECT_HTML
        else:
            result.mode = AcquisitionMode.INVALID_CONTENT
        return result


def alternate_urls(url: str, kind: PageKind) -> list[str]:
    """First-party alternate representations exposed by the catalogue itself.

    The site advertises print-friendly variants via '&print' (observed on
    index.php Print-Friendly links). Alternates are validated semantically
    exactly like primaries.
    """
    alternates: list[str] = []
    parts = urlsplit(url)
    if "print" not in parts.query:
        joiner = "&" if parts.query else "?"
        alternates.append(f"{url}{joiner}print")
    return alternates


class BrowserFetcher:
    """Layer 3: Playwright Chromium, persistent profile, semantic readiness."""

    def __init__(
        self,
        cfg: config.ScraperConfig,
        profile_dir: Path,
        screenshots_dir: Path,
        pacer: Pacer,
        headed: bool,
    ):
        self.cfg = cfg
        self.profile_dir = profile_dir
        self.screenshots_dir = screenshots_dir
        self.pacer = pacer
        self.headed = headed
        self._pw: Any = None
        self._context: Any = None
        self._page: Any = None

    # ---------------------------------------------------------------- setup
    def _ensure_started(self) -> None:
        if self._context is not None:
            return
        from playwright.sync_api import sync_playwright

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        launch_kwargs: dict = {
            "headless": not self.headed,
            "viewport": {"width": 1440, "height": 1000},
            "accept_downloads": False,
            "chromium_sandbox": self.cfg.chromium_sandbox,
        }
        if self.cfg.browser_extra_args:
            launch_kwargs["args"] = list(self.cfg.browser_extra_args)
        if not self.headed:
            launch_kwargs["user_agent"] = config.USER_AGENT
        self._context = self._pw.chromium.launch_persistent_context(
            str(self.profile_dir), **launch_kwargs
        )
        self._context.set_default_navigation_timeout(self.cfg.nav_timeout_ms)
        self._context.set_default_timeout(self.cfg.nav_timeout_ms)
        pages = self._context.pages
        self._page = pages[0] if pages else self._context.new_page()

    def browser_version(self) -> str:
        try:
            self._ensure_started()
            return self._context.browser.version if self._context.browser else "persistent-context"
        except Exception as e:
            return f"unavailable: {e}"

    def cookies(self) -> list[dict]:
        if self._context is None:
            return []
        with contextlib.suppress(Exception):
            return self._context.cookies()
        return []

    def save_storage_state(self, path: Path) -> None:
        if self._context is None:
            return
        with contextlib.suppress(Exception):
            path.parent.mkdir(parents=True, exist_ok=True)
            self._context.storage_state(path=str(path))

    def close(self) -> None:
        for closer in (
            lambda: self._context.close() if self._context else None,
            lambda: self._pw.stop() if self._pw else None,
        ):
            with contextlib.suppress(Exception):
                closer()
        self._context = None
        self._pw = None
        self._page = None

    # ------------------------------------------------------------ readiness
    def _semantic_marker_present(self, kind: PageKind) -> bool:
        js = {
            PageKind.PROGRAMS_INDEX: (
                "() => document.querySelectorAll('a[href*=\"preview_program.php\"]').length >= 5"
                " || /undergraduate\\s+programs/i.test(document.body ? document.body.innerText : '')"
                " || /programs,\\s*minors\\s*and\\s*certificates/i.test(document.body ? document.body.innerText : '')"
            ),
            PageKind.PROGRAM_PAGE: (
                "() => !!document.querySelector('h1') && (document.body ? document.body.innerText.length > 400 : false)"
            ),
        }.get(
            kind,
            "() => document.body ? document.body.innerText.length > 300 : false",
        )
        try:
            return bool(self._page.evaluate(js))
        except Exception:
            return False

    def _wait_semantic_ready(self, kind: PageKind) -> bool:
        deadline = time.monotonic() + self.cfg.readiness_timeout_ms / 1000
        while time.monotonic() < deadline:
            if self._semantic_marker_present(kind):
                return True
            time.sleep(0.4)
        return False

    def _stabilize(self) -> str:
        """Wait for a stable DOM content signature; return final HTML."""
        stable_needed = max(2, self.cfg.stabilization_polls)
        interval = self.cfg.stabilization_interval_ms / 1000
        last_sig = ""
        stable = 0
        html = ""
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                html = self._page.content()
            except Exception:
                time.sleep(interval)
                continue
            sig = hashlib.sha256(html.encode("utf-8", "ignore")).hexdigest()
            if sig == last_sig:
                stable += 1
                if stable >= stable_needed:
                    return html
            else:
                stable = 0
                last_sig = sig
            time.sleep(interval)
        return html

    # ------------------------------------------------------------ expansion
    def _expand_collapsed(self, kind: PageKind) -> int:
        """Activate legitimate expand controls (expand-all, accordions,
        aria-expanded=false toggles). Bounded; returns number of clicks."""
        clicks = 0
        scripts_clicked: set[str] = set()
        try:
            # 1. Explicit expand-all style controls.
            for locator in (
                "a:has-text('Expand All')",
                "button:has-text('Expand All')",
                "a:has-text('Show All')",
                "a:has-text('View All')",
            ):
                with contextlib.suppress(Exception):
                    for el in self._page.locator(locator).all()[:4]:
                        el.click(timeout=2000)
                        clicks += 1
                        time.sleep(0.35)
            # 2. aria-expanded=false toggles and accordion headers.
            selector = "[aria-expanded='false'], a.acalog-accordion, .acalog-expandable a"
            for _round in range(3):
                elements = self._page.locator(selector).all()
                if not elements:
                    break
                progressed = False
                for el in elements[:80]:
                    try:
                        key = el.evaluate("e => (e.outerHTML || '').slice(0, 160)")
                        if key in scripts_clicked:
                            continue
                        scripts_clicked.add(key)
                        el.scroll_into_view_if_needed(timeout=1500)
                        el.click(timeout=1500)
                        clicks += 1
                        progressed = True
                        time.sleep(0.2)
                    except Exception:
                        continue
                if not progressed:
                    break
                time.sleep(0.6)
        except Exception as e:
            log.debug("expansion pass ended: %s", e)
        return clicks

    def _scroll_through(self) -> None:
        with contextlib.suppress(Exception):
            self._page.evaluate(
                """async () => {
                    const step = 900;
                    for (let y = 0; y < document.body.scrollHeight; y += step) {
                        window.scrollTo(0, y);
                        await new Promise(r => setTimeout(r, 120));
                    }
                    window.scrollTo(0, 0);
                }"""
            )

    # ---------------------------------------------------------------- fetch
    def fetch(
        self,
        url: str,
        kind: PageKind,
        attempt_base: int = 1,
        wait_for_human: bool = False,
    ) -> FetchResult:
        check_robots_allowed(url)
        self._ensure_started()
        self.pacer.wait()
        start = time.monotonic()
        result = FetchResult(url=url, page_kind=kind, method="playwright", attempt=attempt_base)
        raw_html = ""
        try:
            response = self._page.goto(url, wait_until="domcontentloaded")
            if response is not None:
                result.http_status = response.status
                result.content_type = response.headers.get("content-type", "")
                with contextlib.suppress(Exception):
                    raw_html = response.text()
        except Exception as e:
            result.mode = AcquisitionMode.NETWORK_FAILURE
            result.error = f"{type(e).__name__}: {e}"
            result.elapsed_seconds = time.monotonic() - start
            return result

        result.raw_html = raw_html
        result.raw_html_sha256 = sha256_text(raw_html) if raw_html else ""

        # Challenge detection on the early DOM; the AWS WAF action header on
        # the navigation response is the definitive signal.
        early_html = ""
        with contextlib.suppress(Exception):
            early_html = self._page.content()
        challenged, evidence = detect_challenge(early_html, self._page.title() or "")
        waf_action = ""
        if response is not None:
            with contextlib.suppress(Exception):
                waf_action = response.headers.get("x-amzn-waf-action", "")
        if waf_action:
            challenged = True
            evidence = [f"x-amzn-waf-action header: {waf_action!r}", *evidence]
        if challenged:
            result.challenge_detected = True
            result.challenge_evidence = evidence
            # The WAF's JavaScript challenge solves itself in a real browser —
            # headless included — within seconds. Give it a short window
            # before any handoff (live finding 2026-07-19: headless runs
            # bailed out before the auto-challenge could finish).
            if self._await_challenge_autoresolve(kind):
                result.challenge_detected = False
                result.challenge_evidence = []
            elif wait_for_human and self.headed:
                solved = self._await_human_verification(kind)
                if not solved:
                    result.mode = AcquisitionMode.CHALLENGE_PAGE
                    result.elapsed_seconds = time.monotonic() - start
                    self._maybe_screenshot("challenge")
                    return result
            else:
                result.mode = AcquisitionMode.CHALLENGE_PAGE
                result.elapsed_seconds = time.monotonic() - start
                self._maybe_screenshot("challenge")
                return result

        self._wait_semantic_ready(kind)
        self._scroll_through()
        html = self._stabilize()

        ok, evidence_dict = validate_page(kind, html, self.cfg)
        if not ok:
            clicked = self._expand_collapsed(kind)
            if clicked:
                html = self._stabilize()
                ok, evidence_dict = validate_page(kind, html, self.cfg)
                evidence_dict["expand_clicks"] = clicked
        elif kind is PageKind.PROGRAM_PAGE:
            # Expand accordions even on valid pages so hidden requirement
            # content is present in the DOM snapshot. If expansion somehow
            # degrades the DOM, revert to the already-valid pre-expansion
            # snapshot instead of accepting a broken page.
            pre_html, pre_evidence = html, dict(evidence_dict)
            clicked = self._expand_collapsed(kind)
            if clicked:
                expanded_html = self._stabilize()
                expanded_ok, expanded_evidence = validate_page(kind, expanded_html, self.cfg)
                if expanded_ok:
                    html = expanded_html
                    evidence_dict = expanded_evidence
                    evidence_dict["expand_clicks"] = clicked
                else:
                    html = pre_html
                    evidence_dict = pre_evidence
                    evidence_dict["expand_clicks_reverted"] = clicked
                ok = True  # the pre-expansion page had already validated

        result.html = html
        result.rendered_dom_sha256 = sha256_text(html)
        with contextlib.suppress(Exception):
            result.page_title = self._page.title()
        result.final_url = self._page.url
        challenged, challenge_evidence = detect_challenge(html, result.page_title)
        result.challenge_detected = challenged
        result.challenge_evidence = challenge_evidence
        result.semantic_ok = ok and not challenged
        result.semantic_evidence = evidence_dict
        if challenged:
            result.mode = AcquisitionMode.CHALLENGE_PAGE
        elif result.semantic_ok:
            result.mode = AcquisitionMode.BROWSER_RENDERED_DOM
        else:
            result.mode = AcquisitionMode.INVALID_CONTENT
            self._maybe_screenshot("invalid")
        result.elapsed_seconds = time.monotonic() - start
        return result

    def _await_challenge_autoresolve(self, kind: PageKind, timeout_s: float = 30.0) -> bool:
        """Wait briefly for the WAF's automatic JS challenge to clear itself."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            time.sleep(2)
            try:
                html = self._page.content()
            except Exception:
                continue
            challenged, _ = detect_challenge(html, self._page.title() or "")
            if not challenged:
                log.info("Challenge auto-resolved by the browser; continuing.")
                return True
        return False

    def _await_human_verification(self, kind: PageKind) -> bool:
        """Headed mode: tell the user what to do, wait for the page to become valid."""
        log.warning(
            "HUMAN VERIFICATION REQUIRED: a verification page appeared. "
            "In the open browser window, complete the verification shown on the page. "
            "Waiting up to %.1f minutes...",
            self.cfg.challenge_wait_minutes,
        )
        deadline = time.monotonic() + self.cfg.challenge_wait_minutes * 60
        while time.monotonic() < deadline:
            time.sleep(3)
            try:
                html = self._page.content()
            except Exception:
                continue
            challenged, _ = detect_challenge(html, self._page.title() or "")
            if not challenged:
                ok, _ = validate_page(kind, html, self.cfg)
                if ok or self._semantic_marker_present(kind):
                    log.info("Verification completed; session saved. Continuing.")
                    return True
        return False

    def _maybe_screenshot(self, label: str) -> Path | None:
        if not self.cfg.save_failure_screenshots or self._page is None:
            return None
        try:
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)
            ts = utcnow_iso().replace(":", "").replace("-", "")
            path = self.screenshots_dir / f"{ts}_{label}.png"
            self._page.screenshot(path=str(path), full_page=True)
            return path
        except Exception:
            return None


class AcquisitionOrchestrator:
    """Chooses layers, records every attempt, saves debugging evidence."""

    def __init__(
        self,
        cfg: config.ScraperConfig,
        db: StateDB,
        state_dir: Path,
        screenshots_dir: Path,
        raw_dir: Path | None = None,
        rendered_dir: Path | None = None,
        headed: bool = False,
    ):
        self.cfg = cfg
        self.db = db
        self.pacer = Pacer(cfg)
        self.http = HttpFetcher(cfg, state_dir, self.pacer)
        self.state_dir = state_dir
        self.screenshots_dir = screenshots_dir
        self.raw_dir = raw_dir
        self.rendered_dir = rendered_dir
        self.headed = headed
        self._browser: BrowserFetcher | None = None

    # ----------------------------------------------------------- lifecycle
    @property
    def browser(self) -> BrowserFetcher:
        if self._browser is None:
            profile = self.cfg.browser_profile_dir or (self.state_dir / "browser_profile")
            self._browser = BrowserFetcher(
                self.cfg, profile, self.screenshots_dir, self.pacer, headed=self.headed
            )
        return self._browser

    def close(self) -> None:
        self.http.close()
        if self._browser is not None:
            self._browser.save_storage_state(self.state_dir / "storage_state.json")
            self._browser.close()

    # ------------------------------------------------------------- logging
    def _log(self, result: FetchResult, page_label: str) -> None:
        self.db.log_fetch(
            url=result.url,
            page_type=page_label,
            attempt=result.attempt,
            method=result.method,
            acquisition_mode=result.mode.value,
            http_status=result.http_status,
            content_type=result.content_type,
            elapsed_seconds=round(result.elapsed_seconds, 3),
            semantic_validation=json.dumps(result.semantic_evidence, default=str)[:1500],
            challenge_detected=result.challenge_detected,
            content_length=len(result.html or ""),
            raw_html_sha256=result.raw_html_sha256,
            rendered_dom_sha256=result.rendered_dom_sha256,
            result="ok" if result.ok else (result.error or result.mode.value),
        )

    def _save_evidence(self, result: FetchResult, label: str) -> None:
        try:
            if self.cfg.save_raw_html and self.raw_dir and result.raw_html:
                self.raw_dir.mkdir(parents=True, exist_ok=True)
                (self.raw_dir / f"{label}.html").write_text(result.raw_html, encoding="utf-8")
            if (
                self.cfg.save_rendered_html
                and self.rendered_dir
                and result.html
                and result.method == "playwright"
            ):
                self.rendered_dir.mkdir(parents=True, exist_ok=True)
                (self.rendered_dir / f"{label}.rendered.html").write_text(
                    result.html, encoding="utf-8"
                )
        except Exception as e:
            log.debug("evidence save failed: %s", e)

    # ------------------------------------------------------------- acquire
    def acquire(self, url: str, kind: PageKind, label: str = "page") -> FetchResult:
        """Layered acquisition with logging. Raises HumanVerificationRequired
        when a challenge blocks headless operation."""
        # Layer 1: direct HTTP.
        result = self.http.fetch(url, kind)
        self._log(result, label)
        self._save_evidence(result, f"{label}.direct")
        if result.ok:
            return result

        # Layer 2: first-party alternates (only when primary was not a challenge).
        if not result.challenge_detected:
            for alt in alternate_urls(url, kind):
                alt_result = self.http.fetch(alt, kind, attempt_base=2)
                alt_result.method = "httpx-alternate"
                if alt_result.mode is AcquisitionMode.DIRECT_HTML:
                    alt_result.mode = AcquisitionMode.ALTERNATE_FIRST_PARTY_HTML
                self._log(alt_result, label)
                self._save_evidence(alt_result, f"{label}.alternate")
                if alt_result.ok:
                    return alt_result

        # Layer 3: browser.
        if not self.cfg.allow_browser:
            return result
        browser_result = self.browser.fetch(url, kind, attempt_base=3, wait_for_human=self.headed)
        self._log(browser_result, label)
        self._save_evidence(browser_result, f"{label}.browser")
        if browser_result.ok:
            # Re-adopt cookies on EVERY browser success, not just the first:
            # the WAF token rotates mid-run (~hourly, observed 2026-07-19) and
            # the HTTP client needs the fresh token to recover direct
            # fetching; without this every later page pays the full browser
            # cost (minutes instead of seconds).
            self.http.adopt_browser_cookies(self.browser.cookies())
            return browser_result

        # Layer 4: human handoff.
        if browser_result.challenge_detected:
            if self.headed:
                # Headed wait already happened inside fetch(); a second failure
                # means the user did not complete verification in time.
                raise HumanVerificationRequired(
                    url,
                    "Verification was not completed in the open browser window. "
                    f"Open {url} in the scraper's browser window and complete the "
                    "verification, then rerun with --resume.",
                )
            raise HumanVerificationRequired(
                url,
                "The catalogue served a verification page that requires a human. "
                "Rerun with --headed; a browser window will open using the saved "
                f"profile. Complete the verification shown for {url}, and the run "
                "will continue automatically (session is persisted for next runs).",
            )
        return browser_result
