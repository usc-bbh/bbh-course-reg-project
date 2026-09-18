# Four-Year Degree Planner — UI notes

_Francis Ruan, Module 2. Written after the code, from the code._

The app lives in [`degree-planner/`](../degree-planner/). It is a browser-only
static site: no backend, no analytics, no third-party scripts, and exactly one
module allowed to make a network request — `src/data/catalogue.ts`, fetching
public course data that ships with the build.

**This document holds only questions that are still open.** Anything already
answered by a committed contract has been built against that contract instead
of being written up here. The current inventory of inventions is
`grep -rn "GAP(" degree-planner/src`; every entry below traces to one of those
markers, and every marker is a line of code a reviewer can stand next to.

---

## 1. What this app is built on, and where each piece comes from

The planner owns no facts of its own. Each seam below names the file that
defines it, so a change on either side shows up as a failing test rather than a
quiet drift.

| Seam | Owner | Contract | Where the planner reads it |
| --- | --- | --- | --- |
| The parsed report | Abhi (`stars-parser/`) | [`stars-parser/README.md`](../stars-parser/README.md) output block; signature `parseStarsReport(file, { onStatus, onProgress })`, resolving to `null` when it cannot read the file | `src/domain/types.ts` → `ParsedStarsReport`, `src/data/parseStarsReport.ts` |
| The sample student | shared | [`fixtures/stars/mock_stars_report.json`](../fixtures/stars/mock_stars_report.json) | `src/data/sampleStudent.ts`, asserted field-for-field against the committed file in `test/contracts.test.ts` |
| Which tier is reused and which is computed | Natalie (degree-audit engine) | [`docs/reference/03-degree-planner-architecture.md`](reference/03-degree-planner-architecture.md) | `Requirement.tier` + `Requirement.source`, `AnalysisResult.reusedFromReportDated` |
| Block statuses `ok` / `no` / `ip` | shared | [`docs/reference/01-reading-a-stars-report.md`](reference/01-reading-a-stars-report.md) | `StarsBlockStatus`, `src/components/status.tsx` |
| Per-course `source` (`usc` / `transfer_specific` / `transfer_generic`) | Abhi | [`docs/parser-brief.md`](parser-brief.md) §6–7 | `CreditSource`, shown on every history row |
| Course titles, units, offering frequency | Agastya (`catalog/`) | [`catalog/README.md`](../catalog/README.md) v6 file: `terms_data` keyed by term code plus `offering_frequency` | `src/data/catalogue/courses.json` in that exact shape, guarded field-for-field in `src/data/catalogue.ts`, pinned by `test/catalogue.test.ts` |
| The `stars_summary` slice | Tanzil (`validator/`) | [`validator/README.md`](../validator/README.md) — exactly five fields | `toStarsSummary()` in `src/domain/situation.ts` |

Three consequences of those contracts that are easy to get wrong, and that the
tests now pin:

- **`minor` is singular and nullable**, because that is what the parser emits.
  Not a list.
- **`classLevel` is USC's own vocabulary** — `Freshman` / `Sophomore` /
  `Junior` / `Senior` — not a spelling of our own.
- **The parser resolves with `null` on failure; it does not reject.** The UI
  treats `null` as "prompt for manual entry" and a rejection as an unexpected
  error, which are different screens.

## 2. What `analyzePlan` hands back

The live contract is
[`degree-planner/src/data/analyzePlan.ts`](../degree-planner/src/data/analyzePlan.ts)
and the shapes are in
[`degree-planner/src/domain/types.ts`](../degree-planner/src/domain/types.ts).
It is deliberately not copied here: the last version of this document held a
paste of that file and went stale within a day.

The shape follows `docs/reference/03` rather than anything invented:

