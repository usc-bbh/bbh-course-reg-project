# Four-Year Degree Planner — UI notes

_Written after the code, from the code. Where this document and
`degree-planner/` disagree, the code is right and this document is wrong._

The app lives in [`degree-planner/`](../degree-planner/). It is a browser-only
static site: no backend, no analytics, no third-party scripts, and exactly one
network request in the whole app — `src/data/catalogue.ts` fetching a public
course list that ships with the build.

---

## 1. What the page captures from the student

These are the facts, not the controls. How each one is collected — dropdown,
text field, editable row — is an implementation detail and has already changed
once.

| Fact | Notes |
| --- | --- |
| Name | Only so the printed plan says whose it is. Never leaves the device, and never appears in an exported filename. |
| Major | One, chosen from the catalogue sample or typed if the list has not loaded. |
| Minors | A list, not a single value. The sample student has one; the shape allows several. |
| Catalogue year | `2024-2025`. Determines which requirements apply. |
| Class standing | First / second / third / fourth year. |
| Entry term | A season **and** a year. The season matters: it decides where the four year columns start. |
| Transfer units | One total. Not mapped to specific courses. |
| Completed coursework | Per course: code, title, units, **the term it was taken in**, and the grade. |
| In-progress coursework | Same, minus the grade. Kept separate from completed work rather than inferred from a missing grade. |
| The proposed plan | Per planned term: the courses in it. Terms carry a season, a year and a status. |

Two of these are load-bearing in a way that is easy to miss:

- **The term on each completed course.** Without it the timeline cannot place
  history, and the app would have to guess which terms to lock. It never guesses
  — a term is locked because its `status` says so, never because of today's
  date.
- **The entry term's season.** A spring entrant's four academic years are not
  the same four as a fall entrant's.

Everything the student enters is stored under the `plansc.degreePlanner.`
prefix in `localStorage` and nowhere else. "Clear all data" removes keys with
that prefix and leaves every other app on the origin alone.

---

## 2. The fixed object `analyzePlan` returns

Copied verbatim from
[`degree-planner/src/data/analyzePlan.ts`](../degree-planner/src/data/analyzePlan.ts).
This is the statement of what the real analysis layer has to hand back. Every
`GAP(analysis)` comment in that file is a question for whoever builds it.

