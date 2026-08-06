"""Semantic response validation.

HTTP 200 is never treated as success. Every fetched page must prove,
from its own content, that it is the page we asked for.
"""

from __future__ import annotations

import re

from usc_catalog_scraper import config
from usc_catalog_scraper.challenge_detection import detect_challenge
from usc_catalog_scraper.models import PageKind

CATALOGUE_TITLE_RE = re.compile(r"USC\s+Catalogue\s+(\d{4})-(\d{4})", re.I)
COURSE_CODE_RE = re.compile(r"\b[A-Z]{2,5}\s?-?\s?\d{3}[A-Z]?\b")
PROGRAM_LINK_RE = re.compile(r"preview_program\.php[^\"'<>\s]*poid=\d+", re.I)


def _text_of(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<noscript[^>]*>.*?</noscript>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def validate_page(kind: PageKind, html: str, cfg: config.ScraperConfig) -> tuple[bool, dict]:
    """Return (ok, evidence). Evidence records each check's outcome."""
    evidence: dict = {"kind": kind.value}
    if not html or not html.strip():
        evidence["empty_body"] = True
        return False, evidence

    challenged, challenge_evidence = detect_challenge(html)
    evidence["challenge_detected"] = challenged
    if challenge_evidence:
        evidence["challenge_evidence"] = challenge_evidence
    if challenged:
        return False, evidence

    text = _text_of(html)
    evidence["visible_text_chars"] = len(text)

    title_match = CATALOGUE_TITLE_RE.search(text)
    evidence["catalogue_title_found"] = bool(title_match)
    if title_match:
        evidence["catalogue_year_seen"] = f"{title_match.group(1)}-{title_match.group(2)}"

    program_links = len(set(PROGRAM_LINK_RE.findall(html)))
    evidence["program_link_count"] = program_links

    if kind is PageKind.PROGRAMS_INDEX:
        evidence["programs_context"] = "programs, minors and certificates" in text.lower()
        norm_target = cfg.boundary_heading.lower()
        evidence["target_heading_text_present"] = norm_target in text.lower()
        # A valid fully-listed index has many program links. A valid collapsed
        # landing page has the section taxonomy but no links yet; that page is
        # NOT sufficient for discovery, so it fails validation and the caller
        # escalates to the browser layer to expand it.
        ok = len(text) >= 1500 and evidence["programs_context"] and program_links >= 5
        evidence["ok_reason"] = (
            "programs context + >=5 program links" if ok else "insufficient index evidence"
        )
        return ok, evidence

    if kind is PageKind.PROGRAM_PAGE:
        evidence["course_code_count"] = len(COURSE_CODE_RE.findall(text))
        low = text.lower()
        requirement_signals = sum(
            1 for signal in ("unit", "requirement", "course", "major", "degree") if signal in low
        )
        evidence["requirement_signal_count"] = requirement_signals
        has_title = bool(re.search(r"<h1[^>]*>\s*\S", html, re.I)) or "Program:" in html
        evidence["program_title_present"] = has_title
        ok = len(text) >= 700 and has_title and requirement_signals >= 2
        evidence["ok_reason"] = (
            "title + requirement content" if ok else "insufficient program-page evidence"
        )
        return ok, evidence

    if kind in (PageKind.CATALOGUE_HOME, PageKind.CATALOGUE_LIST):
        low = text.lower()
        ok = len(text) >= 400 and ("catalogue" in low or "catalog" in low)
        evidence["ok_reason"] = "catalogue context" if ok else "no catalogue context"
        return ok, evidence

    evidence["ok_reason"] = "unknown page kind"
    return False, evidence
