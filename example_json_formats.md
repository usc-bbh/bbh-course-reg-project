# JSON Schema Reference

Schemas for all data flowing though. All field names are **snake_case**. Course IDs follow USC format with a space: `"CSCI 201"` not `"CSCI201"`.

**Owners**

| Schema | Owner | Where it lives |
|---|---|---|
| F1: Course record | Francis | Server SQL DB |
| F2: Major requirements  | Francis | Server SQL DB |
| F3: Minor requirements  | Francis | Server SQL DB |
| F4: GE requirements  | Francis | Server SQL DB |
| A1: Course availability | Agastya | Server SQL DB |
| V1: Stars Student record | Avi (parser output) | Client-side only. Never sent to server. |
| N1: Enriched course object | Natalie (engine, derived) | In memory only. Not stored. |
| N2: Degree plan output | Natalie (engine, derived) | In memory only. Not stored. |


## Shared field reference

Fields that appear in more than one schema. All must be consistent in type and format across every module that uses them.

| Field | Type | Appears in | Description |
|---|---|---|---|
| `catalog_year` | `string` | F2, F3, F4, V1, N2 | Academic year in `"YYYY-YYYY"` format. Determines which version of requirements to apply. Example: `"2023-2024"` |
| `category_id` | `string` | F4.categories, V1.requirements_status (as key) | GE requirement category identifier. Values in F4 must exactly match the keys used in V1.requirements_status. |
| `concentration_id` | `string \| null` | V1, F2 (planned) | Concentration or emphasis identifier. Required for Marshall students where emphasis determines the elective pool. Null if no concentration declared. |
| `coreqs` | `string[]` | F1, N1 | Flat list of course IDs that must be completed in the same semester or earlier. Empty array if none. |
| `course_id` | `string` | F1, A1, V1.completed_courses, V1.in_progress_courses, N1, N2.plan.courses | Unique course identifier in `"[DEPT] [NUMBER]"` format with a space. Example: `"CSCI 201"`. F1, A1, and V1 all join on this field. Format must be identical across all three modules. |
| `course_type` | `string` | F1, N1 | Requirement type label. Values: `"major-core"`, `"major-elective"`, `"GE"`, `"free-elective"`. V2 only (soft constraint S3). Treat as optional in V1. |
| `elective_groups` | `object[]` | F2, F3, F4.categories | Array of pick-N elective requirement groups. Each object contains `group_id`, `required_count`, and `options`. |
| `grade` | `string` | V1.completed_courses | Letter grade received. Example: `"A"`, `"B+"`, `"C"` |
| `group_id` | `string` | F2.elective_groups, F3.elective_groups, F4.categories.elective_groups | Unique identifier for an elective group within a manifest. Example: `"tech-electives"` |
| `major_id` | `string` | F2, V1 | Major identifier. V1 sends this value to the server to fetch the corresponding F2 manifest. Example: `"CSCI-BS"` |
| `minor_id` | `string` | F3 (top-level field), V1.minor_ids (array values) | Minor identifier. Each value in V1's `minor_ids` array must match a `minor_id` in a corresponding F3 object. Example: `"CS-minor"` |
| `offered_every_year` | `boolean` | A1, N1 | True if this course runs every academic year. False indicates irregular or infrequent offering. The solver checks `offering_history` to estimate when it will next run. |
| `offered_semesters` | `string[]` | A1, N1 | Semesters this course is offered. Values: `"fall"`, `"spring"`. Example: `["fall", "spring"]` or `["fall"]` |
| `options` | `string[]` | F2.elective_groups, F3.elective_groups, F4.categories.elective_groups | Course IDs eligible to satisfy this elective group requirement. Must never be empty. An empty options list means the solver cannot verify the requirement is satisfiable. |
| `prereqs` | `string[][]` | F1, N1 | CNF structure: outer array is AND, inner array is OR. See prereq structure note below. |
| `required_count` | `number` | F2.elective_groups, F3.elective_groups, F4.categories.elective_groups | Number of courses the student must choose from this group's `options` list. |
| `required_courses` | `string[]` | F2, F3, F4.categories | Course IDs the student must complete. No choice; all required. |
| `required_for` | `string[]` | F1, N1 | Requirement category IDs this course satisfies. Values must exactly match keys in F2.unit_thresholds and V1.requirements_status. |
| `required_units` | `number` | F2.elective_groups, F3.elective_groups | Minimum total units that must come from this group's options. |
| `semester` | `string` | A1.offering_history, V1.completed_courses, V1.in_progress_courses, N2.plan | `"fall"` or `"spring"`. Always lowercase. |
| `semesters_completed` | `number` | V1 | Integer count of semesters already completed at USC. The solver uses this to compute the remaining time horizon: `8 - semesters_completed`. |
| `title` | `string` | F1, N1, N2.plan.courses | Full course title. Example: `"Data Structures"` |
| `total_units_required` | `number` | F2, F3 | Total units required to complete this major or minor. |
| `unit_thresholds` | `object` | F2, F3 | Unit requirements broken down by category. Keys must exactly match V1.requirements_status keys and F1.required_for values. |
| `units` | `number` | F1, V1.completed_courses, V1.in_progress_courses, N1, N2.plan.courses | Credit unit count for a single course. |
| `year` | `number` | A1.offering_history, V1.completed_courses, V1.in_progress_courses, N2.plan | 4-digit calendar year. Example: `2023` |

