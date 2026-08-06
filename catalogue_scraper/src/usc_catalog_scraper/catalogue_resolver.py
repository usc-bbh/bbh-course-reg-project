"""Latest-catalogue resolution from first-party evidence.

Order of evidence:
1. misc/catalog_list.php — the official all-catalogues list, which marks
   archived editions with "[ARCHIVED CATALOGUE]" (observed live 2026-07-09).
2. The chosen catalogue's index.php — title must corroborate the year, and its
   navigation supplies the "Programs, Minors and Certificates" navoid.
Never assumes a larger catoid is newer (live evidence: 2023-2024 is catoid 18,
2024-2025 is catoid 20 — not contiguous). Falls back to the supplied URL with
an explicit "not verified" note rather than guessing.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urljoin, urlsplit

from bs4 import BeautifulSoup

from usc_catalog_scraper import config
from usc_catalog_scraper.logging_config import get_logger
from usc_catalog_scraper.models import CatalogueInfo, PageKind, ResolutionResult

log = get_logger("resolver")

YEAR_RE = re.compile(r"(\d{4})\s*[-–]\s*(\d{4})")
TITLE_RE = re.compile(r"USC\s+Catalogue\s+(\d{4})\s*[-–]\s*(\d{4})", re.I)
PROGRAMS_LINK_TEXT = "programs, minors and certificates"


def params_of(url: str) -> dict[str, str]:
    return dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))


def parse_catalog_list(html: str, base_url: str) -> list[CatalogueInfo]:
    """Entries from misc/catalog_list.php, newest evidence preserved verbatim."""
    soup = BeautifulSoup(html, "lxml")
    entries: list[CatalogueInfo] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "index.php" not in href or "catoid=" not in href:
            continue
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if "catalogue" not in title.lower() and "catalog" not in title.lower():
            continue
        catoid = params_of(urljoin(base_url, str(href))).get("catoid", "")
        if not catoid:
            continue
        # Archive marker appears as text following the anchor.
        following_parts: list[str] = []
        node = a.next_sibling
        for _ in range(4):
            if node is None:
                break
            if hasattr(node, "get_text"):
                following_parts.append(node.get_text(" ", strip=True))
            else:
                following_parts.append(str(node))
            node = node.next_sibling
        following = " ".join(following_parts)
        parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        archived = "archived catalogue" in (following + " " + parent_text).lower()
        m = YEAR_RE.search(title)
        year = f"{m.group(1)}-{m.group(2)}" if m else ""
        entries.append(CatalogueInfo(title=title, year=year, catoid=catoid, archived=archived))
    # Deduplicate by catoid keeping first occurrence.
    seen: set[str] = set()
    unique: list[CatalogueInfo] = []
    for e in entries:
        if e.catoid in seen:
            continue
        seen.add(e.catoid)
        unique.append(e)
    return unique


def find_programs_navoid(index_html: str, base_url: str, catoid: str) -> str:
    """Locate the Programs, Minors and Certificates link in official navigation."""
    soup = BeautifulSoup(index_html, "lxml")
    for a in soup.find_all("a", href=True):
        text = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip().lower()
        if text == PROGRAMS_LINK_TEXT:
            p = params_of(urljoin(base_url, str(a["href"])))
            if p.get("catoid") == catoid and p.get("navoid"):
                return p["navoid"]
    # Second pass: startswith, in case of decorations.
    for a in soup.find_all("a", href=True):
        text = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip().lower()
        if text.startswith(PROGRAMS_LINK_TEXT):
            p = params_of(urljoin(base_url, str(a["href"])))
            if p.get("catoid") == catoid and p.get("navoid"):
                return p["navoid"]
    return ""


def resolve_latest(orchestrator, cfg: config.ScraperConfig) -> ResolutionResult:
    """orchestrator: AcquisitionOrchestrator (duck-typed for tests)."""
    supplied = cfg.start_url
    supplied_params = params_of(supplied)
    supplied_catoid = supplied_params.get("catoid", "")
    supplied_navoid = supplied_params.get("navoid", "")
    notes: list[str] = []

    fallback = ResolutionResult(
        supplied_url=supplied,
        resolved_url=supplied,
        catalogue=CatalogueInfo(
            catoid=supplied_catoid, navoid=supplied_navoid, programs_url=supplied
        ),
        method="supplied-url-fallback",
        verified=False,
        notes=notes,
    )

    if not cfg.latest_resolution:
        notes.append("latest resolution disabled by --no-latest-resolution")
        fallback.method = "supplied-url-forced"
        return fallback

    supplied_parts = urlsplit(supplied)
    host = supplied_parts.netloc or config.CATALOGUE_HOST
    scheme = supplied_parts.scheme or "https"
    list_url = f"{scheme}://{host}/misc/catalog_list.php?catoid={supplied_catoid or ''}".rstrip("=")
    list_result = orchestrator.acquire(list_url, PageKind.CATALOGUE_LIST, label="catalogue_list")
    if not list_result.ok:
        notes.append(
            f"catalogue list not acquired ({list_result.mode.value}); "
            "automatic latest-catalogue resolution NOT verified"
        )
        return fallback

    entries = parse_catalog_list(list_result.html, list_result.final_url or list_url)
    current = [e for e in entries if not e.archived and e.year]
    notes.append(
        f"catalogue list entries: {[(e.year, e.catoid, 'archived' if e.archived else 'current') for e in entries][:14]}"
    )
    if not current:
        notes.append("no non-archived catalogue found in official list; using supplied URL")
        return fallback

    newest = max(current, key=lambda e: int(e.year.split("-")[0]))
    index_url = f"{scheme}://{host}/index.php?catoid={newest.catoid}"
    index_result = orchestrator.acquire(index_url, PageKind.CATALOGUE_HOME, label="catalogue_home")
    if not index_result.ok:
        notes.append(f"could not verify {newest.title} via its index page; using supplied URL")
        return fallback

    m = TITLE_RE.search(index_result.html)
    if not m or f"{m.group(1)}-{m.group(2)}" != newest.year:
        notes.append(
            f"index page year evidence {m.groups() if m else None} does not corroborate "
            f"{newest.year}; using supplied URL"
        )
        return fallback

    navoid = find_programs_navoid(
        index_result.html, index_result.final_url or index_url, newest.catoid
    )
    if not navoid:
        notes.append(
            f"Programs, Minors and Certificates link not found in {newest.title} navigation; "
            "using supplied URL"
        )
        return fallback

    programs_url = f"{scheme}://{host}/content.php?catoid={newest.catoid}&navoid={navoid}"
    newest.navoid = navoid
    newest.programs_url = programs_url
    if newest.catoid == supplied_catoid and navoid == supplied_navoid:
        notes.append("supplied URL confirmed as the newest current catalogue's programs page")
    else:
        notes.append(
            f"resolved newer/current catalogue {newest.title}: catoid={newest.catoid}, "
            f"navoid={navoid} (supplied was catoid={supplied_catoid}, navoid={supplied_navoid})"
        )
    return ResolutionResult(
        supplied_url=supplied,
        resolved_url=programs_url,
        catalogue=newest,
        method="archive-list+index-navigation",
        verified=True,
        notes=notes,
    )
