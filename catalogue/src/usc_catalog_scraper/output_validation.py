"""Validation of the FINAL extracted text, immediately before it is written.

Why this module exists (incident 2026-07-30)
-------------------------------------------
`semantic_validation.validate_page()` validates the fetched *page*: it proves
we received the program page we asked for. It says nothing about what the
extractor then pulled out of that page. When container selection picked the
whole document (see extraction.ContentRegionNotFound), the rendered text was
site navigation, the page header table and literal <script> markup — yet every
page-level check passed, and the only text-level gate in the pipeline was
"more than 200 characters". 158 of 470 outputs were written as
`Extraction Status: complete` while containing no program requirements at all.

These checks run on the text that is about to become the file, so a failed
extraction can no longer be saved as a valid result.

Thresholds are derived from the audited 470-file corpus (majors + minors,
2026-2027): every one of the 276 clean files began with its own program title
as a markdown heading and contained course/unit content; every one of the 158
contaminated files failed both of those checks. Legitimately short programs
pass on semantic evidence (title heading + course/unit content), never on
length alone.
"""

from __future__ import annotations

import re
from collections import Counter

# Literal contamination fingerprints, copied verbatim from the defective
# outputs. Any single hit is fatal: none of these strings can occur in a
# correctly extracted program body.
FATAL_TEXT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"Skip to Navigation", "site skip-link (page shell captured as content)"),
    # NOTE: a bare "Row N:" label is NOT a defect — the renderer emits it for
    # genuine course-requirement tables (tests/fixtures/program_tables.html).
    # The real fingerprint is the SITE HEADER appearing inside such a row.
    (r"\|\s*University of Southern California", "site header table cell"),
    (r"Begin Responsive|End Responsive", "acalog responsive layout build markers"),
    (r"<\s*/?\s*script\b", "literal <script> markup in text"),
    (
        r"<\s*(?:div|span|td|tr|table|ul|ol|li|img|link|style|body|html|meta|iframe)\b[^>]*>",
        "literal HTML markup in text",
    ),
    (r"(?:\bLoading\.\.\.|\bPlease wait\b|\bJust a moment)", "loading placeholder"),
    (
        r"(?:ReferenceError|TypeError:|Uncaught |undefined is not a function)",
        "JavaScript error text",
    ),
    (
        r"(?:verify you are human|Pardon our interruption|Request unsuccessful|Access Denied)",
        "bot-wall / access-denied text",
    ),
    (r"Courses\s+Programs\s+School", "navigation menu run-on"),
)

COURSE_CODE_RE = re.compile(r"\b[A-Z]{2,5}\s\d{3}[A-Za-z]{0,3}\b")
UNITS_RE = re.compile(r"\bUnits?:\s*\d|\bTotal units\b", re.I)
# Catalogue section headings / vocabulary. A few legitimate programmes are
# prose-only and list no courses at all — e.g. "Interdisciplinary Studies (BA)",
# a self-designed major whose page describes admission, an academic contract and
# restrictions instead of a fixed course list. That is a valid extraction, so
# course/unit evidence is not required when the body carries real catalogue
# section structure. Contamination is caught independently: all 158 defective
# files failed the title-heading test, which no clean file failed.
SECTION_HEADING_RE = re.compile(r"^#{2,4}\s+\S", re.M)
# Cross-reference stub pages. USC publishes some interdisciplinary minors as a
# short description that deliberately points elsewhere, e.g. poid=32395
# "Nonprofits, Philanthropy and Volunteerism Interdisciplinary Minor" is 286
# characters ending "See complete description in the USC Price School of Public
# Policy section." Verified against the live pages 2026-07-30: the extraction is
# complete — the page really is that short. Such a body must pass.
CROSS_REFERENCE_RE = re.compile(
    r"\bSee\b[^.\n]{0,140}?\b(?:School|College|section|Department|Division|catalogue)\b",
    re.I,
)
PROGRAMME_SECTION_WORDS = (
    "admission",
    "requirement",
    "restriction",
    "advisement",
    "prerequisite",
    "elective",
    "curriculum",
    "thesis",
    "total units",
    "course work",
)

