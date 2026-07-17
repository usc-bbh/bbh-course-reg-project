# Catalog Schema

Owner: Agastya Bassi (owns the Schedule of Classes scrape)

This document is the contract for the course catalog data consumed by
`validate_next_semester()` and the validator GUI. If you change the scraper
output, update this file in the same PR.

`_schema_version`: **6.0** (scraper code — see status note below)

> **Status:** The v6 scraper (dynamic department discovery + retry logic) is
> written and in this folder, but has not yet completed a full successful
> run — USC's API has been intermittently rate-limiting/timing out during
> scraping sessions. The last complete dataset is **v5**
> (`bbh_schedule_data_v5.json`, not yet committed here), which used a fixed
> 62-department list and is missing courses from ~30 real departments
> (e.g. FBE, GERO, PPD, ADNT) that were never searched directly. v6 fixes
> this by pulling the department list from USC's own `Search/Autocomplete`
> endpoint, but needs a clean run to completion to produce v6 data. Until
> then, treat department coverage as incomplete.

---

## Source

Scraped from USC's Schedule of Classes API (`classes.usc.edu/api/Search/Basic`).
Requires USC network or VPN to run. See `scrape_schedule.py`.

The list of department prefixes to scrape is pulled dynamically from USC's
own `Search/Autocomplete` endpoint each run, rather than a hand-maintained
list — this was a real bug in earlier versions (a hand-typed 62-department
list silently missed ~30+ real departments like FBE, GERO, PPD, ADNT, since
they only ever appeared as "leaked" results under unrelated searches).

Terms covered: Fall 2026, Spring 2026, Fall 2025, Spring 2025, Fall 2024,
Spring 2024 (term codes `20263`, `20261`, `20253`, `20251`, `20243`, `20241`).

## Current on-disk shape (`bbh_schedule_data_v6.json`)

This is the raw scrape output — **not** the shape the validator consumes.
See "Shape the validator expects" below for the transform.

```json
{
  "schema_version": "6.0",
  "generated_at": "...",
  "terms": { "20263": "Fall 2026", "20261": "Spring 2026", "...": "..." },
  "terms_data": {
    "20263": [ /* array of course objects, this term only */ ],
    "20261": [ /* ... */ ]
  },
  "offering_frequency": { /* see below */ }
}
```

`terms_data` is keyed by term code, and each value is an **array** of course
objects (not a dict). `validate_next_semester()` expects a dict keyed by
course code for a single term, so a transform step is required. The
per-course-file hosting plan (one file per course per term) produces the
correct shape natively — see "Shape the validator expects" below.

## Course object

| Field | Type | Notes |
|---|---|---|
| `course_name` | string | e.g. `"CSCI 104"`. Always `"PREFIX NNN"` format (space-separated). |
| `units` | int or float | Verified across the full scrape — always numeric, never null or string. |
| `description` | string | Course description. May contain prereq text in free form. |
| `term_code` | string | e.g. `"20263"`. Matches the parent key in `terms_data`. |
| `has_lab` | boolean | True if any section has `section_type = "labs"`. |
| `has_discussion` | boolean | True if any section has `section_type = "discussions"`. |
| `has_d_clearance` | boolean | True if **any** section has `has_d_clearance = true`. Course-level rollup. |
| `has_restrictions` | boolean | True if any section has a non-null `notes` field. |
| `section_counts` | object | e.g. `{"lectures": 1, "labs": 2}`. Empty groups omitted. |
| `sections` | object | Grouped by type — see below. **Not** a flat list. |

## Sections object

Sections are grouped by type, not a flat array:

```json
"sections": {
  "lectures": [ { ...section }, { ...section } ],
  "labs": [ { ...section } ],
  "discussions": [ { ...section } ],
  "quizzes": [ { ...section } ]
}
```

Only non-empty groups are present. A lecture-only course has just a
`"lectures"` key.

### Section object

