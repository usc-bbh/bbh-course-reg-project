#!/usr/bin/env python3
"""Reproduce the container-selection defect offline and deterministically.

Fetches a known-FAIL page and a known-PASS page with the app's own HTTP layer,
saves both HTML snapshots, then runs the app's real select_main_container() and
prints every candidate's score so the winner is visible.

Usage: reproduce_container_defect.py OUTDIR
Run with the app's venv python.
"""
from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup

from usc_catalog_scraper import config
from usc_catalog_scraper.acquisition import AcquisitionOrchestrator
from usc_catalog_scraper.extraction import (
    _CANDIDATE_SELECTORS,
    _score,
    _text_len,
    clean_content,
    select_main_container,
)
from usc_catalog_scraper.models import PageKind
from usc_catalog_scraper.state import StateDB
from usc_catalog_scraper.text_renderer import render_text

CASES = [
    ("FAIL_025_astronomy_ba", "31889"),
    ("FAIL_451_spanish_minor", "31896"),
    ("PASS_001_accounting_bs", "31653"),
    ("PASS_106_environmental_engineering_bs", "32437"),
    ("FAIL_107_environmental_science_health_ba", "31805"),
]


def fetch_all(outdir: Path) -> None:
    cfg = config.ScraperConfig(workdir=outdir, delay_min=1.0, delay_max=2.0)
    work = outdir / "_repro_work"
    work.mkdir(parents=True, exist_ok=True)
    db = StateDB(work / "repro.sqlite3")
    orch = AcquisitionOrchestrator(
        cfg, db, state_dir=work, screenshots_dir=work, headed=False
    )
    try:
        for label, poid in CASES:
            snap = outdir / f"snapshot_{label}.html"
            if snap.exists() and snap.stat().st_size > 20000:
                print(f"[cached] {label}")
                continue
            url = (f"https://catalogue.usc.edu/preview_program.php?"
                   f"catoid=22&poid={poid}&returnto=9396")
            r = orch.acquire(url, PageKind.PROGRAM_PAGE, label=label)
            print(f"[fetch] {label}: mode={r.mode.value} status={r.http_status} "
                  f"bytes={len(r.html or '')}")
            if r.html:
                snap.write_text(r.html, encoding="utf-8")
    finally:
        orch.close()
        db.close()


def analyze(outdir: Path) -> None:
    cfg = config.ScraperConfig(workdir=outdir)
    print("\n" + "=" * 100)
    print("CONTAINER SELECTION SCORES  (winner = highest; +50 bonus applied to acalog labels)")
    print("=" * 100)
    for label, poid in CASES:
        snap = outdir / f"snapshot_{label}.html"
        if not snap.exists():
            print(f"\n### {label}: NO SNAPSHOT")
            continue
        html = snap.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "lxml")
        print(f"\n### {label}  (poid={poid}, html={len(html)} bytes)")
        rows = []
        for selector, slabel in _CANDIDATE_SELECTORS:
            try:
                found = list(soup.select(selector))
            except Exception:
                found = []
            for el in found[:4]:
                bonus = 50.0 if "acalog" in slabel else 0.0
                rows.append((_score(el) + bonus, f"{slabel} ({selector})",
                             el.name, _text_len(el), bonus))
        body = soup.body
        if body is not None:
            rows.append((_score(body) - 0.0, "document body fallback", "body",
                         _text_len(body), 0.0))
        rows.sort(key=lambda t: -t[0])
        for score, lab, name, tlen, bonus in rows[:6]:
            mark = "  <== WINNER" if (score, lab) == (rows[0][0], rows[0][1]) else ""
            print(f"   {score:9.1f}  <{name:6}> textlen={tlen:<7} {lab[:56]:<58}{mark}")
        # what the pipeline actually produces
        container, evidence = select_main_container(soup, cfg)
        text = render_text(clean_content(container, cfg), cfg)
        contaminated = any(s in text for s in
                           ("Skip to Navigation", "Row 1:", "University of Southern California |",
                            "Begin Responsive", "<script"))
        print(f"   selected: <{container.name}> | {evidence[:80]}")
        print(f"   rendered: {len(text)} chars | CONTAMINATED={contaminated}")
        first = next((ln for ln in text.splitlines() if ln.strip()), "")
        print(f"   first line: {first[:90]!r}")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    fetch_all(out)
    analyze(out)
