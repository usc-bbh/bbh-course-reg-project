"""Program classification: standalone undergraduate degrees in, everything else out.

Token-aware: credential acronyms match only as whole tokens with correct case
inside a structured credential field (trailing parenthesized group or trailing
comma segment). "MS" inside an ordinary word or prose never matches.
"""

from __future__ import annotations

import html as html_module
import re

from usc_catalog_scraper import config
from usc_catalog_scraper.models import Classification, ClassificationResult

DOCTORAL_TOKENS = {"PhD", "EdD", "DMA", "DSW", "DNP", "OTD", "AuD", "DrPH"}
PROFESSIONAL_TOKENS = {"JD", "LLM", "PharmD", "DDS", "MD", "DPT"}

_TRAILING_FOOTNOTE = re.compile(r"[\s*†‡+^]+$")
_TOKEN_SPLIT = re.compile(r"(?i)\s+and\s+|[\s/,+&]+")


def normalize_title(title: str) -> str:
    title = html_module.unescape(title or "")
    title = title.replace("’", "'").replace(" ", " ")
    return re.sub(r"\s+", " ", title).strip()


def strip_footnote_markers(title: str) -> str:
    return _TRAILING_FOOTNOTE.sub("", title).strip()


def pop_trailing_paren_groups(title: str) -> tuple[str, list[str]]:
    """Return (base_title, groups) where groups are rightmost-first trailing
    parenthesized segments: "Design (Track A) (BS)*" -> ("Design", ["BS", "Track A"])."""
    t = strip_footnote_markers(title)
    groups: list[str] = []
    while t.endswith(")"):
        i = t.rfind("(")
        if i < 0:
            break
        groups.append(t[i + 1 : -1].strip())
        t = strip_footnote_markers(t[:i]).strip()
    return t, groups


def parse_credential_tokens(field: str) -> tuple[list[str], list[str], list[str]]:
    """Return (undergrad_tokens, grad_tokens, unknown_tokens) from a credential field."""
    ug: list[str] = []
    grad: list[str] = []
    unknown: list[str] = []
    low = field.lower()
    for pat in config.UNDERGRAD_CREDENTIAL_PHRASES:
        m = re.search(pat, low)
        if m:
            ug.append(m.group(0))
    for pat in config.GRADUATE_CREDENTIAL_PHRASES:
        m = re.search(pat, low)
        if m:
            grad.append(m.group(0))
    for raw in _TOKEN_SPLIT.split(field):
        tok = raw.strip(" .:;()[]")
        if not tok:
            continue
        if tok in config.UNDERGRAD_CREDENTIAL_TOKENS:
            ug.append(tok)
        elif tok in config.GRADUATE_CREDENTIAL_TOKENS:
            grad.append(tok)
        else:
            unknown.append(tok)
    return ug, grad, unknown


def _is_credential_group(group: str) -> bool:
    ug, grad, _ = parse_credential_tokens(group)
    return bool(ug or grad)


_PAREN_GROUP_RE = re.compile(r"\(([^()]{1,40})\)")


def scan_all_credential_tokens(title: str) -> tuple[list[str], list[str], list[str]]:
    """Tokens from EVERY parenthesized credential group, plus a comma tail.

    A composite like "Chemistry (BS) / Chemistry (MS)" hides the BS from the
    trailing-field parser; scanning all groups lets combined programs be
    excluded under the correct category with full evidence.
    """
    ug: list[str] = []
    grad: list[str] = []
    groups: list[str] = []
    plain = strip_footnote_markers(normalize_title(title))
    for raw in _PAREN_GROUP_RE.findall(plain):
        group = raw.strip()
        if _is_credential_group(group):
            groups.append(group)
            u, g, _ = parse_credential_tokens(group)
            ug.extend(u)
            grad.extend(g)
    if not groups and "," in plain and not plain.endswith(")"):
        _head, tail = plain.rsplit(",", 1)
        tail = tail.strip()
        if _is_credential_group(tail):
            groups.append(tail)
            u, g, _ = parse_credential_tokens(tail)
            ug.extend(u)
            grad.extend(g)
    return ug, grad, groups


def extract_credential_field(title: str) -> tuple[str, str]:
    """Return (base_title_without_credential, credential_field). Empty field if none.

    Recognized structures, in order: trailing parenthesized group(s); a trailing
    comma segment ("Accounting, BS"). Prose is never scanned for acronyms.
    """
    base, groups = pop_trailing_paren_groups(title)
    for g in groups:
        if _is_credential_group(g):
            return base, g
    plain = strip_footnote_markers(title)
    if "," in plain and not plain.endswith(")"):
        head, tail = plain.rsplit(",", 1)
        if _is_credential_group(tail.strip()):
            return head.strip(), tail.strip()
    return plain, ""


