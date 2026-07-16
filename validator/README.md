# Next-Semester Validator (Module 4B)

Checks a student's planned courses against a STARS summary, the course
catalog, and USC department D-clearance rules. Owned by Tanzil.

```python
def validate_next_semester(
    planned_courses: list[str | dict],
    stars_summary: dict,
    course_catalog: dict,
    dept_clearance: dict,
) -> ValidationResult
```

## Input schemas

This section documents what the validator reads/assumes from each input. The
validator does not own these schemas (except `dept_clearance`) — it documents
its assumptions so upstream producers (the STARS parser, Agastya's catalog
scrape) can be checked against them, per the schema-contract discussion.

### `planned_courses`

A list where each item is **either**:

- a plain course code string: `"CSCI 104"`, or
- a dict naming specific chosen sections: `{"course": "CSCI 104", "sections": ["29903", "30119"]}`

When sections are given, seat availability, time conflicts, and lab/discussion
pairing are checked against exactly those sections. When they aren't, those
checks fall back to "is there at least one viable section" / "is every
section full" across all of the course's sections.

### `stars_summary`

**Not the full STARS parser output** — only a slice of it. This validator only
reads the fields below; it does not assume any other STARS field is present:

```json
{
  "major": "Computer Science",
  "classLevel": "Junior",
  "gpa": 3.42,
  "completedCourses": [
    { "code": "CSCI 104", "grade": "B+" }
  ],
  "inProgressCourses": [
    { "code": "CSCI 350" }
  ]
}
```

| Field | Type | Used by |
|---|---|---|
| `major` | `string` | major-restrictions check (best-effort keyword match) |
| `classLevel` | `"Freshman" \| "Sophomore" \| "Junior" \| "Senior"` | class-standing check, major-restrictions undergrad/grad check |
| `gpa` | `number` | prereq check (GPA-threshold parsing) |
| `completedCourses[].code` | `string` | already-taken check, prereq check |
| `inProgressCourses[].code` | `string` | already-taken check |

### `course_catalog`

Accepts either `{"term": "20263", "courses": {code: entry}}` or a flat
`{code: entry}` dict. **Agastya owns this schema** (he owns the scrape) — the
table below is only what the validator reads from it today.

```json
{
  "units": 4,
  "description": "Course description text, sometimes containing prereq/restriction language.",
  "has_d_clearance": true,
  "has_restrictions": true,
  "has_lab": false,
  "has_discussion": true,
  "sections": {
    "lectures": [
      {
        "section_id": "39625",
        "link_code": "A",
        "notes": null,
        "is_cancelled": false,
        "is_full": false,
        "days": ["Mon", "Wed", "Fri"],
        "start_time": "09:00",
        "end_time": "09:50"
      }
    ],
    "labs": [],
    "discussions": [],
    "quizzes": []
  }
}
```

| Field | Used by |
|---|---|
| `units` | unit-overload summary |
| `description` | prereq check (GPA + course-code parsing) |
| `has_d_clearance` | D-clearance check |
| `has_restrictions` | major-restrictions check |
| `has_lab`, `has_discussion` | lab/discussion pairing check |
| `sections.*[].section_id` | section selection matching |
| `sections.*[].link_code` | lab/discussion pairing check |
| `sections.*[].notes` | major-restrictions check |
| `sections.*[].is_cancelled` | excluded from all section-based checks |
| `sections.*[].is_full` | seat-availability check |
| `sections.*[].days`, `start_time`, `end_time` | time-conflict check ("TBA" or malformed values are treated as unresolvable, not a crash) |

### `dept_clearance`

The exact shape of `dept_clearance.json` at the repo root — passed in
explicitly rather than read from a hardcoded path. The validator requires
`_schema_version == "1.4"` and raises `ValueError` immediately if it doesn't
match, rather than silently misreading an unfamiliar shape.

## Output schema

```json
{
  "overall_status": "valid | invalid | warning",
  "course_results": [
    {
      "course": "CSCI 104",
      "status": "pass | fail | warning",
      "reasons": ["CSCI 104 is already completed."]
    }
  ],
  "summary": {
    "total_units": 20.0,
    "warnings": ["Planned load is 20.0 units, above the recommended max of 18."]
  }
}
```

Note the two status vocabularies are intentional, not an oversight:
`course_results[].status` uses `pass/fail/warning`, `overall_status` uses
`valid/invalid/warning`. The GUI (`validator_gui_v2.jsx`) already keys off both
exact vocabularies, so unifying them would be a breaking cross-file change —
flagging here instead of changing unilaterally.

## Checks

| Check | Severity | Data source | USC documentation |
|---|---|---|---|
| Already completed | fail | `stars_summary.completedCourses` | — |
| Already in progress | warning | `stars_summary.inProgressCourses` | — |
| Class standing (400+ level vs. Freshman/Sophomore) | fail | `stars_summary.classLevel` + course number | ⚠️ no authoritative source linked yet — needs a citation or should be dropped |
| D-clearance | warning (never a hard fail — see below) | `course_catalog.has_d_clearance` + `dept_clearance.json` | per-department `source_url` field already inside `dept_clearance.json` |
| Prerequisites | fail / warning | `course_catalog.description` (best-effort GPA + course-code parsing) against `stars_summary` | — |
| Not found in catalog | warning | `course_catalog` presence | — |
| Seat availability | fail | `course_catalog` section `is_full` | — |
| Lab/discussion pairing | fail / warning | `course_catalog.has_lab` / `has_discussion` + section `link_code` | — |
| Major restrictions | fail / warning | `course_catalog.has_restrictions` + section `notes` (best-effort keyword match) | — |
| Time conflict | fail / warning | section `days` / `start_time` / `end_time` | — |
| Unit overload | warning | sum of `course_catalog.units`, threshold = 18 | ⚠️ no authoritative source linked yet — needs a citation or should be dropped |

D-clearance is always a `warning`, never a `fail`, because `dept_clearance.json`
is keyed by department (not by specific course) and its `clearance_required_for`
text changes every semester — there isn't enough here to be confident a
specific course/section is blocked outright.

## Known limitations

- **Prereq and major-restriction checks are best-effort text parsing**, not a
  structured requirements database. They handle GPA thresholds, plain course
  codes, "reserved for X", "not available for X majors", and "only open to
  undergrad/grad students" patterns. Anything else (e.g. "consent of
  instructor", unit-count-based requirements like "8 units of upper division
  ANTH courses") falls back to an unverified warning rather than a wrong
  pass/fail.
- **Time conflict** is checked pairwise across all of a course's considered
  sections. It's a hard `fail` only when *every* combination overlaps
  (no viable choice avoids it); a `warning` when only some combinations do.
  When a course has multiple selected sections at once (e.g. lecture + lab
  both chosen), they're treated as alternative options for this comparison,
  which can under-flag a conflict that only comes from one of them.
- Course codes are normalized to `"DEPT ###"` (single space) everywhere in
  this module.

## Running tests

```bash
python3 -m pip install pytest  # first time only
python3 -m pytest validator/test/
```

## Try it against the mock fixtures

```bash
python3 validator/validate_next_semester.py
```
