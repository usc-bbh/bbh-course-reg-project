# USC Catalogue Collector — incident investigation and repair

**Date:** 2026-07-30 · **Symptom reported:** `107 Environmental Science` produced
the wrong plain-text output · **Scope found:** 158 of 470 output files (33.6%)
· **Status:** root cause proven, fixed, full dataset regenerated and validated.

---

## 1. Project root identified

| Item | Location |
| --- | --- |
| **Canonical scraper source** (the one repaired) | `~/Desktop/DEEP_WORK /BBH/DELIVERABLE_1/USC Complete Scrape/USC Complete Collector.app/Contents/Resources/scraper` |
| Git-tracked working copy used for the repair | `~/Desktop/USC Scraper Incident Fix/04_fixed_app/USC Complete Collector.app/…/scraper` |
| Majors output that contains the defect (207 files) | `…/DELIVERABLE_1/OTHER STUFF/MAJOR STUFF/usc_undergraduate_catalogue_2026_2027` |
| Minors output (263 files) | `…/DELIVERABLE_1/OTHER STUFF/USC Minors Text Files/usc_minors_catalogue_2026_2027` |
| Preserved read-only baseline of both | `~/Desktop/USC Scraper Incident Fix/01_baseline/` |

**Why this is the right repository.** Three `.app` bundles exist, each with its
own embedded copy of the same Python package `usc_catalog_scraper`:
`USC Catalogue Collector.app` (majors), `USC Minors Collector.app` (minors) and
`USC Complete Collector.app` (both). All three report `__version__ 1.2.0` and
share the defective code. The manifest of the majors corpus
(`manifest.json → application_version`) records **`usc-catalog-scraper 1.1.0`**,
run `run-20260716T055727Z-900fe2`, 2026-07-16 05:57→09:50 UTC — so the delivered
majors files were produced by the 1.1.0 build, and the minors files by 1.2.0 on
2026-07-19/20. The defect is present in **all** of them, including the newest,
so the repair was made in the Complete Collector (the superset app that
regenerates the whole 470-file dataset) and then propagated to the other two.

No `.git` existed in any bundle. A repository was initialised in the working
copy so every change is traceable:

```
da04915 baseline: v1.2.0 as shipped (contaminates 158/470 outputs)
147b650 fix: require content region for program pages + validate extracted text
f300a83 lint/format clean; resume revalidation simplified
244b78b validator: accept prose-only programmes on catalogue section structure
aaf3729 validator: accept cross-reference stub pages (verified against live pages)
```

## 2. Current architecture (system map)

```
year picker (AppleScript)
  → driver.sh (retry ladder, pacing, resume, auto-resume on bot-wall)
    → cli.py run --all-undergrad
      → catalogue_resolver     year → catoid → navoid, from USC's own archive list
      → acquisition.acquire()  L1 httpx → L2 print variant → L3 Playwright Chromium
           · semantic_validation.validate_page()   ← validates the PAGE
           · challenge_detection + x-amzn-waf-action header
      → discovery + boundary   program links inside the proven section
      → classification         bachelor's / minor = include; grad/cert = exclude+reason
      → extraction.select_main_container()         ← ***DEFECT WAS HERE***
      → extraction.clean_content()                noise selectors
      → text_renderer.render_text()               HTML → deterministic text
      →   (no validation of the produced text)    ← ***DEFECT WAS HERE***
      → output.build_filename + atomic_write_text
      → state (SQLite, per-program commit, SHA-256) → index/manifest/CSVs
      → audit command (hashes, counts, indexes)
```

Points where wrong content could enter the pipeline, before the fix:

1. **Container selection** — scored comparison with a whole-document fallback
   that was eligible to win. *(this is what happened)*
2. **Renderer** — a page-layout table with ≥2 cells per row is treated as a data
   table and flattened into `TABLE: / Row 1: / Row 2:`, with rowspan/colspan
   expansion duplicating cell text. *(amplified the damage)*
