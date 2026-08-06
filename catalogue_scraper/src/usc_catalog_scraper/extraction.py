"""Program-page main-content identification, noise removal, metadata capture.

Content region selection is a scored, multi-signal comparison — never one CSS
selector. The winning selector/method is recorded for the audit trail.
"""

from __future__ import annotations

import copy
import math
import re

from bs4 import BeautifulSoup, Tag

from usc_catalog_scraper import config
from usc_catalog_scraper.classification import extract_credential_field, normalize_title
from usc_catalog_scraper.models import ProgramMetadata

_CANDIDATE_SELECTORS: tuple[tuple[str, str], ...] = (
    ("main", "main element"),
    ("article", "article element"),
    ("[role=main]", "aria main landmark"),
    ("td.block_content", "acalog block_content cell"),
    ("div.block_content", "acalog block_content div"),
    ("#acalog-content", "acalog content anchor region"),
    ("div.custom_leftpad_20", "acalog custom content region"),
    ("#content", "id=content region"),
    (".main-content", "main-content class region"),
)

_NAV_CLASS_RE = re.compile(
    r"(?:^|\b)(nav|navbar|menu|sidebar|footer|header|breadcrumb|social|share|cookie|banner|skiplink)(?:\b|$)",
    re.I,
)

# Labels (from _CANDIDATE_SELECTORS) that identify a TRUE catalogue content
# region — a container that holds only the program's own content. Everything
# else ("document body fallback", "aria main landmark", which on the live
# catalogue is a page-level <tr> wrapping the site header) also contains page
# chrome, so it must never be used for a program page.
#
# Incident 2026-07-30: container choice was decided purely by score, and on
# pages whose program content is short relative to the page chrome the whole
# <body> outscored td.block_content by as little as 0.3 points (poid=31805,
# "Environmental Science and Health (BA)": body 305.0 vs block_content 304.7).
# The body then rendered site header/nav as content — 158 of 470 outputs. A
# program page's container is now a STRUCTURAL requirement, not a score.
_CONTENT_REGION_LABELS: frozenset[str] = frozenset(
    label for _sel, label in _CANDIDATE_SELECTORS if "acalog" in label
)

# Page-chrome probes, used as a SECOND eligibility tier so that a clean content
# region behind an unfamiliar selector is still usable if USC ever renames its
# acalog classes — instead of the whole page being refused.
#
# These four probes were chosen because they discriminate perfectly on the seven
# real page snapshots captured during the incident: each flags the whole <body>
# on 7/7 pages and the correct `td.block_content` region on 0/7. Two candidate
# probes were REJECTED by that same measurement: a `gateway-toolbar` class test
# (flags the correct region 7/7 — the toolbar lives inside block_content) and a
# "Begin/End Responsive" text test (flags neither). Do not add a probe without
# re-running that measurement.
_CHROME_TEXT_RE = re.compile(
    r"skip to (?:navigation|content)|university of southern california", re.I
)
_CHROME_ROLE_RE = re.compile(r"^(navigation|banner|contentinfo)$", re.I)


def has_page_chrome(el: Tag) -> bool:
    """True when this element contains site furniture rather than only content."""
    if el.name in ("body", "html", "[document]"):
        return True
    if el.find(["nav", "header", "footer"]) is not None:
        return True
    if el.find(True, role=_CHROME_ROLE_RE) is not None:
        return True
    return bool(_CHROME_TEXT_RE.search(el.get_text(" ", strip=True)))


class ContentRegionNotFound(RuntimeError):
    """No trustworthy program-content region exists in this page/DOM.

    Raised instead of silently falling back to the whole document, so the
    caller can escalate (browser render / retry) or record an explicit
    failure. Never swallowed into an output file.
    """

    def __init__(self, message: str, candidates_seen: list[str] | None = None):
        super().__init__(message)
        self.candidates_seen = candidates_seen or []


def _text_len(el: Tag) -> int:
    return len(el.get_text(" ", strip=True))


def _link_text_len(el: Tag) -> int:
    return sum(len(a.get_text(" ", strip=True)) for a in el.find_all("a"))


