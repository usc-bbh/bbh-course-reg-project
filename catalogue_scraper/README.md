# Catalogue Requirements Schema

Module 2 — USC Catalogue scrape (degree/major/minor requirements). Python.

Owner: Francis Ruan

This document is the contract for the degree-requirements data consumed by the
**degree-audit engine** (Natalie) and by `validate_next_semester()`'s
prerequisite logic. If you change the scraper output, update this file in the
same PR.

`_schema_version`: **1.0** — text output is stable; the **JSON shape is
PROPOSED** and needs the audit-engine owner's sign-off (see *Status*).

> **Status.** The 470-file text corpus is complete and verified for 2026-2027.
> The structured JSON (`data/requirements_json_2026_2027/`) is generated from it
> by `tools/to_requirements_json.py` and is **v1.0 proposed, not agreed** —
> field names are a starting point for Natalie's engine, not a settled contract.
> Two known coverage gaps are stated honestly under *Known limitations*:
> **332 of 470** programmes do not state a total unit count in a form that can
> be read unambiguously, and **23** are prose-only or cross-reference stubs with
> no course list at all.

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
per-programme JSON in `data/requirements_json_2026_2027/`: one file per
programme plus `programmes_index.json`. The `.txt` files remain the source of
record — every JSON course entry carries the exact `source_line` it came from,
so any parse can be traced back and disputed rather than trusted blindly.

**2. `validate_next_semester()` prerequisite check — secondary.**
That check is currently *"a free-text regex over `description`… explicitly
unverified"* (per `validator/README.md`), because the Schedule of Classes has no
prereq data. Prerequisite text lives in these files. Wiring it up is **not done
in this PR** — it needs Tanzil's agreement on the input shape first, since
`validate_next_semester()` takes four fixed arguments and requirements are not
one of them today.

**Not wired to anything yet.** This PR adds the data source and the converter.
No existing module's behaviour changes.

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
data/usc_undergrad_complete_catalogue_2026_2027/     ← source of record (text)
├── programs/NNN_name_credential.txt                   470 files
├── index.csv                one row per included programme
├── excluded_programs.csv    623 rows: every exclusion + evidence
├── manual_review.csv        57 rows: undecidable, needs a human
├── errors.csv, fetch_log.csv, manifest.json

data/requirements_json_2026_2027/                    ← for the audit engine
├── NNN_name_credential.json                           470 files
└── programmes_index.json                              roll-up + counts
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
| `Content SHA-256` | string | Hash of the rendered content **only** (not the header). |
| `Extraction Status` | string | Always `complete` — a failed extraction is never written. |
| `Breadcrumbs` | string | Optional 13th line; `Return to:` context. |

Content is deterministic plain text: `#`/`##` headings, `-` course lines,
`Units: N`, `TABLE:`/`Columns:`/`Row N:` for genuine data tables, `[1]` footnotes.

## JSON object (`requirements_json_*/NNN_*.json`) — **proposed v1.0**

| Field | Type | Notes |
|---|---|---|
| `_schema_version` | string | `"1.0"`. Consumers should **fail fast** on mismatch, per the `dept_clearance.json` convention. |
| `programme.name` | string | Same as the text file's `Program Name`. |
| `programme.credential` | string \| null | `null` for minors. |
| `programme.kind` | string | `"degree"` \| `"minor"`. Derived from the title. |
| `programme.program_identifier` | string | `poid=NNNNN` — join key back to the text file and `index.csv`. |
| `programme.source_text_file` | string | The `.txt` this was derived from. |
| `programme.source_content_sha256` | string | Lets the engine detect that the underlying text changed. |
| `totals.stated_total_units` | number \| null | **`null` when USC does not state it unambiguously.** Never guessed — see limitations. |
| `totals.stated_total_units_source` | string \| null | The exact phrase the number came from, e.g. `"Total units: 52"`, `"is a 128-unit program"`. |
| `totals.unit_statements_verbatim` | array of string | Every sentence mentioning units, kept verbatim, so a human can adjudicate. **Not interpreted.** |
| `totals.course_entry_count` / `distinct_course_codes` / `section_count` | int | Counts for sanity-checking a parse. |
| `sections[]` | array | Requirement sections in document order. |
| `sections[].title` | string | e.g. `"Required Courses"`, `"Total units: 52"`. `"(preamble)"` for text before the first heading. |
| `sections[].level` | int | Heading depth (2 = `##`). Preserves nesting. |
| `sections[].courses[]` | array | Course entries in this section. |
| `sections[].courses[].code` | string | `"PREFIX NNN[suffix]"`, e.g. `"BISC 120Lg"`. Same format as `catalog/`'s `course_name` **except** suffixes are preserved. |
| `sections[].courses[].title` | string \| null | Course title as printed. |
| `sections[].courses[].units` | number \| null | From `Units: N`; `null` if the catalogue omits it. |
| `sections[].courses[].source_line` | string | **The verbatim source line.** Every entry is traceable. |
| `sections[].courses[].alternative_follows` | bool | Present only when a bare `or` followed this entry — the next entry is an alternative. |
| `sections[].notes[]` | array | Prose that is not a course line. Nothing is dropped. |
| `sections[].notes[].states_choice_rule` | bool | Present when the note contains a "choose one / select two / at least" rule. |
| `sections[].choice` | string \| null | First choice rule found in the section, verbatim. |
| `parse_warnings` | array of string | Empty when the parse was clean. |

