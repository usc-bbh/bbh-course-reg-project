"""Strict first-section boundary detection for "Undergraduate Programs".

Heading-like elements are recognized through multiple signals (native h1-h6,
role="heading", vendor-specific patterns, documented strong-label fallback).
Collection walks the document in order and stops at the first later heading
whose effective level is equal to or higher (numerically <=) than the target's.
"""

from __future__ import annotations

import html as html_module
import re
import unicodedata
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from usc_catalog_scraper import config
from usc_catalog_scraper.models import BoundaryEvidence, HeadingInfo

_DECORATIVE_EDGE = "  \t\r\n:;·•*–—-.[]|"


class BoundaryNotProvableError(RuntimeError):
    """Raised in strict mode when the section boundary cannot be proven."""

    def __init__(self, message: str, headings_seen: list[dict] | None = None):
        super().__init__(message)
        self.headings_seen = headings_seen or []


def normalize_heading_text(text: str) -> str:
    """Decode entities, normalize unicode, collapse whitespace, strip decoration."""
    text = html_module.unescape(text or "")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(" ", " ").replace("​", "")
    # Normalize typographic apostrophes so "Bachelor’s" == "Bachelor's".
    text = text.replace("’", "'")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(_DECORATIVE_EDGE)
    return text.casefold()


def dom_path(el: Tag) -> str:
    """Concise, reproducible DOM locator like body>div#content>h2[3]."""
    parts: list[str] = []
    node: Tag | None = el
    while isinstance(node, Tag) and node.name != "[document]":
        ident = node.name
        if node.get("id"):
            ident += f"#{node['id']}"
            parts.append(ident)
            break
        siblings = [s for s in node.find_previous_siblings(node.name)]
        if siblings:
            ident += f"[{len(siblings) + 1}]"
        parts.append(ident)
        node = node.parent if isinstance(node.parent, Tag) else None
        if len(parts) > 12:
            break
    return ">".join(reversed(parts))


@dataclass
class _Candidate:
    element: Tag
    info: HeadingInfo


@dataclass
class SectionSlice:
    heading: _Candidate
    terminating: _Candidate | None
    anchors: list[Tag]
    evidence: BoundaryEvidence
    elements: list[Tag] = field(default_factory=list)


def _is_strong_label(el: Tag) -> str | None:
    """Return label text if el is a paragraph-ish wrapper whose only meaningful
    content is a single <strong>/<b> — a visual section label."""
    if el.name not in ("p", "td", "div"):
        return None
    children = [c for c in el.children if isinstance(c, Tag) or str(c).strip()]
    tags = [c for c in children if isinstance(c, Tag)]
    texts = [str(c).strip() for c in children if not isinstance(c, Tag) and str(c).strip()]
    if texts:
        return None
    if len(tags) != 1 or tags[0].name not in ("strong", "b"):
        return None
    label = tags[0].get_text(" ", strip=True)
    if not label or len(label) > 80:
        return None
    return label


def iter_heading_candidates(
    container: Tag,
    cfg: config.ScraperConfig,
    allow_strong_label_fallback: bool = False,
) -> list[_Candidate]:
    """All heading-like elements inside container, in document order."""
    out: list[_Candidate] = []
    native_re = re.compile(r"^h([1-6])$", re.I)
    for el in container.find_all(True):
        if not isinstance(el, Tag):
            continue
        m = native_re.match(el.name or "")
        text = el.get_text(" ", strip=True)
        if m and text:
            out.append(
                _Candidate(
                    el,
                    HeadingInfo(
                        text=text,
                        normalized=normalize_heading_text(text),
                        level=int(m.group(1)),
                        source="native-h",
                        tag=el.name,
                        dom_path=dom_path(el),
                    ),
                )
            )
            continue
        role = str(el.get("role") or "").lower() if el.has_attr("role") else ""
        if role == "heading" and text:
            try:
                level = int(str(el.get("aria-level") or "2"))
            except (TypeError, ValueError):
                level = 2
            out.append(
                _Candidate(
                    el,
                    HeadingInfo(
                        text=text,
                        normalized=normalize_heading_text(text),
                        level=level,
                        source="role-heading",
                        tag=el.name,
                        dom_path=dom_path(el),
                    ),
                )
            )
            continue
        classes = " ".join(el.get("class") or [])
        for signal in config.VENDOR_HEADING_SIGNALS:
            if signal.get("strong_label_fallback"):
                if not allow_strong_label_fallback:
                    continue
                label = _is_strong_label(el)
                if label:
                    out.append(
                        _Candidate(
                            el,
                            HeadingInfo(
                                text=label,
                                normalized=normalize_heading_text(label),
                                level=int(signal["level"]),
                                source="strong-label",
                                tag=el.name,
                                dom_path=dom_path(el),
                            ),
                        )
                    )
                    break
                continue
            if (
                el.name in signal["tags"]
                and signal["class_regex"]
                and text
                and "|" not in text  # filter bars are not headings
                and len(text) <= 60
                and re.search(signal["class_regex"], classes, re.I)
            ):
                out.append(
                    _Candidate(
                        el,
                        HeadingInfo(
                            text=text,
                            normalized=normalize_heading_text(text),
                            level=int(signal["level"]),
                            source=f"vendor:{signal['name']}",
                            tag=el.name,
                            dom_path=dom_path(el),
                        ),
                    )
                )
                break
    return out