```ts
const REQUIREMENTS: Requirement[] = [
  {
    id: 'req-units-128',
    name: '128-unit minimum',
    category: 'University',
    status: 'unsatisfied',
    reason:
      'This plan reaches 120 units counted toward the degree. USC requires 128, so 8 more are needed before Spring ' +
      yearOf(TERM.spring4) +
      '.',
    satisfiedBy: [],
    unitsCounted: 120,
    unitsRequired: 128,
  },
  {
    id: 'req-core-electives',
    name: 'Core electives',
    category: 'Major',
    status: 'unsatisfied',
    reason:
      'Four 300- or 400-level CSCI courses are required, for at least 16 units. The plan has two: CSCI 402 and CSCI 420.',
    satisfiedBy: [
      { code: 'CSCI 402', termId: TERM.fall4 },
      { code: 'CSCI 420', termId: TERM.spring4 },
    ],
    unitsCounted: 8,
    unitsRequired: 16,
  },
  {
    id: 'req-general-education',
    name: 'General education',
    category: 'University',
    status: 'unsatisfied',
    reason:
      'Three general education categories are still open. The plan has one GE course, GESM 120g, and two more are needed.',
    satisfiedBy: [{ code: 'GESM 120g', termId: TERM.spring3 }],
    unitsCounted: 4,
    unitsRequired: 20,
  },
  {
    id: 'req-composition',
    name: 'Composition and writing',
    category: 'University',
    status: 'in-progress',
    satisfiedBy: [
      { code: 'WRIT 150', termId: TERM.fall1 },
      { code: 'WRIT 340', termId: TERM.fall3 },
    ],
    unitsCounted: 4,
    unitsRequired: 8,
  },
  {
    id: 'req-cs-core',
    name: 'Computer science core',
    category: 'Major',
    status: 'in-progress',
    satisfiedBy: [
      { code: 'CSCI 102L', termId: TERM.fall1 },
      { code: 'CSCI 103L', termId: TERM.fall1 },
      { code: 'CSCI 104L', termId: TERM.spring1 },
      { code: 'CSCI 170', termId: TERM.spring1 },
      { code: 'CSCI 201', termId: TERM.fall2 },
      { code: 'CSCI 270', termId: TERM.spring2 },
      { code: 'CSCI 310', termId: TERM.spring2 },
      { code: 'CSCI 350', termId: TERM.fall3 },
      { code: 'CSCI 356', termId: TERM.fall3 },
      { code: 'CSCI 353', termId: TERM.spring3 },
      { code: 'CSCI 360', termId: TERM.spring3 },
      { code: 'CSCI 401', termId: TERM.spring4 },
    ],
    unitsCounted: 38,
    unitsRequired: 46,
  },
  {
    id: 'req-mathematics',
    name: 'Mathematics',
    category: 'Pre-major',
    status: 'satisfied',
    satisfiedBy: [
      { code: 'MATH 125g', termId: TERM.fall1 },
      { code: 'MATH 126g', termId: TERM.spring1 },
      { code: 'MATH 226g', termId: TERM.fall2 },
      { code: 'MATH 225', termId: TERM.spring2 },
    ],
    unitsCounted: 16,
    unitsRequired: 16,
  },
  {
    id: 'req-sciences',
    name: 'Life and physical sciences',
    category: 'Pre-major',
    status: 'satisfied',
    satisfiedBy: [
      { code: 'PHYS 151Lg', termId: TERM.spring1 },
      { code: 'BISC 120Lg', termId: TERM.fall2 },
    ],
    unitsCounted: 8,
    unitsRequired: 8,
  },
  {
    id: 'req-statistics',
    name: 'Statistics and probability',
    category: 'Pre-major',
    status: 'satisfied',
    satisfiedBy: [{ code: 'EE 364', termId: TERM.spring2 }],
    unitsCounted: 4,
    unitsRequired: 4,
  },
];

const WARNINGS: PlanWarning[] = [
  {
    id: 'warn-capstone-term',
    severity: 'blocking',
    message:
      'CSCI 401 is offered in the fall only, and this plan places it in Spring ' +
      yearOf(TERM.spring4) +
      '. The capstone will not be available that term.',
    course: { code: 'CSCI 401', termId: TERM.spring4 },
    termId: TERM.spring4,
  },
  {
    id: 'warn-seminar-late',
    severity: 'warning',
    message:
      'GESM 120g is a first-year seminar. Taking it in your third year is allowed, but seats go to first-year students first.',
    course: { code: 'GESM 120g', termId: TERM.spring3 },
    termId: TERM.spring3,
  },
  {
    id: 'warn-final-term-load',
    severity: 'warning',
    message:
      'The last three terms each carry 12 units. At that pace the plan finishes 8 units short of the 128-unit minimum.',
    termId: TERM.spring4,
  },
  {
    id: 'warn-transfer-units',
    severity: 'info',
    message:
      'Your 8 transfer units count toward the 128-unit minimum. They have not been matched to a specific requirement.',
  },
];

const FIXED_RESULT: AnalysisResult = {
  verdict: 'not-yet',
  headline:
    'This plan does not reach the degree yet: three requirements are unmet and one course is scheduled in a term it is not offered.',
  unitsCounted: 120,
  unitsRequired: 128,
  // The plan echoed back, per the brief. The UI does not render this.
  terms: buildTimeline(sampleSituation, samplePlan),
  requirements: REQUIREMENTS,
  warnings: WARNINGS,
  isSample: true,
};
```

The shapes these fill in are in
[`degree-planner/src/domain/types.ts`](../degree-planner/src/domain/types.ts).
Two choices in there are deliberate and worth keeping:

- **`isSample` drives the sample badge.** The badge — *"Sample results. These do
  not reflect your edits yet."* — is rendered from this field alone, on screen
  and on the printed page. When the real layer lands and returns `false`, the
  badge disappears with no change to any component.
- **The timeline is drawn from the store, not from `result.terms`.** The result
  echoes the plan back, per the brief, and the UI ignores it. Two sources of
  truth for one plan is how a UI starts lying. Whether that echo should exist at
  all is an open question below.

---

## 3. What I needed and couldn't get

Built from `grep -rn "GAP(" degree-planner/src`, grouped by who can answer it.
Every item is something the UI actually hit while being built, not a
speculative wish list.

### For the STARS parser — Abhi and Agastya