---

| # | Fields that must match | Between |
|---|---|---|
| 1 | `course_id` format | F1, A1, V1.completed_courses, V1.in_progress_courses |
| 2 | `catalog_year` format | F2, F3, F4, V1. Must all use `"YYYY-YYYY"` |
| 3 | `major_id` value | V1.major_id must match a F2.major_id on the server |
| 4 | `minor_ids` values | V1.minor_ids[*] must each match a F3.minor_id on the server |
| 5 | `required_for` values in F1 | Must match keys in F2.unit_thresholds, which must match keys in V1.requirements_status |
| 6 | `category_id` values in F4 | Must match keys in V1.requirements_status |

---

## Prereq structure: CNF (Conjunctive Normal Form)

The outer array is AND. Every inner list must be satisfied.
The inner array is OR. At least one course in the group must be completed.

```
prereqs: [
  ["CSCI 104"],              AND: must have completed CSCI 104
  ["MATH 225", "MATH 229"]   AND: must have completed MATH 225 OR MATH 229
]
```

No prereqs: `[]`
Single hard prereq: `[["CSCI 103"]]`

In BIP: each inner OR-group becomes a sum constraint of 1 or more over completed-course flags.
In CP-SAT: each inner OR-group becomes a domain restriction on the target course's semester.

---

## F1: Course record

One record per course. Satisfies constraints C1, C2, C3, C4, C5, F1, S2, S3.

```json
{
  "course_id": "CSCI 201",
  "title": "Data Structures",
  "units": 4,
  "prereqs": [
    ["CSCI 104"],
    ["MATH 225", "MATH 229"]
  ],
  "coreqs": [],
  "required_for": ["CSCI-BS-core"],
  "course_type": "major-core"
}
```

| Field | Type | Notes |
|---|---|---|
| `course_id` | `string` | Join key. Must match A1 and V1 exactly. |
| `title` | `string` | Full course name |
| `units` | `number` | Credit hours |
| `prereqs` | `string[][]` | CNF structure. See prereq note above. |
| `coreqs` | `string[]` | Empty array if none |
| `required_for` | `string[]` | Must match F2.unit_thresholds keys and V1.requirements_status keys |
| `course_type` | `string` | V2 only (S3). Treat as optional. |

---

## F2: Major requirements 

One record per major. Separate object from F1 course records. The engine uses this to derive the pending course list. Satisfies C0, C11.