# Corpus-derived floors (majors + minors, 2026-2027, 276 clean files).
#
# The smallest CLEAN body observed was 971 characters (283_documentary_minor)
# and clean bodies always carried both a title heading and course/unit content.
# Length is therefore NOT used to judge a programme that shows semantic
# evidence: a terse but complete minor must pass. Length is only a backstop for
# extractions so short they cannot be a programme at all — set well below the
# observed clean minimum so it can never reject real content.
MIN_BODY_CHARS_WITHOUT_SEMANTICS = 971  # observed clean minimum
ABSOLUTE_MIN_BODY_CHARS = 200  # backstop; ~5x below the clean minimum
MAX_REPEATED_SENTENCE = 3


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def max_repeated_sentence(text: str) -> tuple[int, str]:
    """Largest repeat count among substantial sentences (duplication signal).

    Whole-page captures duplicate the programme blurb once per expanded
    rowspan/colspan cell; the 107 defect repeated one sentence 8 times.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 80]
    if not sentences:
        return 1, ""
    key, n = Counter(_norm(s) for s in sentences).most_common(1)[0]
    return n, key[:140]


def title_heading_present(text: str, program_name: str) -> bool:
    """Does the body open with the programme's own title as a heading?

    Clean acalog extractions always start '# <Program Name>'. Compared on the
    credential-stripped stem so '(BA)*' footnote markers and minor title
    variations do not cause false negatives.
    """
    if not program_name:
        return bool(re.search(r"^#{1,3}\s+\S", text, re.M))
    stem = re.split(r"\s*\(", program_name)[0].strip()
    stem = re.sub(r"[*†‡]+$", "", stem).strip()
    if not stem:
        return bool(re.search(r"^#{1,3}\s+\S", text, re.M))
    # Prefix match on the heading's own text, NOT a substring search: for a short
    # programme name like "Art (BA)" a substring test matches "## Departmental
    # Requirements" ("dep-ART-mental") and "## Chart of Accounts", which would let
    # a body with no title heading of its own pass the single most reliable
    # contamination check.
    target = _norm(stem)
    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        heading = _norm(line.lstrip("#"))
        if heading.startswith(target):
            return True
    return False


def validate_extracted_text(
    text: str,
    program_name: str = "",
    *,
    min_chars: int = ABSOLUTE_MIN_BODY_CHARS,
) -> tuple[bool, dict]:
    """Return (ok, evidence) for text that is about to be written to disk.

    Fails closed: any fatal fingerprint, a missing title heading, absent
    course/unit content, or heavy duplication rejects the extraction.
    """
    evidence: dict = {}
    body = (text or "").strip()
    evidence["body_chars"] = len(body)
    if not body:
        evidence["reasons"] = ["empty_extraction"]
        return False, evidence

    fatal: list[str] = []
    for pattern, description in FATAL_TEXT_PATTERNS:
        flags = re.M if pattern.startswith("^") else 0
        m = re.search(pattern, body, flags)
        if m:
            start = max(0, m.start() - 50)
            fatal.append(description)
            evidence.setdefault("fatal_excerpts", []).append(
                f"{description}: …{body[start : m.end() + 50]}…".replace("\n", " ⏎ ")
            )
    evidence["fatal_patterns"] = fatal

    course_codes = len(COURSE_CODE_RE.findall(body))
    units = len(UNITS_RE.findall(body))
    has_title = title_heading_present(body, program_name)
    section_headings = len(SECTION_HEADING_RE.findall(body))
    low_body = body.casefold()
    section_words = sum(1 for w in PROGRAMME_SECTION_WORDS if w in low_body)
    # A prose-only programme page: no course list, but unmistakably a catalogue
    # programme description carrying its own sections.
    has_section_structure = section_headings >= 2 or section_words >= 3
    # A stub must also END coherently. Without this, a TRUNCATED extraction that
    # happens to contain a "See the X Department" phrase would be waved through
    # by the stub allowance (self-review finding 2026-07-31).
    last = next((ln.strip() for ln in reversed(body.splitlines()) if ln.strip()), "")
    ends_cleanly = last.endswith((".", "!", "?", "---", ":")) or last.startswith("#")
    is_stub = bool(CROSS_REFERENCE_RE.search(body)) and len(body) >= min_chars and ends_cleanly
    repeats, repeat_txt = max_repeated_sentence(body)
    evidence.update(
        {
            "course_code_count": course_codes,
            "units_mentions": units,
            "title_heading_present": has_title,
            "section_heading_count": section_headings,
            "programme_section_words": section_words,
            "prose_only_programme": (course_codes == 0 and units == 0 and has_section_structure),
            "cross_reference_stub": is_stub,
            "body_ends_cleanly": ends_cleanly,
            "max_repeated_sentence_count": repeats,
        }
    )
    if repeats >= MAX_REPEATED_SENTENCE:
        evidence["repeated_sentence"] = repeat_txt

    reasons: list[str] = []
    if fatal:
        reasons.append("contaminated_text:" + "; ".join(fatal))
    if not has_title:
        reasons.append("no_program_title_heading_in_body")
    if course_codes == 0 and units == 0 and not has_section_structure and not is_stub:
        reasons.append("no_course_or_unit_content_and_no_section_structure")
    # Semantic evidence (own title heading + either course/unit content or real
    # catalogue section structure) is what makes a body valid. Only bodies
    # lacking that evidence are judged on length.
    has_semantics = has_title and (
        course_codes > 0 or units > 0 or has_section_structure or is_stub
    )
    if len(body) < min_chars:
        reasons.append(f"body_under_{min_chars}_chars")
    elif not has_semantics and len(body) < MIN_BODY_CHARS_WITHOUT_SEMANTICS:
        reasons.append(f"weak_semantics_and_body_under_{MIN_BODY_CHARS_WITHOUT_SEMANTICS}_chars")
    evidence["has_semantic_evidence"] = has_semantics
    if repeats >= MAX_REPEATED_SENTENCE:
        reasons.append(f"duplicated_sentence_x{repeats}")

    evidence["reasons"] = reasons
    evidence["ok_reason"] = (
        "programme title heading + course/unit content, no contamination"
        if not reasons
        else "; ".join(reasons)
    )
    return (not reasons), evidence