## Known limitations

- **332 of 470 programmes have `stated_total_units: null`.** USC often states
  units only per-section, or in prose that also contains unrelated unit
  restrictions. A naive `\d+ units` grab produces **wrong** totals — e.g.
  Accounting (BS) contains *"may complete a maximum of 12 units from the
  Marshall School"*, which is a restriction, not the degree total. The
  converter therefore extracts a total only from unambiguous phrasing and
  otherwise reports `null` plus `unit_statements_verbatim`. **Do not infer a
  total from those statements automatically.**
- **23 programmes have no course list at all**, and this is correct: some are
  self-designed majors (`Interdisciplinary Studies (BA)` has no fixed courses by
  design) and some are cross-reference stubs (`Nonprofits… Interdisciplinary
  Minor` is ~286 characters ending *"See complete description in the USC Price
  School of Public Policy section"*). Verified against the live pages.
- **`manual_review.csv` has 57 rows by design.** Links whose title carries no
  recognizable credential. Neither included nor excluded — a human decides.
  Please do not read them as silently dropped data.
- **Requirement *logic* is only partially structured.** "Choose one of the
  following" is captured as `choice` / `states_choice_rule`; deeply nested
  or/and trees are left in `notes` verbatim rather than guessed at. The audit
  engine will need human review for complex programmes.
- **Prerequisites are inside requirement prose**, not a separate field yet. If
  the validator wants them structured, that is a follow-up.
- **Catalogue text belongs to USC.** This is public-page retrieval for academic
  use. `robots.txt` disallowed paths are never requested, requests are paced on
  a single connection, and CAPTCHAs are never defeated — the scraper hands off
  to a visible browser for a human.

## Versioning

This file's `_schema_version` (1.0) must match the `_schema_version` field in
every JSON file under `data/requirements_json_*/`. Any consumer should check it
and **fail fast** — raise, don't silently misread — matching the convention used
by `catalog/` and `dept_clearance.json`.

Bump the minor version for additive fields; bump major for a rename or a
semantic change. `programme.source_content_sha256` lets a consumer detect that
the underlying catalogue text changed even when the schema did not.

## Run it

```bash
cd catalogue_scraper
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium

# scrape a catalogue year (bachelor's + minors)
python -m usc_catalog_scraper run --all-undergrad --resume \
  --catalogue-year 2026-2027 --workdir ./out

# convert the text corpus into requirements JSON
python tools/to_requirements_json.py \
  data/usc_undergrad_complete_catalogue_2026_2027 \
  data/requirements_json_2026_2027
```

~25–35 minutes for a full year (request pacing is deliberate).
`macos_app/` wraps this in a double-clickable app that asks for the year.

## Verify it

```bash
python tools/audit_corpus.py <report-dir> data/usc_undergrad_complete_catalogue_2026_2027
python -m pytest -q      # 211 tests, incl. 4 real-browser integration tests
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

`docs/HOW_IT_WORKS_AND_HOW_TO_BUILD_IT.md` — design reasoning and a rebuild guide.
