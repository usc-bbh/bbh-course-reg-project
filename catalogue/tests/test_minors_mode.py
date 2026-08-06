"""Minors collection mode: minors are included, degrees are recorded exclusions."""

from usc_catalog_scraper import config
from usc_catalog_scraper.classification import classify_title, reconcile_with_page_evidence
from usc_catalog_scraper.models import Classification


def _cfg(minors: bool = True) -> config.ScraperConfig:
    cfg = config.ScraperConfig()
    cfg.collect_minors = minors
    return cfg


def test_minor_is_included_in_minors_mode():
    r = classify_title("Spanish Minor", cfg=_cfg())
    assert r.classification is Classification.INCLUDED
    assert "minor" in r.reason.lower()


def test_bachelor_is_excluded_in_minors_mode_with_reason():
    r = classify_title("Accounting (BS)", cfg=_cfg())
    assert r.classification is Classification.EXCLUDED_NOT_MINOR
    assert r.evidence["undergrad_tokens"] == ["BS"]


def test_graduate_and_certificates_stay_excluded_in_minors_mode():
    assert classify_title("Mathematics (MA)", cfg=_cfg()).classification.is_excluded
    r = classify_title("Data Science Certificate", cfg=_cfg())
    assert r.classification is Classification.EXCLUDED_CERTIFICATE


def test_asia_minor_studies_still_not_a_minor():
    r = classify_title("Asia Minor Studies (BA)", cfg=_cfg())
    assert r.classification is Classification.EXCLUDED_NOT_MINOR  # a degree, not a minor


def test_manual_review_preserved_in_minors_mode():
    r = classify_title("Interdisciplinary Studies", cfg=_cfg())
    assert r.classification is Classification.MANUAL_REVIEW


def test_default_mode_unchanged():
    assert classify_title("Spanish Minor", cfg=_cfg(False)).classification is (
        Classification.EXCLUDED_MINOR
    )
    assert classify_title("Accounting (BS)", cfg=_cfg(False)).classification is (
        Classification.INCLUDED
    )


def test_reconcile_agrees_in_minors_mode():
    cfg = _cfg()
    prelim = classify_title("Spanish Minor", cfg=cfg)
    final = reconcile_with_page_evidence(prelim, "Spanish Minor", "", cfg)
    assert final.classification is Classification.INCLUDED
    assert final.evidence.get("page_agrees") is True


def test_reconcile_page_contradiction_downgrades_in_minors_mode():
    cfg = _cfg()
    prelim = classify_title("Spanish Minor", cfg=cfg)  # link looked like a minor
    final = reconcile_with_page_evidence(prelim, "Spanish (BA)", "", cfg)  # page is a degree
    assert final.classification is not Classification.INCLUDED
