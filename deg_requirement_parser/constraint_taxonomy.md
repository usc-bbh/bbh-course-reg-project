# USC Degree-Requirement Constraint Taxonomy

Version 2026-09-08. Five families.

This block defines the `family` and `details` fields. Every other field on a constraint record
(`id`, `source_text`, `description`, `confidence`, `note`) is specified by the prompt. Examples
below therefore show `family` and `details` only.

Families follow one pattern: a **filter** naming which courses count, a **measure** counting
units or courses, and a **bound** giving the threshold. Where a family needs more than those
three, its section says so.

**Shared shapes.** `bound` and `count` are both `{"op": "eq|min|max", "value": n}`. `measure` is
`"units" | "courses" | "hours" | "tracks" | "departments"`. `scope` is free text naming what the
rule applies to and is valid on any family. `kind` names the variant within a family and is
listed per section below.

**Normalizing.** "four courses" = "4 courses". "no more than 2" / "a maximum of 2" / "at most 2"
= `{"op": "max", "value": 2}`. "at least 1" / "a minimum of 1" / "no fewer than 1" = `{"op":
"min", "value": 1}`. Active and passive voice are identical.

**When two families both fit.** A pool and a count with nothing further is Course Selection; add
a bound on how the picks spread and it is Distribution Bounds. Anything about one course
counting toward two requirements is Course Reuse even when a count appears. Anything about what
must be completed before what is Sequencing. Anything the planner can neither fill nor verify
from a course list is Manual Review.

---

## Course Selection

`family`: `"Course Selection"`

The student picks a stated number of courses or units from a bounded pool. The pool may be an
explicit list, a rule that closes a set ("any ECON 400 or above"), or a fixed set with no choice
at all. This is the only family that adds courses to a plan; the other four constrain what this
one produces.

`details`: `count`, plus one or more of `pool` (course codes), `pool_rule` (text closing a set),
`fixed` (required courses), `choose` (`[{"n": 1, "from": [...]}]`). `kind` is not used.

> Choose three courses from the following list: CSCI 201, CSCI 270, CSCI 310, CSCI 350.

```json
{ "family": "Course Selection",
  "details": { "count": {"op": "eq", "value": 3}, "measure": "courses",
               "pool": ["CSCI 201", "CSCI 270", "CSCI 310", "CSCI 350"] } }
```

> Complete all of the following: PHIL 350, PHIL 351, PHIL 352.

```json
{ "family": "Course Selection",
  "details": { "fixed": ["PHIL 350", "PHIL 351", "PHIL 352"] } }
```

> Complete BUAD 302 and BUAD 304, plus one of BUAD 306 or BUAD 307.

```json
{ "family": "Course Selection",
  "details": { "fixed": ["BUAD 302", "BUAD 304"],
               "choose": [{"n": 1, "from": ["BUAD 306", "BUAD 307"]}] } }
```

> Twelve units from any MUSC course at the 300 level or higher.

```json
{ "family": "Course Selection",
  "details": { "count": {"op": "eq", "value": 12}, "measure": "units",
               "pool_rule": "subject MUSC, level >= 300" } }
```

> Students select four courses from the department's approved upper-division offerings in
> American, European, or global history.

```json
{ "family": "Course Selection",
  "details": { "count": {"op": "eq", "value": 4}, "measure": "courses",
               "pool_rule": "department-approved upper-division history offerings",
               "scope": "American, European, or global history" } }
```

> Choose one of the following tracks: Public Health, Environmental Policy, Urban Development.

```json
{ "family": "Course Selection",
  "details": { "count": {"op": "eq", "value": 1}, "measure": "tracks",
               "pool": ["Public Health", "Environmental Policy", "Urban Development"] } }
```

---

## Distribution Bounds

`family`: `"Distribution Bounds"`

A minimum, a maximum, or both, applied to a subset of the student's selections picked out by an
attribute: a category, a course level, a department, or whether the course sits inside or
outside the home unit. Every variant is the same filter-measure-bound pattern with different
values, which is why they are one family rather than four.

`details`: `filter`, `measure`, `bound`, optionally `scope`. Category splits instead use `total`
plus `categories` (`[{"filter", "measure", "min", "max"}]`) or `groups` (`{"count",
"min_each", "measure"}`).
`kind`: `CATEGORY_BOUNDS` | `LEVEL_BOUNDS` | `ORIGIN_BOUND` | `DEPARTMENT_SPREAD`

> Law Electives (min 4 / max 8 units) plus Other Electives (min 4 / max 8 units), jointly
> totaling 12 units.

```json
{ "family": "Distribution Bounds",
  "details": { "kind": "CATEGORY_BOUNDS",
               "total": {"op": "eq", "value": 12}, "measure": "units",
               "categories": [
                 {"filter": "Law Electives", "min": 4, "max": 8},
                 {"filter": "Other Electives", "min": 4, "max": 8}] } }
```

> Choose four courses (16 units), at least one from each of three thematic groups.

```json
{ "family": "Distribution Bounds",
  "details": { "kind": "CATEGORY_BOUNDS",
               "total": {"op": "eq", "value": 4}, "measure": "courses",
               "groups": {"count": 3, "min_each": 1} } }
```