def _score(el: Tag) -> float:
    text_len = _text_len(el)
    if text_len == 0:
        return -1000.0
    headings = len(el.find_all(re.compile(r"^h[1-6]$")))
    lists = len(el.find_all("li"))
    tables = len(el.find_all("table"))
    acalog_cores = len(el.find_all(class_=re.compile("acalog", re.I)))
    has_h1 = 1 if el.find("h1") else 0
    link_ratio = _link_text_len(el) / max(1, text_len)
    score = (
        math.log(text_len + 1) * 12
        + headings * 6
        + min(lists, 200) * 0.6
        + tables * 5
        + min(acalog_cores, 50) * 2
        + has_h1 * 40
    )
    # Navigation-dominated regions: mostly links.
    if link_ratio > 0.85:
        score -= 80
    classes_id = " ".join(el.get("class") or []) + " " + str(el.get("id") or "")
    if _NAV_CLASS_RE.search(classes_id):
        score -= 120
    # The whole document always contains every candidate; it is a fallback and
    # must lose ties against a specific landmark region.
    if el.name in ("body", "html"):
        score -= 30
    # Navigation landmarks must never win, whatever their id/class say.
    if el.name in ("nav", "aside", "header", "footer"):
        score -= 200
    return score


def strip_navigation_regions(container: Tag) -> Tag:
    """Deep copy of container with navigation landmarks removed.

    Used before boundary detection so sidebar/nav copies of section headings
    and quick-links menus can neither hijack the boundary nor contribute links.
    A region is only removed when it is clearly navigational (element name,
    ARIA role, or nav-ish class/id) AND does not hold the bulk of the content.
    """
    cleaned = copy.copy(container)
    total_len = max(1, _text_len(cleaned))
    removable: list[Tag] = []
    for el in cleaned.find_all(["nav", "aside", "header", "footer"]):
        removable.append(el)
    for el in cleaned.find_all(
        True, role=re.compile("^(navigation|banner|contentinfo|search)$", re.I)
    ):
        if isinstance(el, Tag):
            removable.append(el)
    for el in cleaned.find_all(True):
        if not isinstance(el, Tag):
            continue
        ident = " ".join(el.get("class") or []) + " " + str(el.get("id") or "")
        if ident.strip() and _NAV_CLASS_RE.search(ident):
            removable.append(el)
    seen: set[int] = set()
    for el in removable:
        if id(el) in seen or el.parent is None:
            continue
        seen.add(id(el))
        try:
            if _text_len(el) / total_len > 0.45:
                continue  # refuse to gut a mis-labelled main region
            el.decompose()
        except Exception:
            continue
    return cleaned