def _positions(container: Tag) -> dict[int, int]:
    return {id(el): i for i, el in enumerate(container.find_all(True))}


def _can_terminate(start_source: str, cand_source: str) -> bool:
    """Vendor/visual heading signals only terminate sections that were
    themselves started by the same signal family; native and ARIA headings
    terminate anything. Prevents decorative vendor-class elements from acting
    as peers of a real h2 (adversarial review finding V1/V2)."""
    if cand_source in ("native-h", "role-heading"):
        return True
    if cand_source.startswith("vendor:"):
        return start_source.startswith("vendor:") or start_source == "strong-label"
    if cand_source == "strong-label":
        return start_source == "strong-label"
    return True


def find_undergraduate_section(
    container: Tag,
    cfg: config.ScraperConfig,
    strict: bool = True,
) -> SectionSlice:
    """Locate the first target-heading section and slice its content.

    Raises BoundaryNotProvableError in strict mode when the target heading is
    absent or ambiguity prevents a provable boundary.
    """
    target = normalize_heading_text(cfg.boundary_heading)
    candidates = iter_heading_candidates(container, cfg)
    if not candidates:
        # Documented structural fallback: only if the page has NO recognizable
        # headings at all do we consider visual strong-labels.
        candidates = iter_heading_candidates(container, cfg, allow_strong_label_fallback=True)

    headings_seen = [
        {
            "text": c.info.text,
            "level": c.info.level,
            "source": c.info.source,
            "dom_path": c.info.dom_path,
        }
        for c in candidates
    ]

    start: _Candidate | None = None
    for cand in candidates:
        if cand.info.normalized == target:
            start = cand
            break
    if start is None:
        msg = (
            f"Heading {cfg.boundary_heading!r} not found. "
            f"Headings present: {[h['text'] for h in headings_seen][:40]}"
        )
        raise BoundaryNotProvableError(msg, headings_seen)

    pos = _positions(container)
    start_idx = pos[id(start.element)]
    # Skip the heading element's own subtree.
    descendant_ids = {id(d) for d in start.element.find_all(True)}
    after_start = start_idx

    terminating: _Candidate | None = None
    for cand in candidates:
        idx = pos.get(id(cand.element))
        if idx is None or idx <= start_idx:
            continue
        if id(cand.element) in descendant_ids:
            continue
        if not _can_terminate(start.info.source, cand.info.source):
            continue
        if cand.info.level <= start.info.level:
            terminating = cand
            break

    end_idx = pos[id(terminating.element)] if terminating else len(pos) + 1
    # An anchor that WRAPS the terminating heading belongs to the next section,
    # even though it precedes the heading in pre-order.
    terminator_ancestor_ids: set[int] = (
        {id(p) for p in terminating.element.parents} if terminating else set()
    )

    anchors: list[Tag] = []
    elements: list[Tag] = []
    for el in container.find_all(True):
        idx = pos[id(el)]
        if idx <= after_start or idx >= end_idx:
            continue
        if id(el) in descendant_ids:
            continue
        elements.append(el)
        if el.name == "a" and el.has_attr("href") and id(el) not in terminator_ancestor_ids:
            anchors.append(el)

    # End-of-container termination is provable only when the container is
    # itself a bounded main-content region rather than the whole document.
    if strict and terminating is None and container.name in ("body", "html", "[document]"):
        raise BoundaryNotProvableError(
            "No terminating heading found and container is the whole document; "
            "cannot prove the section boundary.",
            headings_seen,
        )

    evidence = BoundaryEvidence(
        heading=start.info,
        terminating_heading=terminating.info if terminating else None,
        terminated_by="heading" if terminating else "end_of_container",
        container_description=dom_path(container) or container.name,
        all_headings_seen=headings_seen,
    )
    return SectionSlice(
        heading=start,
        terminating=terminating,
        anchors=anchors,
        evidence=evidence,
        elements=elements,
    )


def parse_container(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")