| Field | Type | Notes |
|---|---|---|
| `section_id` | string | USC section ID, e.g. `"14025"`. Unique per section, not per course. |
| `section_type` | string | `"lectures"` \| `"labs"` \| `"discussions"` \| `"quizzes"` \| `"other"`. |
| `mode` | string | Raw USC value, e.g. `"Lecture"`, `"Lab"`, `"Discussion"`. |
| `has_d_clearance` | boolean | D-clearance for this specific section. Can differ from sibling sections. |
| `link_code` | string \| null | Raw API field. **Not reliable for lecture/lab pairing** — confirmed with Tanzil that within a course, any lab/discussion is valid with any lecture. Kept in case a future term makes it meaningful. |
| `notes` | string \| null | Free-text restriction/eligibility note. Not structured — surfaced as-is. |
| `instructor` | string | Name, or `"TBD"`. |
| `days` | array of strings | e.g. `["Mon", "Wed"]`. |
| `start_time`, `end_time` | string | 24hr `"HH:MM"` format. Empty string if TBA. |
| `total_seats`, `registered_seats` | int | From USC's public feed. |
| `open_seats` | int | `max(0, total_seats - registered_seats)`. **Best-effort** — see limitations. |
| `is_full` | boolean | USC's own full flag, not derived from seats. |
| `is_cancelled` | boolean | Cancelled sections should be filtered out by consumers. |

## Offering frequency object

Top-level key alongside `terms_data`. One entry per unique course name across
all 6 scraped terms:

```json
"CSCI 104": {
  "terms_offered": ["20263", "20261", "20253", "20251", "20243", "20241"],
  "count": 6,
  "frequency_label": "every_semester"
}
```

`frequency_label`: `every_semester` | `most_semesters` | `occasionally` | `rarely`.

## Shape the validator expects

`validate_next_semester(planned_courses, stars_report, course_catalog)` does:

```python
catalog = {_normalize_code(code): entry for code, entry in
           course_catalog.get("courses", course_catalog).items()}
```

It wants a **single-term dict keyed by normalized course code** —
`{"CSCI 104": {...entry...}}` — not the term-nested array in the raw scrape
file. Two ways to produce this:

1. **Per-course-file hosting (planned for V1):** one static JSON file per
   course per term, e.g. `/catalog/20263/CSCI-104.json`, containing just
   that course's entry. React fetches only the courses the student picked
   and assembles the dict client-side before calling into Pyodide.
2. **Local dev (current):** a small transform script converts
   `terms_data["20263"]` from an array into a dict keyed by
   `course_name`, filtered to one term.

Either way, the *entry* shape per course is exactly the course object
documented above — no other transformation needed.

## Known limitations

- **Reserved seats are not exposed** by USC's public API — `open_seats` is
  best-effort, not ground truth. Don't treat a seat count of 0 as
  authoritative; students should still check WebReg.
- **Major restrictions are free text**, not structured. `has_restrictions`
  tells you *that* a restriction exists; `notes` gives the raw text. No
  automated eligibility check is possible from this alone.
- **Prerequisites are not in this data at all.** They live in the course
  catalogue (Module 2 / Francis's scrape), not the Schedule of Classes.
  `validate_next_semester()`'s prereq check is a free-text regex over
  `description` and is explicitly unverified.
- **`link_code` does not reliably indicate lecture/lab pairing.** Do not
  use it to restrict which lab/discussion a student can pick relative to
  their chosen lecture.
- **The scrape requires USC VPN/network access to run.** It cannot be
  re-run from outside USC's network without VPN. USC's API has also shown
  intermittent timeouts/rate-limiting during heavy scraping sessions —
  the scraper retries transient failures automatically, but a full run
  can still take 45-60+ minutes.
- **Variable-unit courses may be mis-recorded.** USC's raw API returns
  `courseUnits` as an array (for courses like directed research/thesis
  that span a unit range); the current scraper takes only the first value.
  Flagged for verification, not yet confirmed as a live bug.

## Versioning

This file's `_schema_version` (6.0) must match the scrape output's
top-level `schema_version` field. Any consumer reading catalog data should
check this field and fail fast (raise, don't silently misread) if it
doesn't match the version it was built against — matching the convention
already used in `dept_clearance.json`.