def select_main_container(
    soup: BeautifulSoup,
    cfg: config.ScraperConfig,
    require_content_region: bool = False,
) -> tuple[Tag, str]:
    """Pick the program/content region. Returns (element, method-evidence).

    With require_content_region=True (program pages) only a true catalogue
    content region may win — the whole-document body and page-level landmarks
    are not eligible at any score, and ContentRegionNotFound is raised when no
    content region exists. See _CONTENT_REGION_LABELS for the incident this
    guards against.
    """
    candidates: list[tuple[Tag, str]] = []
    for selector, label in _CANDIDATE_SELECTORS:
        try:
            found = list(soup.select(selector))
        except Exception:
            found = []
        for el in found[:4]:
            target = el
            # An anchor/heading id marks the region start; use its enclosing cell.
            if selector == "#acalog-content" and el.name in ("a", "h1", "span"):
                parent = el.find_parent(["td", "div", "main", "article"])
                if parent is not None:
                    target = parent
            if isinstance(target, Tag):
                candidates.append((target, f"{label} ({selector})"))
    body = soup.body if soup.body else soup
    if isinstance(body, Tag):
        candidates.append((body, "document body fallback"))

    scored: list[tuple[float, Tag, str]] = []
    seen: set[int] = set()
    for el, label in candidates:
        if id(el) in seen:
            continue
        seen.add(id(el))
        # Platform-specific regions (acalog block_content etc.) are exact
        # content markers; when present they must beat the generic landmarks
        # and the body fallback, whose bulk-text scores run slightly higher on
        # the live table-layout pages (verified 2026-07-13).
        bonus = 50.0 if "acalog" in label else 0.0
        scored.append((_score(el) + bonus, el, label))
    scored.sort(key=lambda t: t[0], reverse=True)

    if require_content_region:
        # Structural gate: only a true content region is eligible, regardless
        # of score. Scores still order the eligible regions among themselves
        # (block_content, the widest region, naturally outscores its own
        # sub-sections).
        eligible = [
            t
            for t in scored
            if any(t[2].startswith(lbl) for lbl in _CONTENT_REGION_LABELS) and _text_len(t[1]) > 0
        ]
        tier = "platform-content-region"
        if not eligible:
            # Tier 2: no recognised platform region. Rather than refuse the page
            # outright (which loses the programme entirely if USC renames its
            # classes), accept the best-scoring candidate that is demonstrably
            # chrome-free. The whole document can never qualify: has_page_chrome()
            # rejects body/html unconditionally, and the 107 body additionally
            # carries a skip-link and the site header.
            # Candidate DISCOVERY must widen too: a region behind an unknown
            # selector is never in `scored` at all. Derive candidates from the
            # page's own <h1> by walking outward to its chrome-free block
            # ancestors; scoring then picks the widest such region (more text =
            # higher score) and the walk stops before body/html.
            structural: list[tuple[float, Tag, str]] = []
            h1 = soup.find("h1")
            if isinstance(h1, Tag):
                for anc in h1.parents:
                    if not isinstance(anc, Tag) or anc.name in ("body", "html", "[document]"):
                        break
                    if (
                        anc.name in ("td", "div", "section", "article", "main")
                        and _text_len(anc) > 0
                        and not has_page_chrome(anc)
                    ):
                        structural.append(
                            (_score(anc), anc, f"structural chrome-free <{anc.name}> around h1")
                        )
            pool = scored + structural
            pool.sort(key=lambda t: t[0], reverse=True)
            eligible = [t for t in pool if _text_len(t[1]) > 0 and not has_page_chrome(t[1])]
            tier = "chrome-free-fallback"
        if not eligible:
            raise ContentRegionNotFound(
                "no catalogue content region (acalog block_content / content anchor) "
                "and no chrome-free candidate found in this page; refusing to fall "
                "back to the whole document",
                [
                    f"{t[2]} score={t[0]:.1f} textlen={_text_len(t[1])} "
                    f"chrome={has_page_chrome(t[1])}"
                    for t in scored[:8]
                ],
            )
        best_score, best_el, best_label = eligible[0]
        # Compare by identity: bs4 Tag.__eq__ is a deep structural comparison, so
        # `t not in eligible` would treat two distinct but identically-marked-up
        # elements as the same one and could suppress this evidence note.
        eligible_ids = {id(t[1]) for t in eligible}
        rejected = [t for t in scored if id(t[1]) not in eligible_ids][:1]
        note = (
            f"; outscored-but-ineligible: {rejected[0][2]} score={rejected[0][0]:.1f}"
            if rejected and rejected[0][0] > best_score
            else ""
        )
        return best_el, f"{best_label} score={best_score:.1f} [{tier}]{note}"

    best_score, best_el, best_label = scored[0]
    runner = f"; runner-up: {scored[1][2]} score={scored[1][0]:.1f}" if len(scored) > 1 else ""
    evidence = f"{best_label} score={best_score:.1f}{runner}"
    return best_el, evidence