- Every `Requirement` carries a **`tier`** (`university` / `college` / `major` /
  `minor`) and a **`source`** (`stars` for a reused verdict, `computed` for one
  worked out from catalogue requirements). The five `source: 'stars'` entries
  are the five requirement blocks in the committed fixture, with their `OK` /
  `NO` verdicts carried through unchanged; `test/fixtures.test.ts` fails if a
  block is dropped or if a reused entry claims a tier the doc says we compute.
- `Requirement.tally` uses **STARS' own tally vocabulary** from
  `docs/reference/01` — `UNITS`, `SUB-GROUPS`, `COURSES`, `GPA` — rather than
  assuming every requirement is counted in units. A GPA requirement is not.
- `AnalysisResult.reusedFromReportDated` carries the report's prepared date.
  Reuse means inheriting that date, and `docs/reference/03` says to "carry that
  date through and surface it rather than presenting an old verdict as
  current", so the verdict card prints it and the audit names it.
- `isSample` drives the sample badge, on screen and on paper, and nothing else
  does. When the real engine returns `false` the badge disappears with no change
  to any component.

`test/stubs.test.ts` asserts that two materially different plans produce a
deeply equal result, so the stub cannot quietly grow degree logic.

### The one thing the UI does with the report on its own

`docs/reference/03` closes with the conditions that invalidate reusing a tier.
Two of them are one text edit away in the review form — a change of major that
may cross schools, and a change of catalog year, where "the reused verdict would
be for the wrong year". So the situation keeps `reportBasis`: the major and
catalog year the reused verdicts were read under, and the planner says so when
the student edits away from them
([`reportDrift.ts`](../degree-planner/src/features/situation/reportDrift.ts)).

That comparison is two string equality checks. It decides nothing about any
requirement, and it must not start to.

---

## 3. Still open — Abhi (`stars-parser/`), and Tanzil for P0

### P0 — the shared fixture disagrees with itself, and both of you read it

`fixtures/stars/mock_stars_report.json` states `"classLevel": "Junior"`. Its own
coursework is **36 units** with `"transferUnits": 0`.
[`docs/reference/01`](reference/01-reading-a-stars-report.md) has this as
`[verified]`: *"Class level comes from units earned, not time enrolled. Freshman
is under 32 units, sophomore 32 to 63.9, junior 64 to 95.9, senior 96 and
above."* 36 units is a **sophomore**.

This is not cosmetic. `classLevel` is one of the five fields
`validator/README.md` documents as the `stars_summary` slice, and the validator
gates class-level-restricted courses on it — so the parser test and the
validator test are both asserting against a student who cannot exist. The
planner shows what the report says and computes nothing, so it inherits the
contradiction whichever way it is resolved.

Two ways to fix it, and it is yours to pick: add ~28 units of coursework so the
fixture is really a junior, or change `classLevel` to `"Sophomore"`. The second
is one character of work and changes what the validator's own tests mean, which
is why this needs both of you rather than a quiet edit.

`test/contracts.test.ts` pins all three numbers, so the day the fixture is
fixed that test fails and this section gets deleted.