3. **Validation gap** — `validate_page()` proves the *page* is right; nothing
   proved the *extraction* was right. The only text-level gate was
   `len(text) < 200`. *(this is why it was silent)*
4. **Resume** — a matching SHA-256 certified a file as good, so a contaminated
   file would never be re-attempted.

## 3. Known symptom

`107_environmental_science_and_health_ba.txt`, 4,614 characters, header claiming
`Extraction Status: complete`, body containing:

```
Skip to Navigation

TABLE:
Row 1:  | University of Southern California
Row 2:  | / Jul 16, 2026 /  / USC Catalogue 2026-2027 / ; Begin Responsive End
Responsive / … Environmental Science and Health (BA) The Environmental Science
and Health BA degree combines … double majors.   ← this sentence 8 times …
; Required Courses Total units: 52 / Required Courses Total units: 52 …

<script src="js/smlinks.js" type="text/javascript"></script>
```

Zero course codes. The neighbouring file `106_environmental_engineering_bs.txt`
from the same run, 3,733 characters, is perfect (39 course codes, full
requirement tree).

## 4. Root cause (proven)

**Container selection was decided purely by a numeric score, and the whole
`<body>` was allowed to win.**

`extraction._score()` is dominated by `log(text_length) × 12`, so a container's
score rises with the amount of text it holds. The whole document therefore
scores close to — and on some pages above — the true content region, despite a
−30 body penalty and a +50 bonus for acalog regions.

Reproduced live against catalogue.usc.edu with the shipping code
(`02_evidence/reproduce_container_defect.py`, snapshots retained):

| Page | `td.block_content` (true content) | `<body>` (whole page) | Winner | Output |
| --- | --- | --- | --- | --- |
| 106 Environmental Engineering (BS) | **421.1** | 410.6 | content region | clean |
| 001 Accounting (BS) | **410.6** | ~400 | content region | clean |
| **107 Environmental Science and Health (BA)** | 304.7 | **305.0** | **`<body>`** | **contaminated** |
| 025 Astronomy (BA) | lower | **higher** | `<body>` | contaminated |
| 451 Spanish Minor | lower | **higher** | `<body>` | contaminated |

**The margin on 107 was 0.3 points out of 305.** Environmental Science and
Health is a short programme: its content region holds 2,114 characters while the
surrounding page holds 3,887. Whenever programme content is short relative to
the page chrome, the body wins.

### Causal chain

1. Programme page fetched successfully (the correct content **was** in the HTML).
2. `select_main_container()` scored `<body>` 0.3 above `td.block_content`.
3. `<body>` includes the site skip-link, the USC header table, the acalog
   "Begin/End Responsive" build markers, and an HTML-escaped `<script>` tag that
   is a text node rather than a real element (so the `script` noise selector
   could not remove it).
4. `text_renderer` saw the page-layout table (2 cells per row, so not caught by
   the single-column `_is_layout_table` guard) and rendered it as a data table:
   `TABLE: / Row 1: / Row 2:`. colspan expansion copied the programme blurb into
   every expanded column — the 8 repetitions.
5. `validate_page()` passed, because it validates the fetched page: the page had
   an `<h1>`, >700 characters of text, and the words "unit/requirement/course".
6. The pipeline's only text check was `len(text) < 200`. 4,614 > 200 → written.
7. `Extraction Status: complete`, SHA-256 recorded, `index.csv` row created,
   run summary reported **207/207 successful, 0 failed**.

### Why it stayed silent

Every check in the system was upstream of the mistake. Acquisition proved the
right page arrived; nothing proved the right *part* of it was extracted. The
run summary, the manifest, `errors.csv` and the `audit` command all reported a
clean run, because from their point of view it was one.

## 5. Evidence

