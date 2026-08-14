# Catalogue Requirements Schema

Module 2 — USC Catalogue scrape (degree/major/minor requirements). Python.

Owner: Francis Ruan

This document is the contract for the degree-requirements data consumed by the
**degree-audit engine** (Natalie) and by `validate_next_semester()`'s
prerequisite logic. If you change the scraper output, update this file in the
same PR.

`_schema_version`: **1.1**

> **Status.** Complete for 2026-2027: 470 programme text files, all passing the
> module's output validator, 0 contamination markers. Repeatability was
> measured on a 60-programme sample (60/60 byte-identical substantive content,
> see `docs/REPEATABILITY.md`) plus the 5 programmes re-acquired on 2026-08-13
> (5/5 byte-identical on an independent second fetch) — **not** across all 470.
>
> **Corrected 2026-08-13:** unit counts had been silently dropped from 58
> course lines across the 4 browser-rendered programmes. Fixed, re-scraped and
> verified — see *Known limitations* and `docs/ENGINEERING_REPORT.md`.
>
> **Scope:** this module's deliverable is the **faithfully scraped text** plus
> the CSVs accounting for every decision. Turning that text into whatever
> structured shape a consumer needs is the consumer's call — see *Who consumes
> this*.

---

## What this module is *not*

**Not** `catalog/` (Module 3). That scrapes `classes.usc.edu` — the Schedule of
Classes, i.e. what is **offered** in a term. This scrapes `catalogue.usc.edu` —
what a degree **requires**. Different site, different data, no overlap.