def _grad_exclusion_for(tokens: list[str]) -> Classification:
    toks = set(tokens)
    if toks & DOCTORAL_TOKENS or any("doctor" in t.lower() for t in tokens):
        return Classification.EXCLUDED_DOCTORAL
    if toks & PROFESSIONAL_TOKENS:
        return Classification.EXCLUDED_PROFESSIONAL_GRADUATE
    return Classification.EXCLUDED_MASTERS


def _search_any(patterns: tuple[str, ...], text: str) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(0)
    return None


def classify_title(
    title: str,
    section_heading: str = "",
    category_label: str = "",
    cfg: config.ScraperConfig | None = None,
) -> ClassificationResult:
    """Classify from the official program title (+ optional catalogue category label).

    Priority: official title structure > explicit credential field > category label.
    Uncertain results go to manual review, never silently dropped.
    """
    if cfg is not None and cfg.collect_all_undergrad:
        return _as_undergrad_union(
            _classify_title_bachelor(title, section_heading, category_label, cfg)
        )
    if cfg is not None and cfg.collect_minors:
        return _as_minors_target(
            _classify_title_bachelor(title, section_heading, category_label, cfg)
        )
    return _classify_title_bachelor(title, section_heading, category_label, cfg)


def _as_undergrad_union(result: ClassificationResult) -> ClassificationResult:
    """Union collection: bachelor's degrees stay included AND minors become
    included; graduate degrees, certificates, joint/dual programs and manual
    reviews keep their original verdicts, reasons and evidence."""
    if result.classification is Classification.EXCLUDED_MINOR:
        return ClassificationResult(
            Classification.INCLUDED,
            f"minor designation is a collection target ({result.reason})",
            result.evidence,
            result.detected_credentials or ["Minor"],
            result.confident,
        )
    return result


def _as_minors_target(result: ClassificationResult) -> ClassificationResult:
    """Invert the bachelor-centric verdict for a minors collection: minors are
    the target; bachelor's degrees become the recorded exclusions. All other
    verdicts (graduate, joint, certificate, manual review) keep their original
    reasons and evidence."""
    if result.classification is Classification.EXCLUDED_MINOR:
        return ClassificationResult(
            Classification.INCLUDED,
            f"minor designation is the collection target ({result.reason})",
            result.evidence,
            result.detected_credentials or ["Minor"],
            result.confident,
        )
    if result.classification is Classification.INCLUDED:
        return ClassificationResult(
            Classification.EXCLUDED_NOT_MINOR,
            f"standalone degree, not a minor ({result.reason})",
            result.evidence,
            result.detected_credentials,
            result.confident,
        )
    return result


