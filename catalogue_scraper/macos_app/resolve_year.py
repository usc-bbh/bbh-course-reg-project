#!/usr/bin/env python3
"""Resolve a chosen catalogue year (catoid) to its Programs page URL.

Runs inside the app's venv. Uses the scraper's own acquisition orchestrator
(direct HTTP with browser fallback) and the same official-navigation logic as
the latest-catalogue resolver: index.php?catoid=N must corroborate the year in
its title, and its navigation supplies the "Programs, Minors and Certificates"
navoid. Prints the programs URL on the last stdout line; exits non-zero with a
message on stderr if the year cannot be verified.
"""

import sys
from pathlib import Path

from usc_catalog_scraper import config
from usc_catalog_scraper.acquisition import AcquisitionOrchestrator
from usc_catalog_scraper.catalogue_resolver import (
    TITLE_RE,
    find_programs_navoid,
    parse_catalog_list,
)
from usc_catalog_scraper.logging_config import setup_logging
from usc_catalog_scraper.models import PageKind
from usc_catalog_scraper.state import StateDB


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: resolve_year.py CATOID YEAR WORKDIR", file=sys.stderr)
        return 2
    catoid, year, workdir = sys.argv[1], sys.argv[2], sys.argv[3]
    setup_logging(False)
    work = Path(workdir) / "year_resolution"
    work.mkdir(parents=True, exist_ok=True)
    cfg = config.ScraperConfig(workdir=Path(workdir))
    db = StateDB(work / "resolve.sqlite3")
    orch = AcquisitionOrchestrator(
        cfg, db, state_dir=work, screenshots_dir=work / "screenshots", headed=False
    )
    try:
        if catoid == "auto":
            list_url = f"https://{config.CATALOGUE_HOST}/misc/catalog_list.php?catoid=22"
            listing = orch.acquire(list_url, PageKind.CATALOGUE_LIST, label="year_list")
            if not listing.ok:
                print("could not load the official catalogue list", file=sys.stderr)
                return 1
            entries = parse_catalog_list(listing.html, listing.final_url or list_url)
            matches = [e for e in entries if e.year == year]
            if not matches:
                known = sorted({e.year for e in entries if e.year}, reverse=True)
                print(f"year {year!r} not in the official list; known: {known}", file=sys.stderr)
                return 1
            catoid = matches[0].catoid
        index_url = f"https://{config.CATALOGUE_HOST}/index.php?catoid={catoid}"
        result = orch.acquire(index_url, PageKind.CATALOGUE_HOME, label="year_home")
        if not result.ok:
            print(f"could not load {index_url} ({result.mode.value})", file=sys.stderr)
            return 1
        m = TITLE_RE.search(result.html)
        page_year = f"{m.group(1)}-{m.group(2)}" if m else None
        if page_year != year:
            print(
                f"catalogue home page year {page_year!r} does not match requested {year!r}",
                file=sys.stderr,
            )
            return 1
        navoid = find_programs_navoid(result.html, result.final_url or index_url, catoid)
        if not navoid:
            print("Programs, Minors and Certificates link not found", file=sys.stderr)
            return 1
        print(f"https://{config.CATALOGUE_HOST}/content.php?catoid={catoid}&navoid={navoid}")
        return 0
    finally:
        orch.close()
        db.close()


if __name__ == "__main__":
    sys.exit(main())
