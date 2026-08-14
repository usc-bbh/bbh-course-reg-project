<div align="center">

# USC Catalogue Scraper

**One plain-text file per USC undergraduate programme, scraped from the USC Catalogue.**

Module 2 of `bbh-course-reg-project` · Owner: Francis Ruan · Schema `1.1`

`470 programmes` · `470 PASS / 0 REVIEW / 0 FAIL` · `0 contamination markers` · `225 tests`

</div>

---

This document is the **contract** for the degree-requirements data consumed by the
degree-audit engine (Natalie) and by `validate_next_semester()`'s prerequisite
logic. If you change the scraper output, update this file in the same PR.

> [!NOTE]
> **One documented exception in the corpus.**
> `402_nonprofits_philanthropy_and_volunteerism_interdisciplinary_minor.txt` is
> only 285 characters, and that is **correct, not truncated**. USC's catalogue
> page for this minor is a pointer, ending *"See complete description in the USC
> Price School of Public Policy section"* — the actual course list lives on
> **price.usc.edu**, not in the catalogue. If you need its requirements, go to
> the Price School site. `260_consumer_behavior_interdisciplinary_minor.txt`
> (447 chars) defers to USC Marshall the same way. The audit report lists both
> under **Notes**; they are not failures.

---

## Contents

| | |
|---|---|
| [Quick start](#quick-start) | Install and run |
| [What this module is](#what-this-module-is) | And what it is not |
| [Who consumes this](#who-consumes-this) | Downstream contracts |
| [On-disk shape](#on-disk-shape) | Where the data lives |
| [Text file format](#text-file-format) | **The schema contract** |
| [Two hashes](#two-hashes-and-which-one-you-want) | Which one detects change |
| [Known limitations](#known-limitations) | Read before parsing |
| [Versioning](#versioning) | Pin and fail fast |
| [Verify it](#verify-it) | Reproduce the numbers above |
| [Documentation](#documentation) | Design notes and incident reports |

---

## Quick start

```bash
cd catalogue_scraper
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
```

Scrape a catalogue year (bachelor's degrees + minors):

```bash
python -m usc_catalog_scraper run --all-undergrad --resume --catalogue-year 2026-2027 --workdir ./out
```

Roughly **25–35 minutes** for a full year — request pacing (3.5–7.5s) is
deliberate. `macos_app/` wraps this in a double-clickable app that asks for the
year.

---

## What this module is

Scraped from `catalogue.usc.edu` (`preview_program.php`) — what a degree
**requires**.

Runs from any network, no VPN needed, but the site sits behind an AWS WAF, so
acquisition escalates through three layers and re-syncs the rotating WAF token
after each browser success:

```
plain HTTP  →  first-party print variant  →  headless Chromium
```

Catalogue year is resolved from USC's own archive list, then corroborated
against the title on that catalogue's home page. `catoid` is **not** ordered by
year (2023-24 = 18, 2024-25 = 20), so it is never inferred.

Committed data: **2026-2027**.

### What it is not

**Not** `catalog/` (Module 3). That scrapes `classes.usc.edu` — the Schedule of
Classes, i.e. what is **offered** in a term. Different site, different data, no
overlap. `catalog/README.md` already points here: *"Prerequisites are not in
this data at all. They live in the course catalogue (Module 2 / Francis's
scrape)."*

**Scope.** This module's deliverable is the **faithfully scraped text** plus the
CSVs accounting for every decision. Turning that text into whatever structured
shape a consumer needs is the consumer's call.

---

## Who consumes this

**1. Degree-audit engine (Natalie) — primary.**
The engine categorises requirements per degree, major and minor, reading the
`.txt` files in `data/usc_undergrad_complete_catalogue_2026_2027/programs/`
directly as its source data. This module deliberately does **not** impose a
structured requirements schema — the audit engine owns that shape. If you want a
specific JSON emitted from here instead, say so and I'll add it; the text format
below is stable enough to parse against.

**2. `validate_next_semester()` prerequisite check — secondary.**
That check is currently *"a free-text regex over `description`… explicitly
unverified"* (per `validator/README.md`), because the Schedule of Classes has no
prereq data. Prerequisite text lives in these files. Wiring it up needs Tanzil's
agreement on the input shape first, since `validate_next_semester()` takes four
fixed arguments and requirements are not one of them today.

---

## On-disk shape

```
data/usc_undergrad_complete_catalogue_2026_2027/
├── programs/NNN_name_credential.txt    470 files — one per programme
├── index.csv                           470 rows — one per included programme
├── excluded_programs.csv               623 rows — every exclusion + evidence
├── manual_review.csv                    57 rows — undecidable, needs a human
├── errors.csv                                   — rejected extractions
├── fetch_log.csv                                — every acquisition attempt
└── manifest.json                                — run provenance + counts
```

Every discovered link is accounted for: **470 + 623 + 57 = 1150**, matching
`discovered_in_boundary` in `manifest.json`. Nothing is silently dropped.

---

## Text file format

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
`Units: N`, `TABLE:`/`Columns:`/`Row N:` for genuine data tables, `[1]`
footnotes.

<details>
<summary><b>Example</b> — <code>365_law_and_public_policy_minor.txt</code> (abridged)</summary>

Header fields elided for brevity are marked `…`; the content excerpt is verbatim.

```
Program Name: Law and Public Policy Minor
Credential:
…
Program Identifier: poid=32309
Acquisition Mode: browser_rendered_dom
Retrieved At: 2026-08-14T02:17:25Z
Content SHA-256: 0b7f065f5e9e84555a7f5584b78e32a1a8f19a8f5475aa798f5b665b430e6635
Extraction Status: complete
Breadcrumbs: Return to: > Programs, Minors and Certificates

OFFICIAL CATALOGUE CONTENT

# Law and Public Policy Minor

---

The minor in law and public policy draws upon four fields of study: public
policy and management, law, economics and political science. …

## Required Courses

---

- PPD 225 Solving Public Problems Units: 4
- PPD 314 Public Policy and Law Units: 4
- PPD 315 Analytic Foundations for Public Policy Units: 4
- POSC 340 Constitutional Law Units: 4 or
- LAW 300 Concepts in American Law Units: 4 or
- PPD 357 Government and Business Units: 4
```

Note that `or` between two courses is preserved verbatim — requirement *logic*
stays as prose (see [Known limitations](#known-limitations)).

</details>

---

## Two hashes, and which one you want

`index.csv` publishes both, and they answer different questions:

| Column | Hashes | Changes when |
|---|---|---|
| `content_sha256` | the rendered content only — identical to the file's `Content SHA-256` header | USC's programme text changes |
| `file_sha256` | the whole `.txt`, header included | **every run** — the header carries `Retrieved At` |

**To detect that a programme's requirements changed, compare `content_sha256`.**
`file_sha256` exists for integrity/resume ("is this file the one I wrote?") and
will differ between two runs even when USC changed nothing.

> Before schema 1.1, `index.csv` published the *file* hash under the name
> `content_sha256`, so a consumer following the advice above saw a spurious
> change on every scrape. If you pinned 1.0 and joined on that column, re-read
> it: the column name now means what it says.

---

## Known limitations

- **Unit totals are stated inconsistently by USC.** Some pages carry an explicit
  `## Total units: N` heading; others state it only in prose, or only
  per-section, or not at all. Treat a total as present-or-absent, never assumed.
  Beware unrelated unit restrictions: Accounting (BS) says *"may complete a
  maximum of 12 units from the Marshall School"* — a restriction, **not** the
  degree total. Roughly 330 of 470 pages have no unambiguous programme total.

- **Requirement *logic* is prose, not structure.** "Choose one of the
  following", `or` between two courses, footnote conditions — all preserved
  verbatim, none of it turned into a machine-readable rule tree. A consumer must
  parse or human-review these for complex programmes.

- **Prerequisites are inside requirement prose**, not a separate field yet.

- **24 programmes have no course list at all**, and this is correct. Some are
  self-designed majors (`Interdisciplinary Studies (BA)` has no fixed courses by
  design); some defer to the owning school (see the note at the top of this
  file). Verified against the live pages.

- **13 course lines carry no unit count, and this is correct.** Course *ranges*
  (`DANC 180-189c`, `DANC 181–189`), prose recommendations (`MATH 129 and MATH
  229 are the recommended…`), the five `EDUC 4xx –` descriptions in
  `461_sustainability…`, and `AHIS 320 Aegean Archaeology Units:` — where USC's
  own page publishes the label with no value. Verified against the live pages
  2026-08-13. Everything else has units, and the validator now enforces that.

- **`manual_review.csv` has 57 rows by design.** Links whose title carries no
  recognizable credential — neither included nor excluded, a human decides.
  Please do not read them as silently dropped data.

- **Catalogue text belongs to USC.** This is public-page retrieval for academic
  use. `robots.txt` disallowed paths are never requested, requests are paced on
  a single connection, and CAPTCHAs are never defeated — the scraper hands off
  to a visible browser for a human.

---

## Versioning

`_schema_version` **1.1** describes the text file format documented above: the
metadata header fields and the rendered-content conventions. A consumer parsing
these files should pin this version and **fail fast** — raise, don't silently
misread — matching the convention used by `catalog/` and `dept_clearance.json`.

Bump the minor version for additive header fields; bump major if a header field
is renamed/removed or the content rendering changes shape.

| Version | Date | Change |
|---|---|---|
| **1.1** | 2026-08-13 | Additive: `index.csv` gains `file_sha256`; `content_sha256` now holds the content-only hash it was always named for. The `.txt` format is unchanged, so a consumer that only reads the text files is unaffected. |
| **1.0** | 2026-08-06 | Initial contract. |

---

## Verify it

Every headline number at the top of this file is reproducible:

```bash
python tools/audit_corpus.py <report-dir> data/usc_undergrad_complete_catalogue_2026_2027
python -m pytest -q                 # 225 tests, incl. 4 real-browser integration tests
ruff check src tests && mypy
```

The audit cross-references every `.txt` against its `index.csv` row and its
accepted `fetch_log.csv` attempt, recomputes hashes, and scans for contamination
signatures. Expected: **470 files, PASS 470 / REVIEW 0 / FAIL 0**, empty
contamination table, two informational Notes (the two deferring minors above).

`tools/` also holds the runtime analysis, before/after comparison and
repeatability checker used to validate the corpus.

---

## Documentation

| Document | What it covers |
|---|---|
| [`docs/HOW_IT_WORKS_AND_HOW_TO_BUILD_IT.md`](docs/HOW_IT_WORKS_AND_HOW_TO_BUILD_IT.md) | Design reasoning and a rebuild guide |
| [`docs/ENGINEERING_REPORT.md`](docs/ENGINEERING_REPORT.md) | The contamination incident, in full |
| [`docs/BEFORE_AFTER.md`](docs/BEFORE_AFTER.md) | Corpus comparison across the fix |
| [`docs/REPEATABILITY.md`](docs/REPEATABILITY.md) | Determinism measurement and its sample size |
| [`docs/RUNTIME_ANALYSIS.md`](docs/RUNTIME_ANALYSIS.md) | Where the 25–35 minutes goes |
| [`docs/FAILED_AND_REVIEW_PAGES.md`](docs/FAILED_AND_REVIEW_PAGES.md) | Per-page acquisition outcomes |

### Read this before changing the extraction logic

Two incidents, one lesson.

**2026-07-30 — the wrong container.** Content-region selection was decided by a
numeric score, and on programmes whose content is short relative to the page
furniture the **whole page body won by 0.3 points**, writing site navigation
into **158 of 470 files** — every one marked `Extraction Status: complete`, with
a valid SHA-256. The fix makes the content region a *structural* requirement and
validates the final text before writing.

> **A passing hash proves integrity, not correctness.**

**2026-08-13 — the vanishing units.** The browser layer fetched the right page,
picked the right container and wrote clean text — but `_expand_collapsed` had
clicked every acalog course toggle on the way, and an expanded course line no
longer carries its `Units: N`. **58 course lines** across 4 files lost their unit
counts while every gate passed, because no gate asserted that units *survived*
extraction. Units are exactly what the degree-audit engine consumes.

> **Validate the fields a consumer actually reads, not just the shape of the text.**

Both are now pinned by regression tests built from the real captured pages:
`tests/test_regression_incident_20260730.py` and
`tests/test_regression_incident_20260813.py`.