| Evidence | Location |
| --- | --- |
| Live reproduction with candidate scores | `02_evidence/reproduce_container_defect.py` + terminal output |
| Real page snapshots (5 pages, fetched 2026-07-30) | `02_evidence/snapshot_*.html` |
| Broken vs good baseline pair | `02_evidence/BROKEN_107_baseline.txt`, `GOOD_106_baseline.txt` |
| Full 470-file audit | `03_audit/scraper_output_audit.{csv,json,md}` |
| Runtime analysis of the supplied sheet | `06_reports/RUNTIME_ANALYSIS.md` |
| Fetch-log forensics (per-attempt mode/status/elapsed) | `01_baseline/*/fetch_log.csv` |
| Regression tests pinning the defect | `tests/test_regression_incident_20260730.py` |

## 6. Full-corpus findings

470 files audited (207 majors + 263 minors). **PASS 276 · REVIEW 36 · FAIL 158.**

All 158 failures carry the identical fingerprint set, and no passing file
carries any of them — a perfectly clean diagnostic split:

| Signature | Files |
| --- | --- |
| `Skip to Navigation` | 158 |
| `| University of Southern California` (site header cell) | 158 |
| `Begin Responsive` / `End Responsive` | 158 |
| literal `<script …>` in text | 158 |
| `TABLE:` / `Row N:` from the flattened layout table | 158 |
| body missing its own programme title heading | 158 |
| median course codes in body | **0** (clean files: 38) |

Distribution — contamination tracks *content length*, not timing:

| Bucket | Files | FAIL | Rate |
| --- | --- | --- | --- |
| Minors | 263 | 122 | **46%** |
| Majors | 207 | 36 | 17% |
| BA degrees | 82 | 23 | 28% |
| BS degrees | 95 | 11 | 12% |
| direct HTTP 200 fetches | 145 of the failures | — | — |
| browser-rendered fetches | 13 of the failures | — | — |

### Hypotheses ruled out, with evidence

| Hypothesis (several suggested in the brief) | Verdict | Evidence |
| --- | --- | --- |
| JavaScript rendering not finished — `page.goto()` returned too early | **Ruled out as the cause** | 120 of 158 failures came from plain `direct_html` HTTP 200 responses where no JavaScript ran at all. The correct content is present in the raw HTML: extracting `td.block_content` from the saved 107 snapshot yields the complete, correct programme (1,746 chars, 20 course codes, "Total units: 52"). |
| Slow pages / timeouts produce bad output | **Ruled out** | FAIL median runtime 7s vs PASS 6s. The four slowest pages (962s, 230s, 219s, 206s) all produced clean output. 34 of 66 measured failures ran at or below the median. |
| AWS WAF bot-wall (HTTP 202) corrupted the capture | **Contributing factor only, not the cause** | 49 files were accepted while the server returned 202; only 13 of them are contaminated, and 145 contaminated files came from clean 200 responses. 107 happens to be a 202 case, which is why it looked causal at first. |
| Fixed sleep too short | **Ruled out** | No fixed sleep governs extraction; the defect is deterministic and reproduces offline from a saved snapshot. |
| Filename collisions / wrong URL / program-name mismapping | **Ruled out** | 0 duplicate normalized bodies among failures; every file's internal `Program Identifier` matches its `index.csv` row and its filename. |
| Encoding corruption | **Ruled out** | All files decode as clean UTF-8; the contamination is structural, not byte-level. |
| Source pages incomplete at request time | **Ruled out** | Re-fetching the same pages today reproduces the identical defect with the identical scores — deterministic, not transient. |

## 7. Every affected programme

The full list of 158 files, with per-file evidence and excerpts, is in
`03_audit/scraper_output_audit.csv` (filter `validation_status == FAIL`) and
summarised in `03_audit/scraper_output_audit.md`. 36 majors and 122 minors.

## 8. Design of the fix

Three changes, all in the direction of "fail loudly rather than write
something plausible".

**(a) A programme page's container is a structural requirement, not a score.**
`select_main_container(soup, cfg, require_content_region=True)` restricts the
winner to a real catalogue content region. The whole-document fallback and
page-level landmarks are ineligible at any score. When no content region exists
the new `ContentRegionNotFound` is raised rather than silently degrading; the
pipeline records the error, leaves the programme pending for a later attempt,
and writes nothing. Scores still order the eligible regions among themselves.

