"""Program-link discovery inside the proven Undergraduate Programs section."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import Tag

from usc_catalog_scraper import config
from usc_catalog_scraper.boundary import (
    SectionSlice,
    dom_path,
    find_undergraduate_section,
    parse_container,
)
from usc_catalog_scraper.extraction import select_main_container, strip_navigation_regions
from usc_catalog_scraper.models import BoundaryEvidence, DiscoveredLink


def canonicalize_url(base_url: str, href: str, cfg: config.ScraperConfig) -> tuple[str, str, dict]:
    """Return (absolute_url, canonical_url, query_params)."""
    absolute = urljoin(base_url, (href or "").strip())
    parts = urlsplit(absolute)
    scheme = "https" if parts.scheme in ("http", "https", "") else parts.scheme
    host = parts.netloc.lower()
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    kept = {
        k: v
        for k, v in params.items()
        if k not in config.STRIP_QUERY_PARAMS
        and not any(k.startswith(p) for p in config.STRIP_QUERY_PARAM_PREFIXES)
    }
    query = urlencode(sorted(kept.items()))
    canonical = urlunsplit((scheme, host, parts.path, query, ""))
    return absolute, canonical, params


def is_program_link(absolute_url: str, cfg: config.ScraperConfig) -> bool:
    parts = urlsplit(absolute_url)
    if not any(marker in parts.path for marker in config.PROGRAM_URL_PATH_MARKERS):
        return False
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    return all(p in params and params[p] for p in config.PROGRAM_URL_REQUIRED_PARAMS)


def _is_interface_link(href: str) -> bool:
    low = (href or "").strip().lower()
    if not low:
        return True
    if any(low.startswith(p) for p in config.INTERFACE_LINK_PREFIXES):
        return True
    path = urlsplit(low).path
    return any(marker in path for marker in config.INTERFACE_PATH_MARKERS)


def _clean_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def collect_links_from_anchors(
    anchors: list[Tag],
    base_url: str,
    section_heading: str,
    cfg: config.ScraperConfig,
) -> tuple[list[DiscoveredLink], int]:
    """Canonicalize, filter to program links, deduplicate by (catoid, poid)."""
    links: list[DiscoveredLink] = []
    seen_ids: set[tuple[str, str]] = set()
    seen_canonical: set[str] = set()
    duplicates = 0
    seq = 0
    for a in anchors:
        href = str(a.get("href") or "")
        if _is_interface_link(href):
            continue
        absolute, canonical, params = canonicalize_url(base_url, href, cfg)
        if not is_program_link(absolute, cfg):
            continue
        catoid = str(params.get("catoid", ""))
        poid = str(params.get("poid", ""))
        key = (catoid, poid)
        if key in seen_ids or canonical in seen_canonical:
            duplicates += 1
            continue
        seen_ids.add(key)
        seen_canonical.add(canonical)
        seq += 1
        links.append(
            DiscoveredLink(
                sequence=seq,
                title=_clean_title(a.get_text(" ", strip=True)),
                href=href,
                absolute_url=absolute,
                canonical_url=canonical,
                catoid=catoid,
                poid=poid,
                returnto=str(params.get("returnto", "")),
                section_heading=section_heading,
                dom_path=dom_path(a),
            )
        )
    return links, duplicates


def discover_program_links(
    html: str,
    base_url: str,
    cfg: config.ScraperConfig,
    strict: bool = True,
) -> tuple[list[DiscoveredLink], BoundaryEvidence, int, SectionSlice]:
    """Full discovery: main container -> section boundary -> in-section links.

    Returns (links, boundary_evidence, duplicate_count, section_slice).
    Raises BoundaryNotProvableError when the boundary cannot be proven (strict).
    """
    soup = parse_container(html)
    container, container_evidence = select_main_container(soup, cfg)
    # Navigation landmarks are stripped BEFORE boundary detection so nav/sidebar
    # copies of section headings cannot hijack the boundary and nav quick-links
    # cannot be collected (adversarial review findings 9a/N1).
    boundary_container = strip_navigation_regions(container)
    section = find_undergraduate_section(boundary_container, cfg, strict=strict)
    links, duplicates = collect_links_from_anchors(
        section.anchors, base_url, section.heading.info.text, cfg
    )
    section.evidence.links_in_section = len(links)
    section.evidence.container_description = (
        f"{section.evidence.container_description} | selected by: {container_evidence}"
    )
    if links:
        section.evidence.first_included_title = links[0].title
        section.evidence.last_included_title = links[-1].title
    return links, section.evidence, duplicates, section