| What the UI needs | Why | What is faked meanwhile |
| --- | --- | --- |
| The **term** each completed course was taken in | It is the only way to lay history out on a timeline and lock it. Without it the app would have to infer the past from today's date, which it refuses to do. | Every fixture course carries a `termId` like `fall-2025`. |
| In-progress coursework **as a separate list** from completed coursework | In-progress terms render locked but ungraded. "No grade" and "grade not parsed" are different facts and must not collapse into one. | Two arrays on the parsed situation. |
| **Entry term** — season and year | It decides where the four year columns start. Nothing in the sample reports we have states it directly. | Hard-coded on the sample student; defaulted from a constant for manual entry. |
| **Transfer units** as a single number | Shown in the situation summary and mentioned by the analysis result. | `8` on the sample student. |
| **Minors as a list** | The UI supports several; every sample we have carries at most one, and `null` when there is none. | `['Mathematics']`. |
| What happens when a completed course's term **cannot be read** | The timeline has nowhere to put it. | It is dropped from the timeline and still shown in the review form, so the student can correct it. This is a guess about what students expect. |
| Whether a report ever implies a **proposed plan** | It does not, as far as we can tell — a report says what a student has done. So an upload lands on an empty four-year scaffold, and only the sample student arrives with a plan already in it. | Empty fall and spring terms for four years from the entry term. |

### For the analysis layer

| What the UI needs | Why | What is faked meanwhile |
| --- | --- | --- |
| Every warning carries a **course code and a term id** | Without them the timeline cannot highlight what a warning is about, and the warning is just a sentence. | Four fixed warnings, three of which carry references. |
| Every unsatisfied requirement carries a **student-readable `reason`** | "Unsatisfied" alone gives a student nothing to act on. The reason is the most-read text in the panel. | A written sentence per unmet requirement. |
| A fixed **`category` vocabulary** for requirements | The panel groups by it, and inconsistent categories would make the grouping nonsense. | We invented `University` / `Pre-major` / `Major` / `Minor`. The real layer should own this list. |
| `satisfiedBy` referencing courses **by code and term** | The same course code can legitimately appear in two terms of a draft plan, and highlighting the wrong one is worse than highlighting neither. | `{ code, termId }` pairs throughout. |
| Whether **transfer units are inside `unitsCounted`** | It is the one progress figure a student sees, and the app is not allowed to work the number out itself. | `120 of 128`, with a note warning that transfer units are not matched to a requirement. |
| `isSample` **set to `false`** by the real implementation | It is the only thing driving the sample badge. | `true`. |
| Whether the echoed **`terms`** array is authoritative | If the real layer may reorder or annotate the plan it was given, the UI needs to know. If it may not, we would rather drop the field than keep two sources of truth. | The field exists, is populated, and is ignored. |

### For catalogue data

| What the UI needs | Why | What is faked meanwhile |
| --- | --- | --- |
| A real source of **course titles and unit counts** | The picker can only offer what it knows about. | About forty USC courses typed by hand into `src/data/catalogue/courses.json`. |
| **Which terms a course is offered in** | The analysis layer already warns about a course placed in a term it is not offered. The two need to agree on where that fact comes from. | Nothing. The UI renders the warning and does not check it. |
| The lists of **majors, minors and catalogue years** a student can pick from | They are the first three fields of the review form. | Invented lists in the same JSON file. |

### Other

| What the UI needs | Why | What is faked meanwhile |
| --- | --- | --- |
| What a **manual-entry** student should see before typing anything | Every field needs a starting value, and a wrong default is worse than an empty one. | Entry term seeded from `PLAN_BASE_YEAR` and catalogue year from the sample. Both editable, both guesses. |
| The **official USC lockup artwork** | The header carries the university mark, and the app may not fetch it from another origin. | The shield and torch are drawn as inline SVG from the lockup on USC's registration pages. Someone with brand-portal access should drop the real file in and replace `<UscShield>`. |

---

## The five to raise first

1. **Abhi and Agastya:** does the parser emit the term for every completed
   course, and in-progress work as its own list? Everything else here is
   cosmetic next to these two.
2. **Abhi and Agastya:** does a STARS report state the entry term, or does the
   student have to tell us?
3. **Analysis layer:** warnings and requirements need course-plus-term
   references, or the cross-highlighting that makes the audit useful cannot
   exist.
4. **Analysis layer:** is `unitsCounted` inclusive of transfer units, and does
   the echoed `terms` array mean anything?
5. **Catalogue:** where do offered terms come from? It is the fact behind the
   only blocking warning we currently show.