| # | Question | Why the planner cares | What it does meanwhile |
| --- | --- | --- | --- |
| P1 | **Course-code spacing.** The README's example shows `"BUAD304"`; the committed fixture shows `"CSCI 103"`; `validator/README.md` says codes are normalised to `"DEPT ###"` with one space "everywhere in this module"; `catalog/README.md` says `course_name` is "always `PREFIX NNN` format (space-separated)". Three of four say spaced. Can the parser settle on it? | Every join in this project is on a course code. A mismatch does not throw — it silently fails to match, and a student sees a requirement as unmet when it is met. | Normalises on the way in (`src/domain/uscTerms.ts`), which is a workaround, not a fix. |
| P2 | **Course-code suffixes.** Does the parser keep USC's trailing `L` and `g` (`CSCI 103L`, `MATH 125g`)? The fixture has neither; the Schedule of Classes has `CSCI 102L`, `BISC 120L`. | Same failure as P1, but harder to spot, because most codes match and a handful do not. | Codes are used as given. |
| P3 | **Per-course `source`.** `docs/parser-brief.md` §6 asks for `usc` / `transfer_specific` / `transfer_generic` on every row; the README's output block and the committed fixture do not have it yet. | §7's own words: treating generic credit as able to fill requirements "would understate how much a student has left to do". The planner marks the two kinds differently on every history row and cannot without this field. | The sample student carries two transfer rows with `source` set by hand. |
| P4 | **Entry term.** `docs/reference/01` lists "term of USC entrance" among the report's pertinent data, but the parser's output has no field for it. | It decides where the year columns start. A spring entrant's four academic years are not a fall entrant's. | Reads an optional `entryTerm` if present, otherwise takes the earliest term on the report. |
| P5 | **The report's prepared date.** Not in the output shape. | `docs/reference/03` requires surfacing it whenever a verdict is reused. The UI has the slot and prints it. | Hard-coded in `analyzePlan.ts` as `SAMPLE_REPORT_PREPARED`. |
| P6 | **A stable id per requirement block.** `requirements[].label` is free text off the report. | Cross-highlighting, saved preferences and any "this one is my problem" affordance need identity that survives re-parsing. Two reports for the same student may word a block differently. | Ids assigned by hand in `analyzePlan.ts`. |
| P7 | **Student name.** The output has no name field, and `fixtures/stars/` holds redacted reports. Is that permanent? | Only so a printed plan says whose it is. It is never exported in a filename and never leaves the device. | Blank after an upload; the *sample* student gets a made-up name. |

## 4. Still open — Natalie (degree-audit engine)

| # | Question | Why the planner cares | What it does meanwhile |
| --- | --- | --- | --- |
| A1 | **Which tier does a reused block belong to?** The report states a verdict per block, not whether the block is a university, college, major or minor rule. | `docs/reference/03` splits the work by tier, so something has to make that call before the engine knows what to recompute. | Tagged by hand from the five fixture labels. |
| A2 | **Category gaps.** `docs/reference/03` says these should "degrade gracefully — let the student nominate which planned course they believe satisfies it, and mark the result unverified". No field in the result carries a nomination. | It is a UI affordance the UI cannot build against nothing: it needs somewhere to send the nomination and somewhere to read back `unverified`. | Not built. Requirements are shown as outstanding with their stated gap. |
| A3 | **`IP`.** It is not in the STARS legend; `docs/reference/01` records it as inferred and unconfirmed — "appears to mean satisfied only if in-progress courses are counted". | It is one of three statuses the panel renders, and the difference between "done" and "done if this term goes well" is the whole point of a planner. | Rendered as in-progress, on that reading. |
| A4 | **Cross-school scope.** `docs/reference/03` says a cross-school what-if invalidates reuse and "should warn and route the student to an advisor". Nothing in the data says which school a major belongs to. | The planner already detects that the student edited their major away from the report; it cannot tell whether that crossed a school boundary, which is the part that matters. | Warns on any change of major, and says an advisor has to confirm it. |
| A5 | **Are transfer units inside the headline unit count?** | It is the one progress number on screen, and this app is not allowed to work it out itself. | Shown as the engine returns it: `120 of 128`. |

## 5. Still open — Agastya (`catalog/`)