def capture_breadcrumbs(soup: BeautifulSoup) -> str:
    """Breadcrumb / 'Return to' context, captured before noise removal."""
    crumbs: list[str] = []
    for sel in (
        ".breadcrumb",
        ".breadcrumbs",
        "#breadcrumb",
        "[aria-label=breadcrumb]",
        ".acalog-breadcrumb",
    ):
        for el in soup.select(sel):
            text = el.get_text(" > ", strip=True)
            if text:
                text = re.sub(r"\s+", " ", text)
                # Literal ">" separators in the source combine with the join
                # separator; collapse repeats.
                text = re.sub(r"(?:\s*>\s*)+", " > ", text)
                crumbs.append(text)
    if not crumbs:
        # The catalogue's own "Return to: ..." link is the reliable carrier;
        # a regex over flowing page text runs on into adjacent prose.
        for a in soup.find_all("a"):
            text = a.get_text(" ", strip=True)
            if text.lower().startswith("return to") and 10 <= len(text) <= 120:
                crumbs.append(re.sub(r"\s+", " ", text))
                break
    if not crumbs:
        m = re.search(r"Return to[^<:]*:?\s*([^<>{|}]{3,120})", soup.get_text(" ", strip=True))
        if m:
            crumbs.append(f"Return to: {m.group(1).strip()}")
    return " | ".join(dict.fromkeys(crumbs))[:400]


def clean_content(container: Tag, cfg: config.ScraperConfig) -> Tag:
    """Return a cleaned deep copy with interface noise removed.

    Content hidden behind collapsed accordions is preserved: nothing is removed
    for being visually hidden; removal is by interface selector/pattern only.
    """
    cleaned = copy.copy(container)
    for selector in config.NOISE_CSS_SELECTORS:
        try:
            for el in cleaned.select(selector):
                el.decompose()
        except Exception:
            continue
    # Interface wrappers by id/class name (never removes requirement content).
    for el in list(cleaned.find_all(True)):
        # Decomposing an element orphans descendants still queued in this
        # list; touching their attributes raises on bs4>=4.13.
        if not isinstance(el, Tag) or el.decomposed:
            continue
        ident = " ".join(el.get("class") or []) + " " + str(el.get("id") or "")
        if not ident.strip():
            continue
        if _NAV_CLASS_RE.search(ident) and not el.find(re.compile(r"^h[1-6]$")):
            text = el.get_text(" ", strip=True).lower()
            if len(text) < 400 and not re.search(r"\b(unit|course|requirement)\b", text):
                el.decompose()
    return cleaned


_SCHOOL_RE = re.compile(
    r"\b((?:[A-Z][\w'&.-]+\s+){0,6}(?:School|College|Academy|Conservatory)(?:\s+(?:of|for)\s+[A-Z][\w'&,.\- ]{2,60})?)"
)


def extract_metadata(
    soup: BeautifulSoup,
    container: Tag,
    url: str,
    canonical_url: str,
    catoid: str,
    poid: str,
    catalogue_year: str,
    cfg: config.ScraperConfig,
) -> ProgramMetadata:
    meta = ProgramMetadata(
        catalogue_year=catalogue_year,
        catalogue_identifier=f"catoid={catoid}",
        program_identifier=f"poid={poid}",
        source_url=url,
        canonical_url=canonical_url,
    )
    h1 = container.find("h1") or soup.find("h1")
    if h1 is not None:
        meta.program_name = normalize_title(h1.get_text(" ", strip=True))
    else:
        title = soup.find("title")
        if title:
            t = normalize_title(title.get_text())
            t = re.sub(r"^Program:\s*", "", t)
            t = re.sub(r"\s*-\s*University of Southern California.*$", "", t)
            meta.program_name = t
    if meta.program_name:
        _, field = extract_credential_field(meta.program_name)
        meta.credential = field
    meta.breadcrumbs = capture_breadcrumbs(soup)

    # School / academic unit: first plausible unit mention near the top.
    # Elements are scanned individually so a match cannot bleed across elements.
    for el in container.find_all(["em", "i", "p", "a", "h2", "div"], limit=60):
        text = el.get_text(" ", strip=True)
        if not text or len(text) > 200:
            continue
        m = _SCHOOL_RE.search(text)
        if m:
            candidate = m.group(1).strip().rstrip(",.;")
            if 4 <= len(candidate) <= 90 and not candidate.lower().startswith("university"):
                meta.school = candidate
                break
    # Live 2026-2027 pages have no short school element; the name only occurs
    # inside prose, where any regex capture runs on. An empty field is honest;
    # a run-on guess is not.
    return meta
