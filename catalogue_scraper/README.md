# catalogue_scraper — degree-requirements scraper

Owner: Francis Ruan

**This is a different source from `catalog/`.** That module scrapes the
*Schedule of Classes* (`classes.usc.edu`) — which courses run in which term.
This module scrapes the *USC Catalogue* (`catalogue.usc.edu`) — what a degree
actually **requires**. The validator needs both: one to know what's offered,
this one to know what's needed.

## What it produces

One plain-text file per undergraduate programme for a chosen catalogue year.
For **2026-2027**: **470 files** — 207 bachelor's programmes (including emphasis
variants) and 263 minors. Master's, doctoral, joint/dual and certificate
programmes are excluded, each with a recorded reason.

Committed dataset: `data/usc_undergrad_complete_catalogue_2026_2027/`

```
programs/107_environmental_science_and_health_ba.txt   ← one file per programme
index.csv                 one row per included programme (name, credential, URL, hashes)
excluded_programs.csv     every excluded link + why (with evidence)
manual_review.csv         57 links whose credential could not be established
errors.csv / fetch_log.csv / manifest.json
```

File shape:

```
Program Name: Environmental Science and Health (BA)
Credential: BA
Program Identifier: poid=31805
Source URL: https://catalogue.usc.edu/preview_program.php?catoid=22&poid=31805
Content SHA-256: 991523b32...
Extraction Status: complete

OFFICIAL CATALOGUE CONTENT

# Environmental Science and Health (BA)
...
- BISC 120Lg General Biology: Organismal Biology and Evolution Units: 4
## Total units: 52
```

## Status

- All 470 files pass the module's own output validator; 0 contamination markers.
- Two independent runs produce byte-identical content for unchanged pages.
- 211 tests pass (including 4 real-browser integration tests).
- Data verified 2026-07-31 against the live catalogue.

## Run it

```bash
cd catalogue_scraper
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium

python -m usc_catalog_scraper run --all-undergrad --resume \
  --catalogue-year 2026-2027 --workdir ./out
```

macOS users: `macos_app/` wraps this in a double-clickable app that asks for the
year. Expect ~25–35 minutes for a full year (deliberate polite request pacing).

## Verify it

```bash
python tools/audit_corpus.py <report-dir> data/usc_undergrad_complete_catalogue_2026_2027
python -m pytest -q
```

## Read this before changing the extraction logic

`docs/ENGINEERING_REPORT.md` documents a real incident: content-region selection
was decided by a numeric score, and on programmes whose content is short relative
to the page furniture the **whole page body won by 0.3 points**, writing site
navigation into **158 of 470 files** — all of them marked
`Extraction Status: complete`. The fix makes the content region a *structural*
requirement and validates the final text before writing.

`docs/HOW_IT_WORKS_AND_HOW_TO_BUILD_IT.md` explains the design reasoning and how
to rebuild the module from scratch.

## Notes for the validator

- `manual_review.csv` (57 rows) is deliberately unresolved — those links carry no
  recognizable credential in their title. They are neither included nor excluded;
  a human decides. Please don't treat them as silently dropped.
- Requirement text is rendered plain text, not structured JSON. If the validator
  needs a machine-readable requirements shape, that is a follow-up worth agreeing
  on together — happy to add a converter.
- Respects `robots.txt`, paces requests on a single connection, and never attempts
  to defeat USC's bot protection (it hands off to a visible browser for a human).
- Runtime state (`browser_profile/`, `*.sqlite3`, `http_cookies.json`) contains
  live session and anti-bot tokens and must never be committed.