> At least 24 of the 32 total major units must be upper-division.

```json
{ "family": "Distribution Bounds",
  "details": { "kind": "LEVEL_BOUNDS", "filter": "level >= 300", "measure": "units",
               "bound": {"op": "min", "value": 24}, "scope": "32 total major units" } }
```

> No more than 2 of the 9 required courses may be at the 100/200 level.

```json
{ "family": "Distribution Bounds",
  "details": { "kind": "LEVEL_BOUNDS", "filter": "level 100-200", "measure": "courses",
               "bound": {"op": "max", "value": 2}, "scope": "9 required courses" } }
```

> No more than two total courses in the major may be taken outside the college.

```json
{ "family": "Distribution Bounds",
  "details": { "kind": "ORIGIN_BOUND", "filter": "outside the college", "measure": "courses",
               "bound": {"op": "max", "value": 2} } }
```

> A minimum of 104 units applicable to the degree must be earned in the college's academic
> departments.

```json
{ "family": "Distribution Bounds",
  "details": { "kind": "ORIGIN_BOUND", "filter": "within the college's departments",
               "measure": "units", "bound": {"op": "min", "value": 104} } }
```

> No more than 12 units may be taken in any one USC department.

```json
{ "family": "Distribution Bounds",
  "details": { "kind": "DEPARTMENT_SPREAD", "filter": "any one department",
               "measure": "units", "bound": {"op": "max", "value": 12} } }
```

> Electives must be drawn from at least three different departments.

```json
{ "family": "Distribution Bounds",
  "details": { "kind": "DEPARTMENT_SPREAD", "filter": "distinct departments",
               "measure": "departments", "bound": {"op": "min", "value": 3},
               "scope": "electives" } }
```

A percentage ceiling ("no more than half of the elective units from one category") keeps the
same shape with `"measure": "units"` and `{"op": "max", "value": 0.5, "as": "fraction"}`.

---

## Course Reuse

`family`: `"Course Reuse"`

Whether a single course can count more than once: toward two requirements inside this program,
toward this program and another one, or as one of several overlapping equivalents. These share
the filter-measure-bound shape but need cross-requirement bookkeeping the other families never
do, so they stay separate.

`details`: `bound` and `scope`, plus `polarity` (`PROHIBITS` | `PERMITS`) on double-counting, or
`set` and `max_from_set` on equivalence.
`kind`: `DOUBLE_COUNT` | `UNIQUENESS_FLOOR` | `EQUIVALENT_EXCLUSIVITY`

> Courses used for the Core, Seminar, or Elective categories cannot count toward more than one
> of those categories.

```json
{ "family": "Course Reuse",
  "details": { "kind": "DOUBLE_COUNT", "polarity": "PROHIBITS",
               "scope": "Core, Seminar, Elective categories" } }
```

> Students may double-count no more than three courses from this degree to satisfy any other
> major.

```json
{ "family": "Course Reuse",
  "details": { "kind": "DOUBLE_COUNT", "polarity": "PERMITS", "measure": "courses",
               "bound": {"op": "max", "value": 3}, "scope": "any other major" } }
```

> A minimum of four courses (16 units) must be unique to the minor.

```json
{ "family": "Course Reuse",
  "details": { "kind": "UNIQUENESS_FLOOR", "measure": "courses",
               "bound": {"op": "min", "value": 4}, "scope": "minor" } }
```

> Students may not complete more than one of TAC 115, TAC 116, CSCI 103L and CSCI 113x.

```json
{ "family": "Course Reuse",
  "details": { "kind": "EQUIVALENT_EXCLUSIVITY",
               "set": ["TAC 115", "TAC 116", "CSCI 103L", "CSCI 113x"], "max_from_set": 1 } }
```

---

## Sequencing

`family`: `"Sequencing"`

Ordering in time: what must be completed before what, and what must happen inside a window. This
is the only family that constrains which term a course lands in rather than whether it counts.

`details`: `before` and `after` on orderings, `milestone` on a non-course event, `window` on a
timing limit.
`kind`: `PREREQUISITE` | `BEFORE_MILESTONE` | `UNIT_WINDOW`

> 200-level IR courses must be completed before 400-level IR courses are attempted.

```json
{ "family": "Sequencing",
  "details": { "kind": "PREREQUISITE", "before": "IR 200-level", "after": "IR 400-level" } }
```

> FBE 391 must be completed before declaring the Real Estate Finance emphasis.

```json
{ "family": "Sequencing",
  "details": { "kind": "BEFORE_MILESTONE", "before": ["FBE 391"],
               "milestone": "declare Real Estate Finance emphasis" } }
```

> The four core courses must be completed within the student's first 32 units.

```json
{ "family": "Sequencing",
  "details": { "kind": "UNIT_WINDOW", "scope": "four core courses", "measure": "units",
               "window": {"op": "max", "value": 32} } }
```

---

## Manual Review

`family`: `"Manual Review"`

Real requirements the planner can neither fill nor verify from a course list. Record them so
they surface to the student, but do not encode them as constraints. Admission gates and program
rules are checkable once at setup if the plan carries the student's declared programs and
standing; the rest are never checkable.