def _classify_title_bachelor(
    title: str,
    section_heading: str = "",
    category_label: str = "",
    cfg: config.ScraperConfig | None = None,
) -> ClassificationResult:
    """Bachelor-centric verdict (the original 1.0.0 rules, unchanged)."""
    original = normalize_title(title)
    label = normalize_title(category_label)
    combined_context = f"{original} | {label}".strip(" |")
    low = combined_context.lower()

    evidence: dict = {"title": original}
    if section_heading:
        evidence["section_heading"] = section_heading
    if label:
        evidence["category_label"] = label

    hit = _search_any(config.PROGRESSIVE_PATTERNS, low)
    if hit:
        evidence["match"] = hit
        return ClassificationResult(
            Classification.EXCLUDED_PROGRESSIVE,
            f"progressive degree designation: {hit!r}",
            evidence,
        )

    base, field = extract_credential_field(original)
    ug_field, grad_field, unknown = parse_credential_tokens(field) if field else ([], [], [])
    all_ug, all_grad, all_groups = scan_all_credential_tokens(original)
    ug = list(dict.fromkeys(ug_field + all_ug))
    grad = list(dict.fromkeys(grad_field + all_grad))
    detected = ug + grad
    evidence["credential_field"] = field
    if all_groups:
        evidence["credential_groups"] = all_groups
    evidence["undergrad_tokens"] = ug
    evidence["graduate_tokens"] = grad
    if unknown:
        evidence["unparsed_tokens"] = unknown

    # Minor designation is judged on the credential-stripped base title so a
    # bachelor program like "Asia Minor Studies (BA)" is never excluded.
    hit = _search_any(config.MINOR_PATTERNS, base.lower()) or _search_any(
        config.MINOR_PATTERNS, label.lower()
    )
    if hit:
        evidence["match"] = hit
        return ClassificationResult(
            Classification.EXCLUDED_MINOR, f"minor designation: {hit!r}", evidence
        )

    hit = _search_any(config.CERTIFICATE_PATTERNS, low)
    if hit:
        evidence["match"] = hit
        cls = (
            Classification.EXCLUDED_GRADUATE_CERTIFICATE
            if "graduate certificate" in low
            else Classification.EXCLUDED_CERTIFICATE
        )
        return ClassificationResult(cls, f"certificate designation: {hit!r}", evidence)

    hit = _search_any(config.JOINT_PATTERNS, low)
    if hit:
        evidence["match"] = hit
        return ClassificationResult(
            Classification.EXCLUDED_JOINT, f"joint degree designation: {hit!r}", evidence, detected
        )
    hit = _search_any(config.DUAL_PATTERNS, low)
    if hit:
        evidence["match"] = hit
        return ClassificationResult(
            Classification.EXCLUDED_DUAL, f"dual degree designation: {hit!r}", evidence, detected
        )
    hit = _search_any(config.COMBINED_DEGREE_PATTERNS, low)
    if hit:
        evidence["match"] = hit
        return ClassificationResult(
            Classification.EXCLUDED_COMBINED,
            f"combined undergraduate/graduate designation: {hit!r}",
            evidence,
            detected,
        )
    hit = _search_any(config.NON_DEGREE_PATTERNS, low)
    if hit:
        evidence["match"] = hit
        return ClassificationResult(
            Classification.EXCLUDED_NON_DEGREE, f"non-degree designation: {hit!r}", evidence
        )

    if ug and grad:
        return ClassificationResult(
            Classification.EXCLUDED_COMBINED,
            f"credential groups {all_groups or [field]} award both undergraduate "
            f"({ug}) and graduate ({grad}) credentials",
            evidence,
            detected,
        )
    if grad:
        cls = _grad_exclusion_for(grad)
        return ClassificationResult(
            cls, f"graduate credential(s) {grad} in credential field {field!r}", evidence, detected
        )
    if ug:
        return ClassificationResult(
            Classification.INCLUDED,
            f"undergraduate-only credential(s) {ug} in credential field {field!r}",
            evidence,
            detected,
        )

    # No structured credential field. Spelled-out degree in the title itself?
    title_low = original.lower()
    ug_phrase = _search_any(config.UNDERGRAD_CREDENTIAL_PHRASES, title_low)
    grad_phrase = _search_any(config.GRADUATE_CREDENTIAL_PHRASES, title_low)
    if ug_phrase and not grad_phrase:
        evidence["match"] = ug_phrase
        return ClassificationResult(
            Classification.INCLUDED,
            f"spelled-out undergraduate degree: {ug_phrase!r}",
            evidence,
            [ug_phrase],
        )
    if grad_phrase and not ug_phrase:
        evidence["match"] = grad_phrase
        return ClassificationResult(
            _grad_exclusion_for([grad_phrase]),
            f"spelled-out graduate degree: {grad_phrase!r}",
            evidence,
            [grad_phrase],
        )
    if ug_phrase and grad_phrase:
        evidence["match"] = f"{ug_phrase} + {grad_phrase}"
        return ClassificationResult(
            Classification.EXCLUDED_COMBINED,
            "title names both undergraduate and graduate degrees",
            evidence,
            [ug_phrase, grad_phrase],
        )

    return ClassificationResult(
        Classification.MANUAL_REVIEW,
        "no recognizable credential in official title; needs human confirmation",
        evidence,
        [],
        confident=False,
    )


def reconcile_with_page_evidence(
    preliminary: ClassificationResult,
    page_title: str,
    breadcrumb: str = "",
    cfg: config.ScraperConfig | None = None,
) -> ClassificationResult:
    """Cross-check a link-title classification against the program page's own
    official title/breadcrumb. Contradictions are downgraded conservatively."""
    if not page_title:
        return preliminary
    page_result = classify_title(page_title, category_label=breadcrumb, cfg=cfg)
    if page_result.classification == preliminary.classification:
        merged = dict(preliminary.evidence)
        merged["page_title"] = normalize_title(page_title)
        merged["page_agrees"] = True
        return ClassificationResult(
            preliminary.classification,
            preliminary.reason,
            merged,
            preliminary.detected_credentials or page_result.detected_credentials,
            preliminary.confident,
        )
    merged = dict(preliminary.evidence)
    merged["page_title"] = normalize_title(page_title)
    merged["page_classification"] = page_result.classification.value
    merged["page_reason"] = page_result.reason
    # Page evidence that the program is NOT a standalone undergraduate degree
    # overrides an optimistic link-title read when the page parse is confident.
    if (
        preliminary.classification is Classification.INCLUDED
        and page_result.classification.is_excluded
        and page_result.confident
    ):
        return ClassificationResult(
            page_result.classification,
            f"program page contradicts link title: {page_result.reason}",
            merged,
            page_result.detected_credentials,
        )
    # Page says included but link said excluded/unknown -> keep cautious path.
    if page_result.classification is Classification.INCLUDED and (
        preliminary.classification is Classification.MANUAL_REVIEW
    ):
        return ClassificationResult(
            Classification.INCLUDED,
            f"program page provides credential evidence: {page_result.reason}",
            merged,
            page_result.detected_credentials,
        )
    return ClassificationResult(
        Classification.MANUAL_REVIEW,
        "link title and program page disagree; needs human confirmation",
        merged,
        page_result.detected_credentials or preliminary.detected_credentials,
        confident=False,
    )
