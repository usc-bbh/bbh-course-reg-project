# Next-Semester Schedule Validator (Module 4B)

> **Status:** work in progress. Skeleton documentation — fill in the `TODO` sections. Keep this file in sync with `validate_next_semester.py` as it changes.

## Purpose & scope

`validate_next_semester.py` checks a student's list of planned courses for next term against their STARS report and the term's course catalog, and returns a per-course + overall verdict.

- **In scope:** _TODO — one-paragraph summary of what this tool decides._
- **Out of scope:** this is NOT the degree-planning / what-if tool. It does not verify graduation requirements.

## How to run

The module has a demo entry point that runs against the fixtures in `test/fixtures/`:

```console
$ cd validator
$ python validate_next_semester.py
```

It prints a `ValidationResult` as JSON. _TODO: note how inputs are supplied in production (passed in as JSON from the React layer via Pyodide — see team notes)._

## Input schemas

The validator is a pure function: `validate_next_semester(planned_courses, stars_report, course_catalog)` (+ `dept_clearance` once it becomes a parameter — see review notes).

### `planned_courses`
List of course-code strings, e.g. `["CSCI 360", "MATH 407"]`. _TODO: confirm course-level vs section-level once the section refactor lands._

### `stars_report`
⚠️ Only a **subset** of the STARS report is used. Fields actually consumed:

| Field | Type | Used for |
|---|---|---|
| `completedCourses[].code` | string | already-taken check |
| `inProgressCourses[].code` | string | in-progress check |
| `classLevel` | string | class-standing check |

_TODO: document full expected object + note the param should be renamed to reflect the subset._

### `course_catalog`
_TODO: document the `{term, courses: {CODE: entry}}` shape and each `entry` field (`units`, `description`, `has_d_clearance`, `has_restrictions`, `has_lab`, `has_discussion`, `sections`), plus the section fields (`section_id`, `link_code`, `notes`, `is_cancelled`, `open_seats`, `is_full`, `days`, `start_time`, `end_time`, `section_type`)._

### `dept_clearance`
_TODO: document the dept-clearance dataset shape (see `../dept_clearance.json`, which carries `_schema_version`)._

## Output schema — `ValidationResult`

_TODO: document the returned object:_
- `overall_status`: `"valid" | "invalid" | "warning"`
- `course_results[]`: `{course, status: "pass" | "fail" | "warning", reasons[]}`
- `summary`: `{total_units, warnings[]}`

## Checks & behavior (analyzed vs. surfaced)

Each check either **analyzes** data to compute a pass/fail, or **surfaces** raw source text as a warning with no analysis. _TODO: fill the source-link column._

| Check | Analyzed / Surfaced | Can produce | Notes |
|---|---|---|---|
| Already taken / in progress | Analyzed | fail / warning | |
| Class standing (400+) | Analyzed | fail | Rule source: **TODO — unverified** |
| Seat availability | Analyzed | fail | |
| Time conflicts | Analyzed | fail | ⚠️ see Limitations |
| In catalog | Analyzed | warning | |
| Unit load > 18 | Analyzed | warning | Cap source: **TODO — unverified** |
| D-clearance | Surfaced | warning | Text from `dept_clearance.json` |
| Prerequisites | Surfaced | warning | Echoes catalog description |
| Lab/discussion pairing | Surfaced | warning | Static reminder |
| Major/registration restrictions | Surfaced | warning | Echoes section notes |

## Constraints & official sources

Link each enforced rule to an authoritative USC page. **Mark anything unverified.**

- Class standing / 400-level rule → _TODO: source or remove (currently unverified)._
- Recommended unit cap (18) → _TODO: source or remove (currently unverified)._
- D-clearance → see `../dept_clearance.json` (`source_url` per department).
- _TODO: add others as checks are added._

## Known limitations (don't-trust-yet)

- **Operates at course level, not section level.** Seats and timing really live on sections; this must be reworked.
- **Time-conflict logic** only fails when *every* section combination overlaps; it should warn on *any* overlap.
- **Prereqs, D-clearance, and restrictions are surfaced as text, not checked** against the student's record.
- **TBA / null-time sections are dropped** from conflict-checking (should warn instead).
- **`total_units` undercounts** — courses missing from the catalog contribute 0 units.

## Data provenance & versioning

- **Course catalog** — owned by the catalogue scrape (Agastya). The catalog/section shape must match across the React GUI and this Python module (they've diverged — reconcile).
- **`dept_clearance.json`** — reference dataset; already stamped with `_schema_version`. The catalog and STARS payloads **must** be stamped with a `_schema_version` the same way so shape changes are detectable and trackable.

## Testing

There are fixtures in `test/fixtures/` but no test suite yet. See **`../docs/TESTING_GUIDE.md`** for how to write one with pytest. Target: one test per check + regression tests for the limitations above.
