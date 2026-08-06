"""Shared data models."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AcquisitionMode(str, enum.Enum):
    DIRECT_HTML = "direct_html"
    ALTERNATE_FIRST_PARTY_HTML = "alternate_first_party_html"
    BROWSER_RENDERED_DOM = "browser_rendered_dom"
    CHALLENGE_PAGE = "challenge_page"
    INVALID_CONTENT = "invalid_content"
    NETWORK_FAILURE = "network_failure"


class PageKind(str, enum.Enum):
    CATALOGUE_HOME = "catalogue_home"
    CATALOGUE_LIST = "catalogue_list"
    PROGRAMS_INDEX = "programs_index"
    PROGRAM_PAGE = "program_page"


class Classification(str, enum.Enum):
    INCLUDED = "included"
    EXCLUDED_MASTERS = "excluded_masters"
    EXCLUDED_DOCTORAL = "excluded_doctoral"
    EXCLUDED_PROFESSIONAL_GRADUATE = "excluded_professional_graduate"
    EXCLUDED_GRADUATE_CERTIFICATE = "excluded_graduate_certificate"
    EXCLUDED_JOINT = "excluded_joint_degree"
    EXCLUDED_DUAL = "excluded_dual_degree"
    EXCLUDED_COMBINED = "excluded_combined_ug_grad"
    EXCLUDED_PROGRESSIVE = "excluded_progressive_degree"
    EXCLUDED_MINOR = "excluded_minor"
    EXCLUDED_NOT_MINOR = "excluded_not_minor"
    EXCLUDED_CERTIFICATE = "excluded_certificate"
    EXCLUDED_NON_DEGREE = "excluded_non_degree"
    EXCLUDED_OUT_OF_SECTION = "excluded_out_of_section"
    EXCLUDED_NOT_A_PROGRAM = "excluded_not_a_program"
    MANUAL_REVIEW = "manual_review"

    @property
    def is_excluded(self) -> bool:
        return self.value.startswith("excluded_")


class ExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


@dataclass
class FetchResult:
    """Outcome of acquiring one page through any layer."""

    url: str
    final_url: str = ""
    page_kind: PageKind = PageKind.PROGRAM_PAGE
    mode: AcquisitionMode = AcquisitionMode.NETWORK_FAILURE
    http_status: int | None = None
    content_type: str | None = None
    html: str = ""
    raw_html: str = ""  # pre-render HTML when browser layer used
    elapsed_seconds: float = 0.0
    attempt: int = 1
    method: str = ""  # httpx / httpx-alternate / playwright
    challenge_detected: bool = False
    challenge_evidence: list[str] = field(default_factory=list)
    semantic_ok: bool = False
    semantic_evidence: dict = field(default_factory=dict)
    page_title: str = ""
    raw_html_sha256: str = ""
    rendered_dom_sha256: str = ""
    error: str = ""
    retrieved_at: str = field(default_factory=utcnow_iso)

    @property
    def ok(self) -> bool:
        return self.semantic_ok and self.mode in (
            AcquisitionMode.DIRECT_HTML,
            AcquisitionMode.ALTERNATE_FIRST_PARTY_HTML,
            AcquisitionMode.BROWSER_RENDERED_DOM,
        )


@dataclass
class HeadingInfo:
    text: str
    normalized: str
    level: int
    source: str  # native-h / role-heading / vendor:<name> / strong-label
    tag: str
    dom_path: str


@dataclass
class BoundaryEvidence:
    heading: HeadingInfo | None = None
    terminating_heading: HeadingInfo | None = None
    terminated_by: str = ""  # heading / end_of_container / not_found
    container_description: str = ""
    links_in_section: int = 0
    links_rejected_after_classification: int = 0
    first_included_title: str = ""
    last_included_title: str = ""
    all_headings_seen: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "undergraduate_heading_text": self.heading.text if self.heading else None,
            "undergraduate_heading_level": self.heading.level if self.heading else None,
            "undergraduate_heading_source": self.heading.source if self.heading else None,
            "undergraduate_heading_dom_path": self.heading.dom_path if self.heading else None,
            "terminating_heading_text": (
                self.terminating_heading.text if self.terminating_heading else None
            ),
            "terminating_heading_level": (
                self.terminating_heading.level if self.terminating_heading else None
            ),
            "terminated_by": self.terminated_by,
            "container_description": self.container_description,
            "links_in_section": self.links_in_section,
            "links_rejected_after_classification": self.links_rejected_after_classification,
            "first_included_title": self.first_included_title,
            "last_included_title": self.last_included_title,
            "all_headings_seen": self.all_headings_seen,
        }


@dataclass
class DiscoveredLink:
    sequence: int
    title: str
    href: str
    absolute_url: str
    canonical_url: str
    catoid: str
    poid: str
    returnto: str
    section_heading: str
    dom_path: str


@dataclass
class ClassificationResult:
    classification: Classification
    reason: str
    evidence: dict = field(default_factory=dict)
    detected_credentials: list[str] = field(default_factory=list)
    confident: bool = True


@dataclass
class CatalogueInfo:
    title: str = ""
    year: str = ""
    catoid: str = ""
    navoid: str = ""
    programs_url: str = ""
    archived: bool = False


@dataclass
class ResolutionResult:
    supplied_url: str
    resolved_url: str
    catalogue: CatalogueInfo
    method: str
    verified: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class ProgramMetadata:
    program_name: str = ""
    credential: str = ""
    school: str = ""
    catalogue_year: str = ""
    catalogue_identifier: str = ""
    program_identifier: str = ""
    source_url: str = ""
    canonical_url: str = ""
    acquisition_mode: str = ""
    retrieved_at: str = ""
    content_sha256: str = ""
    extraction_status: str = ""
    breadcrumbs: str = ""