**(b) The final extracted text is validated immediately before it is written.**
New module `output_validation.py`. A body must:

- contain none of the literal contamination fingerprints taken from the real
  defective files (skip-link, site-header cell, responsive build markers,
  literal `<script>`/HTML markup, loading placeholders, JS errors, bot-wall
  text, navigation run-ons);
- open with the programme's **own title** as a heading;
- contain course-code or unit evidence;
- not repeat a substantial sentence 3+ times (the rowspan-duplication signature);
- clear a 200-character backstop.

Thresholds are derived from the corpus, not invented: the smallest *clean* body
observed was 971 characters, and clean bodies always had both a title heading
and course/unit content. **Length alone never rejects a programme that shows
semantic evidence**, so a genuinely terse minor still passes — the brief's
warning about the five smallest files is handled by evidence, not by size.

One deliberate correction during implementation: my first draft treated a bare
`Row N:` label as fatal. That is wrong — the renderer legitimately emits it for
real course-requirement tables (`tests/fixtures/program_tables.html`), and the
rule caused a false positive. The fingerprint is the *site header inside* such a
row, which is what is now matched. The other four fingerprints already identify
100% of the 158 files, so nothing was lost.

**(c) Resume re-validates existing output.** `needs_extraction()` previously
trusted a matching SHA-256. A hash proves the file is unmodified, not that it is
correct, so every contaminated file would have been skipped forever. It now runs
the content validator on existing files and queues bad ones for repair.

An invalid extraction can no longer overwrite a valid file: the pipeline returns
before the write, so any previously good output survives.

## 9. Files changed

| File | Change |
| --- | --- |
| `src/usc_catalog_scraper/extraction.py` | `ContentRegionNotFound`, `_CONTENT_REGION_LABELS`, `require_content_region` gate in `select_main_container()` |
| `src/usc_catalog_scraper/output_validation.py` | **new** — validation of the final text |
| `src/usc_catalog_scraper/pipeline.py` | strict container for programme pages; validate before write; error rows; keep prior file |
| `src/usc_catalog_scraper/state.py` | `_existing_output_is_valid()`; `needs_extraction()` re-validates |
| `tests/test_regression_incident_20260730.py` | **new** — 16 tests |
| `tests/test_state_resume.py` | realistic fixtures + new contaminated-but-unmodified test |
| `tests/fixtures/program_10{6,7}_*.html` | **new** — the real live pages |

Not changed: acquisition, classification, discovery, boundary detection,
filenames, the driver, the user-facing workflow. The app is still launched by
double-clicking it and picking a year.

## 10. Tests added

16 regression tests, all passing, including: the defect reproduced from the real
107 page; the fix producing correct content from that same page; 106 unaffected;
`ContentRegionNotFound` raised instead of using the document; the exact broken
107 body rejected with reasons; the repaired body accepted; six parametrised
failure modes; a legitimately short programme accepted on semantics;
rowspan-duplication detected; and contaminated-but-unmodified files re-queued on
resume.

Two further tests were added after live rejections during the corrected run
(see §13): a prose-only programme must pass, and a cross-reference stub page
must pass — plus two guard tests proving neither allowance lets contamination
through.

**Full suite: 209 passed** (207 + 2 self-review regressions; see §17). `ruff check` clean, `ruff format --check` clean,
`mypy` clean (20 source files).

## 11. Commands

```bash
APP="$HOME/Desktop/USC Scraper Incident Fix/04_fixed_app/USC Complete Collector.app"
S="$APP/Contents/Resources/scraper"

# run the fixed scraper (normal user workflow: just double-click the .app)
open "$APP"

# explicit CLI equivalent for the full 470-programme dataset
"$S/.venv/bin/python" -m usc_catalog_scraper run --all-undergrad --resume \
  --no-latest-resolution --catalogue-year 2026-2027 \
  --boundary-heading "Programs, Minors and Certificates" --no-strict \
  --workdir "<output folder>"

# validate any collection (full audit → CSV + JSON + MD)
python3 "$HOME/Desktop/USC Scraper Incident Fix/03_audit/audit_corpus.py" \
  <report-out-dir> <collection-folder> [more-collection-folders...]

# the app's own integrity audit (hashes, counts, indexes)
"$S/.venv/bin/python" -m usc_catalog_scraper audit --workdir "<output folder>"

# tests + quality gates
cd "$S" && ./.venv/bin/python -m pytest -q
cd "$S" && ./.venv/bin/python -m ruff check src tests && ./.venv/bin/python -m mypy
```