`catalog/README.md` already points here: *"Prerequisites are not in this data at
all. They live in the course catalogue (Module 2 / Francis's scrape)."*

## Who consumes this, and how

**1. Degree-audit engine (Natalie) — primary consumer.**
The engine categorises requirements per degree, major and minor. It reads the
`.txt` files in `data/usc_undergrad_complete_catalogue_2026_2027/programs/`
directly as its source data. This module deliberately does **not** impose a
structured requirements schema — the audit engine owns that shape. If you want a
specific JSON emitted from here instead, say so and I'll add it; the text format
below is stable enough to parse against.

**2. `validate_next_semester()` prerequisite check — secondary.**
That check is currently *"a free-text regex over `description`… explicitly
unverified"* (per `validator/README.md`), because the Schedule of Classes has no
prereq data. Prerequisite text lives in these files. Wiring it up is **not done
in this PR** — it needs Tanzil's agreement on the input shape first, since
`validate_next_semester()` takes four fixed arguments and requirements are not
one of them today.

**Not wired to anything yet.** This PR adds the data source and its documented
format. No existing module's behaviour changes.

## Source

Scraped from `catalogue.usc.edu` (`preview_program.php`), the USC Catalogue.
Runs from any network — no VPN needed — but the site is behind an AWS WAF, so
the scraper escalates plain HTTP → first-party print variant → headless Chromium
and re-syncs the rotating WAF token after each browser success.

Catalogue year is resolved from USC's own archive list, then corroborated
against the title on that catalogue's home page. `catoid` is **not** ordered by
year (2023-24 = 18, 2024-25 = 20), so it is never inferred.

Terms covered: whichever catalogue year you pass. Committed data: **2026-2027**.

## On-disk shape

```
data/usc_undergrad_complete_catalogue_2026_2027/
├── programs/NNN_name_credential.txt                   470 files
├── index.csv                one row per included programme
├── excluded_programs.csv    623 rows: every exclusion + evidence
├── manual_review.csv        57 rows: undecidable, needs a human
└── errors.csv, fetch_log.csv, manifest.json
```

## Text file shape (`programs/*.txt`)

A metadata header, the line `OFFICIAL CATALOGUE CONTENT`, then rendered content.

| Header field | Type | Notes |
|---|---|---|
| `Program Name` | string | Official catalogue title, e.g. `"Environmental Science and Health (BA)"`. Trailing `*` = Dornsife jurisdiction footnote. |
| `Credential` | string | `BA`, `BS`, `BFA`, `BM`, `BArch`, `BLA`, `BSW`, or empty for minors. |
| `Catalogue Year` | string | e.g. `"2026-2027"`. |
| `Catalogue Identifier` | string | `catoid=NN`. Not ordered by year. |
| `Program Identifier` | string | `poid=NNNNN`. **Stable join key.** |
| `Source URL` | string | Exact page scraped. |
| `Acquisition Mode` | string | `direct_html` \| `browser_rendered_dom` \| `alternate_first_party_html`. |
| `Content SHA-256` | string | Hash of the rendered content **only** (not the header). Published as `content_sha256` in `index.csv`. |
| `Extraction Status` | string | Always `complete` — a failed extraction is never written. |
| `Breadcrumbs` | string | Optional 13th line; `Return to:` context. |

Content is deterministic plain text: `#`/`##` headings, `-` course lines,
`Units: N`, `TABLE:`/`Columns:`/`Row N:` for genuine data tables, `[1]` footnotes.

## Two hashes, and which one you want

`index.csv` publishes both, and they answer different questions:

| Column | Hashes | Changes when |
|---|---|---|
| `content_sha256` | the rendered content only — identical to the file's `Content SHA-256` header | USC's programme text changes |
| `file_sha256` | the whole `.txt`, header included | **every run** — the header carries `Retrieved At` |

**To detect that a programme's requirements changed, compare `content_sha256`.**
`file_sha256` exists for integrity/resume ("is this file the one I wrote?") and
will differ between two runs even when USC changed nothing.

Before `_schema_version` 1.1, `index.csv` published the *file* hash under the
name `content_sha256`, so a consumer following the advice above saw a spurious
change on every scrape. If you pinned 1.0 and joined on that column, re-read
it: the column name now means what it says.

## Known limitations

- **Unit totals are stated inconsistently by USC.** Some pages carry an
  explicit `## Total units: N` heading; others state it only in prose, or only
  per-section, or not at all. Anything parsing this text should treat a total as
  present-or-absent, not assume it. Beware unrelated unit restrictions: e.g.
  Accounting (BS) says *"may complete a maximum of 12 units from the Marshall
  School"* — a restriction, **not** the degree total. Roughly 330 of 470 pages
  have no unambiguous programme total.
- **24 programmes have no course list at all**, and this is correct: some are
  self-designed majors (`Interdisciplinary Studies (BA)` has no fixed courses by
  design) and some are cross-reference stubs (`Nonprofits… Interdisciplinary
  Minor` is ~286 characters ending *"See complete description in the USC Price
  School of Public Policy section"*). Verified against the live pages.
- **`manual_review.csv` has 57 rows by design.** Links whose title carries no
  recognizable credential. Neither included nor excluded — a human decides.
  Please do not read them as silently dropped data.
- **Requirement *logic* is prose, not structure.** "Choose one of the
  following", `or` between two courses, footnote conditions — all preserved
  verbatim in the text, none of it turned into a machine-readable rule tree.
  A consumer must parse or human-review these for complex programmes.
- **Prerequisites are inside requirement prose**, not a separate field yet. If
  the validator wants them structured, that is a follow-up.
- **13 course lines carry no unit count, and this is correct.** Course *ranges*
  (`DANC 180-189c`, `DANC 181–189`), prose recommendations (`MATH 129 and MATH
  229 are the recommended…`), the five `EDUC 4xx –` descriptions in
  `461_sustainability…`, and `AHIS 320 Aegean Archaeology Units:` — where USC's
  own page publishes the label with no value. Verified against the live pages
  2026-08-13. Everything else has units; the validator now enforces that.
- **Catalogue text belongs to USC.** This is public-page retrieval for academic
  use. `robots.txt` disallowed paths are never requested, requests are paced on
  a single connection, and CAPTCHAs are never defeated — the scraper hands off
  to a visible browser for a human.

## Versioning

`_schema_version` 1.0 describes the **text file format** documented above: the
metadata header fields and the rendered-content conventions. A consumer parsing
these files should pin this version and **fail fast** — raise, don't silently
misread — matching the convention used by `catalog/` and `dept_clearance.json`.

Bump the minor version for additive header fields; bump major if a header field
is renamed/removed or the content rendering changes shape.

**1.1 (2026-08-13)** — additive: `index.csv` gains `file_sha256`, and
`content_sha256` now holds the content-only hash it was always named for (it
previously held the whole-file hash). The `.txt` format itself is unchanged, so
this is a minor bump; a consumer that only reads the text files is unaffected. Each file's
`Content SHA-256` lets a consumer detect that a programme's text changed even
when the format did not.

## Run it

```bash
cd catalogue_scraper
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium

# scrape a catalogue year (bachelor's + minors)
python -m usc_catalog_scraper run --all-undergrad --resume \
  --catalogue-year 2026-2027 --workdir ./out
```

~25–35 minutes for a full year (request pacing is deliberate).
`macos_app/` wraps this in a double-clickable app that asks for the year.

## Verify it

```bash
python tools/audit_corpus.py <report-dir> data/usc_undergrad_complete_catalogue_2026_2027
python -m pytest -q      # 225 tests, incl. 4 real-browser integration tests
ruff check src tests && mypy
```

`tools/` also holds the runtime analysis, before/after comparison and
repeatability checker used to validate the corpus.

## Read before changing the extraction logic

`docs/ENGINEERING_REPORT.md` — content-region selection was once decided by a
numeric score, and on programmes whose content is short relative to the page
furniture the **whole page body won by 0.3 points**, writing site navigation
into **158 of 470 files** — every one of them marked
`Extraction Status: complete`, with a valid SHA-256. The fix makes the content
region a *structural* requirement and validates the final text before writing.

The lesson generalises to the other scrapers here: **a passing hash proves
integrity, not correctness.**

The 2026-08-13 incident is the same lesson one level down. The browser layer
fetched the right page, picked the right container and wrote clean text — but
`_expand_collapsed` had clicked every acalog course toggle on the way, and an
expanded course line no longer carries its `Units: N`. 58 course lines lost
their unit counts across 4 files while every gate passed, because no gate
asserted that units *survived* extraction. **Validate the fields a consumer
actually reads, not just the shape of the text.**

`docs/HOW_IT_WORKS_AND_HOW_TO_BUILD_IT.md` — design reasoning and a rebuild guide.
