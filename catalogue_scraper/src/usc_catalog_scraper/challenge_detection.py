"""Detect JavaScript-verification / anti-bot challenge pages.

Detection is evidence-based and conservative: text markers inside <noscript>
blocks do NOT count, because legitimate catalogue pages carry a
"Javascript is currently not supported" noscript banner (observed live on
catalogue.usc.edu 2026-07-09).
"""

from __future__ import annotations

import re

from usc_catalog_scraper import config


def _strip_noscript(html: str) -> str:
    return re.sub(r"<noscript[^>]*>.*?</noscript>", " ", html, flags=re.I | re.S)


def _title_of(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def _visible_text_len(html: str) -> int:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return len(re.sub(r"\s+", " ", text).strip())


def detect_challenge(html: str, page_title: str | None = None) -> tuple[bool, list[str]]:
    """Return (challenge_detected, evidence_strings)."""
    if not html:
        return False, []
    evidence: list[str] = []
    title = (page_title or _title_of(html)).lower()
    for marker in config.CHALLENGE_TITLE_MARKERS:
        if marker in title:
            evidence.append(f"title contains {marker!r}")

    lower_no_noscript = _strip_noscript(html).lower()
    for marker in config.CHALLENGE_TEXT_MARKERS:
        if marker in lower_no_noscript:
            evidence.append(f"body contains {marker!r}")

    raw_lower = html.lower()
    for marker in config.CHALLENGE_SCRIPT_MARKERS:
        if marker in raw_lower:
            evidence.append(f"script marker {marker!r}")

    if not evidence:
        return False, []

    # Weak, single body-text hits on an otherwise content-rich page are treated
    # as prose (e.g. an accessibility note), not a challenge wall.
    strong = [e for e in evidence if e.startswith(("title", "script"))]
    if strong:
        return True, evidence
    if _visible_text_len(html) < 3500:
        return True, evidence
    body_hits = [e for e in evidence if e.startswith("body")]
    if len(body_hits) >= 2:
        return True, evidence
    return False, evidence