## 12. Remaining risks

1. **Vendor coupling.** The content-region whitelist is acalog-specific
   (`td.block_content`, `#acalog-content`, `div.custom_leftpad_20`). If USC
   re-platforms, programme pages will fail loudly rather than silently — the
   right failure mode, but it will need a one-line selector addition.
2. **Bot-wall throughput.** USC's WAF still rotates its token roughly hourly and
   occasionally serves a verification page. Recovery is automatic, but a run can
   still slow down or pause; this is unrelated to the defect fixed here.
3. **`REVIEW` files (36).** Flagged for a human look, not defects — mostly exact
   duplicate bodies where USC genuinely publishes identical requirement text for
   paired programmes. Listed in the audit CSV.
4. **`manual_review.csv` (57 links).** Unchanged behaviour: titles carrying no
   recognizable credential are never silently dropped.
5. **Vishal's review has not been incorporated** — it could not be found. See
   `VISHAL_REVIEW_ACTIONS.md`. **STARS Redacter does not exist on this machine
   and no work was done on it.**
6. Two of the three `.app` bundles keep their own venv; a moved bundle rebuilds
   its environment on next launch (existing, documented behaviour).

---

## 13. Focused and full rerun results

Corrected output was written to a **new** directory; the delivered baseline was
never modified.

| Stage | Result |
| --- | --- |
| Focused run (6 programmes) | 6/6 valid |
| **Full run (470 programmes)** | **467 written, 3 refused** on the first pass |
| Resume pass 1 | +1 recovered (Interdisciplinary Studies BA) |
| Resume pass 2 | +2 recovered (the two stub minors) |
| **Final** | **470/470 files, 0 outstanding failures** |
| Wall-clock, full run | ~26 minutes (≈2 s/page, direct HTTP throughout) |
| Rejections logged | 3, all investigated against their live source pages |

### The three refusals were my validator being wrong, not the scraper

This is the part worth reading. The new gate refused three programmes. In every
case the *container was correct* (`td.block_content`) and the *body was clean* —
the validator's content rules were too strict:

| Programme | Body | Why it was refused | Ground truth (checked against the live page) |
| --- | --- | --- | --- |
| Interdisciplinary Studies (BA) | 1,978 chars | demanded course codes | A self-designed major: the page describes admission, an academic contract and restrictions. It has **no course list by design**. |
| Consumer Behavior Interdisciplinary Minor | 448 chars | too short, no courses | USC publishes only a description ending "See USC Marshall School of Business." |
| Nonprofits, Philanthropy and Volunteerism Interdisciplinary Minor | 286 chars | too short, no courses | Ends "See complete description in the USC Price School of Public Policy section." |

I fetched all three live to establish ground truth before touching the rules.
The validator now accepts a body with no course list when it carries real
catalogue section structure, and accepts a short body when it is a
cross-reference stub — in both cases still requiring the programme's own title
heading and a clean body, which is what 100% of the 158 contaminated files
failed. Two extra tests pin the guard so the allowances cannot become holes.

A third false positive was caught earlier in the same way: the first version of
the fingerprint list treated a bare `Row N:` label as fatal, which would have
flagged legitimate course-requirement tables. Only the site-header-inside-a-row
pattern is fatal now.

**No page was special-cased.** Every change is a rule change with a documented
reason, applied corpus-wide.

## 14. Before / after metrics

Both corpora audited with the **same** authoritative rules — the audit script
imports the scraper's own `validate_extracted_text`, so audit and scraper cannot
disagree.

