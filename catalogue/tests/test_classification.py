"""Classification tests: inclusion, exclusion, token awareness, page reconciliation."""

import pytest

from usc_catalog_scraper.classification import (
    classify_title,
    extract_credential_field,
    parse_credential_tokens,
    reconcile_with_page_evidence,
)
from usc_catalog_scraper.models import Classification, ClassificationResult

C = Classification


@pytest.mark.parametrize(
    "title",
    [
        "Philosophy (BA)",
        "Accounting (BS)",
        "Design (BFA)",
        "Music Performance (BM)",
        "Architecture (BArch)",
        "Landscape Architecture (BLA)",
        "Social Work (BSW)",
        "Media Arts and Practice (BA)*",
        "Civil Engineering (Building Science) (BS)",
    ],
)
def test_bachelor_only_included(title):
    result = classify_title(title)
    assert result.classification is C.INCLUDED, result.reason


@pytest.mark.parametrize(
    "title",
    [
        "Economics/Mathematics (BA)",
        "Computer Science and Business Administration (BS)*",
        "Health and Human Sciences (BS)",
        "Philosophy, Politics and Law (BA)",
    ],
)
def test_interdisciplinary_bachelor_included(title):
    """Slashes, ampersands, 'and' combinations never exclude a bachelor-only title."""
    result = classify_title(title)
    assert result.classification is C.INCLUDED, result.reason


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Mathematics (MA)", C.EXCLUDED_MASTERS),
        ("Computer Science (MS)", C.EXCLUDED_MASTERS),
        ("Business Administration (MBA)", C.EXCLUDED_MASTERS),
        ("Accounting (MAcc)", C.EXCLUDED_MASTERS),
        ("Film and Television Production (MFA)", C.EXCLUDED_MASTERS),
        ("Public Health (MPH)", C.EXCLUDED_MASTERS),
        ("Chemistry (PhD)", C.EXCLUDED_DOCTORAL),
        ("Education (EdD)", C.EXCLUDED_DOCTORAL),
        ("Musical Arts (DMA)", C.EXCLUDED_DOCTORAL),
        ("Law (JD)", C.EXCLUDED_PROFESSIONAL_GRADUATE),
        ("Pharmacy (PharmD)", C.EXCLUDED_PROFESSIONAL_GRADUATE),
        ("Physical Therapy (DPT)", C.EXCLUDED_PROFESSIONAL_GRADUATE),
        ("Medicine (MD)", C.EXCLUDED_PROFESSIONAL_GRADUATE),
    ],
)
def test_graduate_and_professional_excluded(title, expected):
    result = classify_title(title)
    assert result.classification is expected, result.reason


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Spanish Minor", C.EXCLUDED_MINOR),
        ("Artificial Intelligence Applications Minor", C.EXCLUDED_MINOR),
        ("Blockchain Certificate", C.EXCLUDED_CERTIFICATE),
        ("Graduate Certificate in Data Science", C.EXCLUDED_GRADUATE_CERTIFICATE),
        ("Progressive Degree Program in Economics", C.EXCLUDED_PROGRESSIVE),
        ("Chemistry (BS/MS)", C.EXCLUDED_COMBINED),
        ("Accounting (BS/MAcc)", C.EXCLUDED_COMBINED),
        ("Engineering (BS) and Business (MBA) Joint Degree", C.EXCLUDED_JOINT),
        ("JD/MBA Dual Degree", C.EXCLUDED_DUAL),
        ("Combined Bachelor's and Master's in Occupational Science", C.EXCLUDED_COMBINED),
        ("Bachelor of Science/Master of Science, Computer Science", C.EXCLUDED_COMBINED),
    ],
)
def test_non_standalone_excluded(title, expected):
    result = classify_title(title)
    assert result.classification is expected, result.reason


def test_combined_major_single_bachelor_is_included():
    """A 'combined major' that awards one bachelor's degree stays included."""
    result = classify_title("Economics and Data Science Combined Major (BS)")
    assert result.classification is C.INCLUDED, result.reason


@pytest.mark.parametrize(
    "title",
    [
        "Marine Systems Engineering (BS)",  # 'MS' inside words must not match
        "Museum Studies (BA)",
        "Mathematics of Systems (BS)",
        "Human Development and Aging (BS)",
    ],
)
def test_ms_substring_never_matches_inside_words(title):
    result = classify_title(title)
    assert result.classification is C.INCLUDED, result.reason
    assert not any(t == "MS" for t in result.evidence.get("graduate_tokens", []))


def test_spelled_out_bachelor_included():
    result = classify_title("Bachelor of Science in Biomedical Engineering")
    assert result.classification is C.INCLUDED


def test_spelled_out_master_excluded():
    result = classify_title("Master of Public Administration")
    assert result.classification is C.EXCLUDED_MASTERS


def test_no_credential_goes_to_manual_review():
    result = classify_title("Interdisciplinary Studies")
    assert result.classification is C.MANUAL_REVIEW
    assert result.confident is False


def test_footnote_asterisk_stripped():
    base, field = extract_credential_field("Media Arts and Practice (BA)*")
    assert field == "BA"
    assert base == "Media Arts and Practice"


def test_concentration_parens_not_credential():
    base, field = extract_credential_field(
        "Civil Engineering (Advanced Design and Construction Technology) (MS)"
    )
    assert field == "MS"
    assert "Advanced Design" in base or base.startswith("Civil Engineering")


def test_comma_style_credential():
    base, field = extract_credential_field("Accounting, BS")
    assert field == "BS"
    assert base == "Accounting"


def test_token_parse_case_sensitivity():
    ug, grad, _unknown = parse_credential_tokens("BS/MS")
    assert ug == ["BS"] and grad == ["MS"]
    ug, grad, _unknown = parse_credential_tokens("bs and ms")
    assert not ug and not grad  # lowercase acronyms are not credentials


def test_reconcile_page_contradiction_downgrades_inclusion():
    prelim = ClassificationResult(C.INCLUDED, "undergraduate-only credential(s) ['BS']", {})
    final = reconcile_with_page_evidence(prelim, "Chemistry (BS/MS)")
    assert final.classification is C.EXCLUDED_COMBINED
    assert "page" in final.reason


def test_reconcile_page_confirms_manual_review_to_included():
    prelim = ClassificationResult(
        C.MANUAL_REVIEW, "no recognizable credential", {}, confident=False
    )
    final = reconcile_with_page_evidence(prelim, "Interdisciplinary Studies (BA)")
    assert final.classification is C.INCLUDED


def test_reconcile_agreement_keeps_classification():
    prelim = ClassificationResult(C.INCLUDED, "ok", {})
    final = reconcile_with_page_evidence(prelim, "Philosophy (BA)")
    assert final.classification is C.INCLUDED
    assert final.evidence.get("page_agrees") is True
