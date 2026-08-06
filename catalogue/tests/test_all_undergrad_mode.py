"""Union collection mode: bachelor's degrees AND minors are both targets."""

from usc_catalog_scraper import config
from usc_catalog_scraper.classification import classify_title, reconcile_with_page_evidence
from usc_catalog_scraper.models import Classification


def _cfg() -> config.ScraperConfig:
    cfg = config.ScraperConfig()
    cfg.collect_all_undergrad = True
    return cfg


def test_bachelor_included():
    r = classify_title("Accounting (BS)", cfg=_cfg())
    assert r.classification is Classification.INCLUDED


def test_minor_included():
    r = classify_title("Spanish Minor", cfg=_cfg())
    assert r.classification is Classification.INCLUDED
    assert "minor" in r.reason.lower()


def test_emphasis_variant_included():
    r = classify_title("Civil Engineering, Building Science Emphasis (BS)", cfg=_cfg())
    assert r.classification is Classification.INCLUDED


def test_graduate_still_excluded():
    assert classify_title("Mathematics (MA)", cfg=_cfg()).classification.is_excluded
    assert classify_title("Chemistry (BS/MS)", cfg=_cfg()).classification is (
        Classification.EXCLUDED_COMBINED
    )


def test_certificates_still_excluded():
    r = classify_title("Data Science Certificate", cfg=_cfg())
    assert r.classification is Classification.EXCLUDED_CERTIFICATE


def test_manual_review_preserved():
    r = classify_title("Interdisciplinary Studies", cfg=_cfg())
    assert r.classification is Classification.MANUAL_REVIEW


def test_union_takes_precedence_over_minors_flag():
    cfg = _cfg()
    cfg.collect_minors = True
    assert classify_title("Accounting (BS)", cfg=cfg).classification is Classification.INCLUDED
    assert classify_title("Spanish Minor", cfg=cfg).classification is Classification.INCLUDED


def test_reconcile_agreement_for_both_kinds():
    cfg = _cfg()
    for title in ("Spanish Minor", "Accounting (BS)"):
        prelim = classify_title(title, cfg=cfg)
        final = reconcile_with_page_evidence(prelim, title, "", cfg)
        assert final.classification is Classification.INCLUDED, title