| Metric | Before (delivered) | After (corrected) | Change |
| --- | --- | --- | --- |
| Files | 470 | 470 | 0 |
| PASS | 276 | **462** | +186 |
| REVIEW | 36 | 8 | −28 |
| **FAIL** | **158** | **0** | **−158** |
| Contaminated with page chrome | 158 | 0 | −158 |
| Missing own title heading | 158 | 0 | −158 |
| Zero course codes | 99 | 3 | −96 |
| Title mismatch vs index | 0 | 0 | 0 | ← see §17: this check was dead code when first reported; now genuinely verified |
| Missing files | — | 0 | — |
| Filename collisions / duplicates | 0 | 0 | 0 |
| Median body | 4,633 | 2,746 | see note |
| Mean body | 5,326 | 3,378 | see note |

*Note on the medians:* the corrected files are **shorter on average because the
contaminated ones were bloated with site chrome and duplicated blurbs.* 107 went
from 4,614 characters of navigation to 1,746 characters of real requirements.
Shorter here means correct.

- **Repaired (FAIL → clean): 158**
- **Regressed (clean → FAIL): 0**
- Other content changes: 29 — investigated, not assumed to be improvements:
  - **27 minors gained `Units: N` values** on course lines that previously had
    none (e.g. `283_documentary_minor`: `CTCS 400 Documentary Film and Media` →
    `… Units: 4`). The old files were quietly incomplete; no signature caught it.
  - **2 files (`055_business_of_innovation_bs`, `212_addiction_science_minor`)**
    differ only in the position of one or two course lines with the same length.
    This is a genuine USC page edit in the two weeks since the delivered run,
    not scraper behaviour — proven in §15.

## 15. Repeatability

| Check | Result |
| --- | --- |
| Same saved HTML extracted 3× (7 pages) | **identical every time** — extraction is deterministic |
| Independent second live run, 60 programmes | **60/60 byte-identical** substantive content vs run 1 |
| Duplicate files created on re-run | 0 |
| Filenames changed on re-run | 0 |
| Valid content replaced by a failed extraction | 0 (impossible by construction: the pipeline returns before writing) |

`055_business_of_innovation_bs` was inside the 60-programme repeat set and was
byte-identical between the two current runs, which is what proves its difference
from the July baseline is a source-page edit rather than non-determinism.

## 16. Deliverables and exact locations

| Deliverable | Path |
| --- | --- |
| **Corrected complete output (470 files)** | `05_corrected_output/full/usc_undergrad_complete_catalogue_2026_2027/programs/` |
| **Corrected 107** | `02_evidence/CORRECTED_107.txt` (also file 107 in the folder above) |
| File-level audit (before / after) | `03_audit/before/` and `03_audit/after/scraper_output_audit.{csv,json,md}` |
| Run manifest | `05_corrected_output/full/usc_undergrad_complete_catalogue_2026_2027/manifest.json` |
| Failed / manual-review pages | `06_reports/FAILED_AND_REVIEW_PAGES.md` |
| Debug artefacts (live page snapshots) | `02_evidence/snapshot_*.html` |
| Preserved baseline | `01_baseline/` |
| Repaired app (git, 4 commits) | `04_fixed_app/USC Complete Collector.app` |

The fix was also propagated into the three live apps under
`~/Desktop/DEEP_WORK /BBH/DELIVERABLE_1/` (all compile and carry the guard); each
rebuilds its Python environment on next launch, which is pre-existing behaviour
for a moved bundle.

---

## 17. Self-review pass (2026-07-31) — four defects found in the fix itself

The fix was re-reviewed adversarially after delivery. Four real defects were
found **in my own changes**, all now fixed, tested and re-propagated.