A gate and a program rule are told apart by what the condition references: this program's own
admission process is `GATE`, the student's other declared programs is `PROGRAM_RULE`.

`details`: `kind` plus the keys shown per example below.
`kind`: `GATE` | `PROGRAM_RULE` | `DISCRETIONARY` | `NO_POOL` | `PROCEDURAL` | `HOURS`

Closed values: `stage` is `INITIAL_ADMISSION` | `INTERNAL_TRANSFER` | `EMPHASIS_ENTRY`. `basis`
is `NUMERIC_THRESHOLD` | `QUALITATIVE_REVIEW`. `direction` is `EXCLUDES` | `REQUIRES` | `ROUTES`
| `COMBINATION`. `action` is `SUBSTITUTE` | `WAIVE` | `ADD_NONLISTED`. `reason` is
`no_enumerated_list` | `fully_adviser_directed` | `empty_catalog_category` |
`faculty_supervised_milestone`. `procedure` is `ADVISING` | `DECLARATION_DEADLINE`.

> A performance audition is required of applicants to most degree programs.

```json
{ "family": "Manual Review",
  "details": { "kind": "GATE", "stage": "INITIAL_ADMISSION", "basis": "QUALITATIVE_REVIEW",
               "process": "performance audition" } }
```

> To enter this emphasis, a student must have sophomore standing and credit for FBE 391.

```json
{ "family": "Manual Review",
  "details": { "kind": "GATE", "stage": "EMPHASIS_ENTRY", "basis": "NUMERIC_THRESHOLD",
               "requires": ["sophomore standing", "FBE 391"] } }
```

> Not available to majors in the natural sciences.

```json
{ "family": "Manual Review",
  "details": { "kind": "PROGRAM_RULE", "direction": "EXCLUDES",
               "applies_to": "natural sciences majors" } }
```

> Biology majors must take CHEM 300L, CHEM 426 and CHEM 453 rather than the alternate options.

```json
{ "family": "Manual Review",
  "details": { "kind": "PROGRAM_RULE", "direction": "ROUTES", "applies_to": "Biology majors",
               "effect": "fixed set CHEM 300L, CHEM 426, CHEM 453 replaces the standard options" } }
```

> This degree cannot be combined as an additional major in business administration.

```json
{ "family": "Manual Review",
  "details": { "kind": "PROGRAM_RULE", "direction": "COMBINATION",
               "applies_to": "business administration majors", "effect": "cannot be combined" } }
```

> A graduate-level course may substitute for an upper-division elective with permission of the
> co-directors.

```json
{ "family": "Manual Review",
  "details": { "kind": "DISCRETIONARY", "action": "SUBSTITUTE", "approver": "co-directors" } }
```

> Two courses approved by the undergraduate adviser, with no defined course list provided.

```json
{ "family": "Manual Review",
  "details": { "kind": "NO_POOL", "count": {"op": "eq", "value": 2}, "measure": "courses",
               "reason": "no_enumerated_list", "approver": "undergraduate adviser" } }
```

> Students are required to meet with an academic adviser once each semester through graduation.

```json
{ "family": "Manual Review",
  "details": { "kind": "PROCEDURAL", "procedure": "ADVISING" } }
```

> 440 hours of supervised field experience.

```json
{ "family": "Manual Review",
  "details": { "kind": "HOURS", "count": {"op": "eq", "value": 440}, "measure": "hours",
               "setting": "supervised field experience" } }
```

---

## Out of scope

These appear in catalogue text but are not degree-plan constraints. Emit nothing for them, and
do not route them to `unclassified` either. Where one sentence carries an in-scope fact and an
out-of-scope fact, keep the in-scope fact and drop the rest.

| Drop | Looks like |
|---|---|
| GPA floors | "A GPA of at least 3.0 on all units attempted is required." |
| Minimum grades and retakes | "A grade of C- or higher is required; lower grades must be repeated." |
| Transfer credit and residency | "All upper-division units must be completed in residence." |
| Substitution percentage caps | "Substitutions are limited to 25 percent of the major." |
| Progressive degree (PDP) | "Admission to the progressive degree program requires 64 but fewer than 96 units." |
| Graduate and professional degrees | "The MS in [program] requires 32 units of coursework." |
| Pass/no-pass grading mode | "A maximum of 24 units may be taken pass/no pass." |
| Optional honors tracks | "Acceptance to Thematic Option requires a 3.5 GPA and an interview." |

> Admission to the major is by application, reviewed by a special admissions committee;
> interested students must have a GPA of 3.0 or above.

The GPA figure drops. What remains is a committee-reviewed process:

```json
{ "family": "Manual Review",
  "details": { "kind": "GATE", "stage": "INITIAL_ADMISSION", "basis": "QUALITATIVE_REVIEW",
               "process": "committee-reviewed application" } }
```

When the GPA is one input to a human review rather than a rule of its own ("submit a personal
statement; applicants should have a 3.0"), keep the clause whole as a `QUALITATIVE_REVIEW` gate
instead of splitting it.