| # | Question | Why the planner cares | What it does meanwhile |
| --- | --- | --- | --- |
| C1 | **A searchable index.** `catalog/README.md` plans per-course-per-term hosting for V1 (`/catalog/20263/CSCI-104.json`) so React fetches only the courses a student picked. The planner's course picker is a search box: it needs a list *before* the student has picked anything. | Without an index the picker can only offer courses it already knows, which is the sample file it ships with. | A hand-made ~40-course file in the documented v6 shape, fetched in one request. |
| C2 | **Terms outside the scrape window.** The scrape covers Spring 2024 – Fall 2026. The sample student's history starts Fall 2022 and their plan ends Spring 2027; a four-year plan made today runs past the window by construction. | `offering_frequency` is the source for "CSCI 401 has only ever run in fall terms". For a term outside the window there is no answer, and "no data" must not read as "not offered". | The frequency labels in the sample file are invented, and the UI renders the warning without checking it. |
| C3 | **v5/v6 data.** The v6 scrape "has not yet completed a full successful run"; v5 is missing ~30 departments and is not committed. Running it needs USC VPN. | A picker that silently lacks FBE or GERO looks broken to the student in those departments, not incomplete. | Sample data only, in the documented v6 shape. Swapping in the real file is a URL change in `src/data/catalogue.ts` and nothing else — `test/catalogue.test.ts` checks the sample against the README rather than against what the UI happens to read. |
| C4 | **What counts as `every_semester`?** The README names the four `frequency_label` values but not the counts that map to them. | Only if the label is ever shown as words to a student. Right now nothing is. | The sample's thresholds are ours: 6 → `every_semester`, 4–5 → `most_semesters`, 2–3 → `occasionally`, 1 → `rarely`. |
| C5 | **The label cannot express seasonality.** A fall-only course and a course that ran three scattered terms both come out `occasionally`. | The planner's only blocking warning is "CSCI 401 has only ever run in fall terms". That fact is in `terms_offered`, not in the label — worth confirming that is intentional before anyone builds on the label. | Reads `terms_offered`. |

## 6. Still open — mine (`catalogue_scraper/`, Module 2)

Not a question for anyone else; recorded here because the planner depends on it.

- **Programme lists.** The major, minor and catalog-year dropdowns have no
  source. `catalogue_scraper/` has 470 programme files for **2026-2027 only**,
  so a student on the fixture's own `2023-2024` catalog year has nothing to pick
  from. The lists live in `src/data/catalogue/programmes.ts`, bundled rather
  than fetched — they are not scrape data, so they should not ride along in the
  course file or vanish when that request fails. Every one of those fields keeps
  the student's own value even when the list has never heard of it.
- **The requirements corpus** behind `source: 'computed'` requirements is the
  same scrape. Until Natalie's engine consumes it, the computed half of the
  audit is three hand-written entries.

## 7. Still open — Tanzil (`validator/`)

One seam, no dependency. The planner does not call the validator and should not:
"can I register for these classes next term" is a different tool.
`toStarsSummary()` produces the exact five fields `validator/README.md`
documents so the same student can be handed across without a translation step.

`toStarsSummary()` takes the **parsed report**, not the planner's situation, on
purpose: the slice needs a real `gpa` for GPA-threshold prerequisites and the
planner keeps no GPA, because nothing on screen uses one. Building the slice
from a situation would have meant inventing that number. Nothing here is open —
it is recorded so nobody "simplifies" the signature later.

See P0 above, which is as much yours as Abhi's.

---

## The six to raise first

1. **Abhi and Tanzil — P0, the fixture's class level.** Two committed test
   suites assert against a student whose units and class level contradict each
   other. Cheapest possible fix, and it is wrong in the shared file, not in any
   one module.
2. **Abhi — P1/P2, course codes.** Everything joins on them, and a mismatch is
   silent. One decision unblocks three modules.
3. **Abhi — P3, per-course `source`.** Already specified in the brief; without
   it the planner cannot tell credit that fills a requirement from credit that
   only adds units.
4. **Agastya — C1, a searchable index.** Per-course-per-term files serve the
   validator's shape well and leave the planner's picker with nothing to search.
   Worth settling before V1 hosting is built rather than after.
5. **Natalie — A1, tiering of reused blocks.** `docs/reference/03` is the design
   the planner is built to; the one thing it does not say is who assigns a tier.
6. **Natalie — A2, category-gap nominations.** The graceful degradation the doc
   asks for is a UI feature with no field to put it in. It is cheap to add to
   the result shape now and expensive to retrofit.