| # | Defect | Severity | Evidence it was real |
| --- | --- | --- | --- |
| 1 | `title_heading_present()` used substring matching, so a short programme name matched unrelated headings — `"Art"` matches `"## Dep**art**mental Requirements"` and `"## Ch**art** of Accounts"`. A body with **no title heading of its own passed** the single most reliable contamination check. | **High** — weakened the primary detector | Demonstrated: `validate_extracted_text("## Departmental Requirements\n\nART 101 …", "Art (BA)")` returned `ok=True`. Now a prefix match on the heading's own text; returns `False`. |
| 2 | The "outscored-but-ineligible" evidence note used `t not in eligible`, and bs4 `Tag.__eq__` is a **deep structural comparison, not identity** — two distinct but identically-marked-up candidates compare equal. | Low (evidence string only) | Demonstrated: two separate `<div><p>x</p></div>` elements compare `==` True while `is` False. Now compares by `id()`. |
| 3 | The cross-reference-stub allowance (added during the run) accepted a **truncated** body that merely contained a "See the X Department" phrase. | Medium — a hole in the new gate | Demonstrated: a 218-char mid-sentence body passed. Stubs must now also end coherently (sentence punctuation, `---`, or a heading); the same body is now rejected while both real stubs still pass. |
| 4 | `state._existing_output_is_valid()` validated a file **missing the `OFFICIAL CATALOGUE CONTENT` marker** by treating the metadata header as body content. | Low | Demonstrated: a marker-less file returned `True`. Such a file is malformed and is now re-extracted. |

### A claim I had to correct

I reported "title mismatch 0 → 0" in §14. That number came from a check that
**never executed**: `index.csv`'s column is `output_filename`, but the audit
join looked for `output_file` / `filename` / `file`, so `index_by_file` was
always empty and `title_mismatch` was hard-wired to `False`. The join is fixed;
the check now runs on **470/470 rows in both corpora and genuinely reports 0
mismatches**. The conclusion was right by luck, not by verification.

### A threshold I had asserted without evidence

`MAX_REPEATED_SENTENCE = 3` was chosen by judgement. Measured across the
corrected corpus: **460 files have max-repeat 1, 10 files have 2, none have 3+**
— so the threshold has real headroom above legitimate content, and the
defective 107 sat at 8. The threshold is now evidence-backed.

### Regression protection for the fixes

All 470 corrected files were re-validated under the tightened rules:
**0 new rejections.** Four tests added (209 total in the working copy).

### Propagation gap found and closed

The src fixes had been copied to the three live apps, but the **updated tests
and their fixtures had not** — so each live app failed its own suite
(`test_state_resume.py` still carried placeholder bodies that content
validation now rejects). All three apps have been given the shared regression
suite and fixtures, had their Python environments rebuilt, and now pass:

| Live app | Result |
| --- | --- |
| `USC Complete Scrape/USC Complete Collector.app` | **205 passed, 4 skipped** |
| `OTHER STUFF/USC Catalogue Collector.app` | **all passed** |
| `OTHER STUFF/USC Minors Collector.app` | **all passed** |

The 4 skips are the real-browser integration tests; they skip when Chromium is
absent from a freshly rebuilt environment and run once the app installs it on
first launch. Mode-specific suites (`test_minors_mode.py`,
`test_all_undergrad_mode.py`) were deliberately **not** copied to apps whose
config lacks those flags.

### Residual weaknesses I am not fixing, and why

1. **Content-region eligibility is a label whitelist, not a chrome test.** A
   region is eligible because its selector label contains "acalog", not because
   it was proven free of page furniture. On the live pages the only
   chrome-bearing acalog candidate (`#acalog-content`'s enclosing toolbar cell)
   scores far below `td.block_content`, so it is unreachable in practice — but a
   future USC layout change could make it reachable. The principled fix is to
   test candidates for chrome markers; it is a larger change than this incident
   warrants and belongs in review with Natalie (decision #2).
2. **`needs_extraction()` now reads and regex-scans every completed file on each
   run.** Negligible at 470 files; worth knowing before the corpus grows by an
   order of magnitude.
3. **Tightening validation rules later will mass-re-fetch.** By design, but it
   means a rule change costs a full re-scrape of anything it newly rejects.