```json
{
  "major_id": "CSCI-BS",
  "major_name": "Computer Science (B.S.)",
  "catalog_year": "2023-2024",
  "total_units_required": 128,
  "required_courses": [
    "CSCI 103",
    "CSCI 104",
    "CSCI 201",
    "CSCI 270",
    "CSCI 350",
    "CSCI 356",
    "CSCI 360",
    "CSCI 401"
  ],
  "elective_groups": [
    {
      "group_id": "tech-electives",
      "group_name": "Technical electives",
      "required_count": 3,
      "required_units": 12,
      "options": [
        "CSCI 420",
        "CSCI 422",
        "CSCI 455",
        "CSCI 467",
        "CSCI 480"
      ]
    }
  ],
  "unit_thresholds": {
    "major_core": 36,
    "upper_division": 16,
    "total": 128
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `major_id` | `string` | Primary key. Must match V1.major_id. |
| `major_name` | `string` | Human-readable name |
| `catalog_year` | `string` | Must match V1.catalog_year |
| `total_units_required` | `number` | Total units needed for graduation |
| `required_courses` | `string[]` | Must take all. Course IDs in USC space format. |
| `elective_groups` | `object[]` | Pick-N groups |
| `unit_thresholds` | `object` | Keys must match F1.required_for values and V1.requirements_status keys |

---

## F3: Minor requirements manifest

One record per minor. Same structure as F2, scoped to a minor.

```json
{
  "minor_id": "CS-minor",
  "minor_name": "Computer Science (minor)",
  "catalog_year": "2023-2024",
  "total_units_required": 20,
  "required_courses": [
    "CSCI 103",
    "CSCI 104"
  ],
  "elective_groups": [
    {
      "group_id": "cs-minor-electives",
      "group_name": "CS minor electives",
      "required_count": 2,
      "required_units": 8,
      "options": [
        "CSCI 201",
        "CSCI 270",
        "CSCI 350"
      ]
    }
  ],
  "unit_thresholds": {
    "total": 20
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `minor_id` | `string` | Primary key. Must match values in V1.minor_ids. |
| `catalog_year` | `string` | Must match V1.catalog_year |
| `unit_thresholds` | `object` | Keys must match V1.requirements_status keys |

---

## F4: GE requirements 

One record per catalog year. Major-independent.

```json
{
  "catalog_year": "2023-2024",
  "total_ge_units_required": 12,
  "categories": [
    {
      "category_id": "GE-writing",
      "category_name": "Writing",
      "required_units": 4,
      "required_courses": ["WRIT 150"],
      "elective_groups": []
    },
    {
      "category_id": "GE-quantitative",
      "category_name": "Quantitative reasoning",
      "required_units": 4,
      "required_courses": [],
      "elective_groups": [
        {
          "group_id": "GE-quant-options",
          "required_count": 1,
          "options": ["MATH 118", "MATH 125", "MATH 126", "MATH 129"]
        }
      ]
    },
    {
      "category_id": "GE-diversity",
      "category_name": "Diversity and pre-industrial societies",
      "required_units": 4,
      "required_courses": [],
      "elective_groups": [
        {
          "group_id": "GE-diversity-options",
          "required_count": 1,
          "options": ["TODO: needs course list from Francis"]
        }
      ]
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `catalog_year` | `string` | Must match V1.catalog_year |
| `total_ge_units_required` | `number` | Total GE units needed |
| `categories[].category_id` | `string` | Must match keys in V1.requirements_status |
| `categories[].elective_groups[].options` | `string[]` | Must not be empty. GE-diversity options are currently a TODO. |

---

## A1: Course availability

One record per course. Joined to F1 at runtime by the engine on `course_id`.

```json
{
  "course_id": "CSCI 201",
  "offered_semesters": ["fall", "spring"],
  "offered_every_year": true,
  "offering_history": [
    { "semester": "fall",   "year": 2023, "sections": 3 },
    { "semester": "spring", "year": 2023, "sections": 2 },
    { "semester": "fall",   "year": 2022, "sections": 3 },
    { "semester": "spring", "year": 2022, "sections": 1 }
  ]
}
```

Edge cases:

```json
{ "course_id": "CSCI 499", "offered_semesters": ["fall"], "offered_every_year": true, "offering_history": [] }
{ "course_id": "CSCI 495", "offered_semesters": ["spring"], "offered_every_year": false,
  "offering_history": [{ "semester": "spring", "year": 2022, "sections": 1 }] }
```

| Field | Type | Notes |
|---|---|---|
| `course_id` | `string` | Join key. Must match F1 exactly. |
| `offered_semesters` | `string[]` | Constraint C6 input. Values: `"fall"`, `"spring"` |
| `offered_every_year` | `boolean` | False means check offering_history to estimate next run. |
| `offering_history` | `object[]` | Used to derive frequency labels. Agastya has 6 terms (Spring 2024 to Fall 2026). |

---

## V1: Student record

Output of Avi's STARS parser. Lives client-side only. Never transmitted to server (FERPA).

```json
{
  "major_id": "CSCI-BS",
  "minor_ids": ["CS-minor"],
  "concentration_id": null,
  "catalog_year": "2023-2024",
  "class_level": "junior",
  "gpa_overall": 3.4,
  "upper_division_gpa": 3.84,
  "semesters_completed": 4,
  "completed_courses": [
    {
      "course_id": "CSCI 103",
      "grade": "A",
      "semester": "fall",
      "year": 2022,
      "units": 4
    },
    {
      "course_id": "CSCI 104",
      "grade": "C",
      "semester": "spring",
      "year": 2023,
      "units": 4
    }
  ],
  "in_progress_courses": [
    {
      "course_id": "CSCI 201",
      "semester": "spring",
      "year": 2024,
      "units": 4
    }
  ],
  "transfer_units": 0,
  "requirements_status": {
    "major_core":      { "units_completed": 16, "units_required": 36 },
    "upper_division":  { "units_completed": 8,  "units_required": 16 },
    "GE-writing":      { "units_completed": 4,  "units_required": 4  },
    "GE-quantitative": { "units_completed": 0,  "units_required": 4  }
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `major_id` | `string` | Sent to server to fetch F2. Must match a F2.major_id. |
| `minor_ids` | `string[]` | Array, supports multiple minors. Each value must match a F3.minor_id. |
| `concentration_id` | `string \| null` | Required for Marshall students. Null if not declared. |
| `catalog_year` | `string` | Used to fetch the correct version of F2, F3, F4. |
| `semesters_completed` | `number` | Constraint C10. Bounds the solver time horizon. |
| `completed_courses[].grade` | `string` | Letter grade received. |
| `completed_courses[].course_id` | `string` | Join key. Must match F1 and A1 format. |
| `requirements_status` | `object` | Keys must match F2.unit_thresholds keys and F4.category_id values exactly. |

---

## N1: Enriched course object

Derived by the engine at runtime. Join of F1 and A1 on `course_id`. Never stored. Rebuilt per request. This is the object the solver operates on directly.

```json
{
  "course_id": "CSCI 201",
  "title": "Data Structures",
  "units": 4,
  "prereqs": [
    ["CSCI 104"],
    ["MATH 225", "MATH 229"]
  ],
  "coreqs": [],
  "required_for": ["CSCI-BS-core"],
  "course_type": "major-core",
  "offered_semesters": ["fall", "spring"],
  "offered_every_year": true
}
```

All fields inherited from F1 and A1. The engine produces one N1 object per pending course before running the solver. F1 and A1 are never passed to the solver directly.

---

## N2: Degree plan output

Produced by the engine after the solver runs. Consumed by Module 4B (next-semester validator) and Module 6 (frontend UI). Not stored. Regenerated on each request.

```json
{
  "generated_at": "2024-03-15",
  "catalog_year": "2023-2024",
  "semesters_remaining": 4,
  "plan": [
    {
      "semester": "fall",
      "year": 2024,
      "semester_index": 5,
      "courses": [
        { "course_id": "CSCI 201", "title": "Data Structures",            "units": 4 },
        { "course_id": "CSCI 270", "title": "Introduction to Algorithms", "units": 4 },
        { "course_id": "WRIT 340", "title": "Advanced Writing",           "units": 4 },
        { "course_id": "MATH 407", "title": "Probability Theory",         "units": 4 }
      ],
      "total_units": 16,
      "flags": []
    },
    {
      "semester": "spring",
      "year": 2025,
      "semester_index": 6,
      "courses": [
        { "course_id": "CSCI 350", "title": "Operating Systems",              "units": 4 },
        { "course_id": "CSCI 356", "title": "Computer Systems Organization",  "units": 4 },
        { "course_id": "ITP 101",  "title": "Intro to Information Technology","units": 3 }
      ],
      "total_units": 11,
      "flags": ["unit_threshold_low"]
    }
  ],
  "flags": [
    {
      "id": "F1",
      "type": "unit_threshold_low",
      "semester_index": 6,
      "message": "Spring 2025 is below 12 units (11 units scheduled)"
    }
  ]
}
```

| Flag type | ID | Trigger |
|---|---|---|
| `unit_threshold_low` | F1 | Semester total < 12 units |
| `exceeds_8_semesters` | F2 | Solver cannot fit all pending courses within remaining window |

---

## D-clearance Flag

D-clearance is not a solver constraint and is not checked by the degree plan engine. After N2 is generated, Module 4B reads the plan and checks any flagged courses against Tanzil's separate D-clearance JSON. The UI surfaces a pop-up to the student for any course in their next-semester plan that requires departmental clearance.

The `d_clearance` field does not appear in F1, N1, or anywhere in the engine schemas. See Tanzil's D-clearance JSON for schema details.

---
