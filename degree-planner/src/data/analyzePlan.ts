import type { AnalysisInput, AnalysisResult, PlanWarning, Requirement } from '../domain/types';
import { SAMPLE_REPORT_PREPARED } from './sampleStudent';

/**
 * STUB. Ignores the situation and the plan it is given and returns the same
 * result every time.
 *
 * The real degree-audit engine is Natalie's (`catalogue_scraper/README.md`
 * names her as its owner and primary consumer of the requirements corpus). It
 * does not exist yet, and faking its reasoning here would hide exactly the gaps
 * this project is meant to surface. So: no requirement checking, no
 * prerequisite rules, no offering-term rules, no unit-load rules — in this file
 * or anywhere else in this app.
 *
 * The *shape* below is not invented. It follows
 * `docs/reference/03-degree-planner-architecture.md`, which splits the work by
 * tier: university and college verdicts are **reused** from the report,
 * major and minor are **computed**. Every requirement therefore carries
 * `tier` and `source`, and the five `source: 'stars'` entries below are the
 * five requirement blocks in `fixtures/stars/mock_stars_report.json`, with
 * their OK / NO verdicts carried through unchanged.
 *
 * `test/stubs.test.ts` asserts that two materially different plans produce a
 * deeply equal result, so this stays a stub. `test/fixtures.test.ts` checks
 * every reference below resolves to a course that really sits in that term.
 */

// GAP(analysis): the reused blocks arrive as free-text labels with no stable
// id, so these ids are ours. If the engine reuses STARS verdicts it will hit
// the same problem — see the matching GAP in parseStarsReport.ts.
// GAP(analysis): docs/reference/03 says a quantitative gap ("twelve units
// needed") is closed arithmetically against the proposed plan, and a category
// gap ("one course from category C") cannot be verified without category-to-
// course lists and should "degrade gracefully — let the student nominate which
// planned course they believe satisfies it, and mark the result unverified".
// Nothing in this contract carries that nomination yet. The UI has nowhere to
// put it and has not built it.
// GAP(analysis): `IP` is not in the STARS legend. docs/reference/01 records it
// as `[inferred]` `[confirm]`: "appears to mean satisfied only if in-progress
// courses are counted". The UI renders it as in-progress on that reading.
// GAP(analysis): nothing says which tier a reused block belongs to. We tag the
// five here by hand from their labels.
// GAP(analysis): `isSample` must be set to false by the real implementation.
// The sample badge is driven entirely by this field, so when the engine lands
// the badge disappears with no change to any component.

const REQUIREMENTS: Requirement[] = [
  /* ── Reused from the report, verbatim verdicts ─────────────────────────── */
  {
    id: 'req-128-units',
    name: '128-Unit Minimum',
    tier: 'university',
    source: 'stars',
    status: 'unsatisfied',
    reason:
      'Your report has this as not met. Counting the courses in this plan you reach 120 units, so 8 more are needed before May 2027.',
    satisfiedBy: [],
    tally: { counted: 120, required: 128, unit: 'UNITS' },
  },
  {
    id: 'req-64-residency',
    name: '64-Unit Residency',
    tier: 'university',
    source: 'stars',
    status: 'satisfied',
    satisfiedBy: [],
  },
  {
    id: 'req-32-upper-division',
    name: '32-Unit Upper Division',
    tier: 'university',
    source: 'stars',
    status: 'in-progress',
    satisfiedBy: [
      { code: 'CSCI 270', termId: 'fall-2024' },
      { code: 'CSCI 350', termId: 'spring-2025' },
      { code: 'CSCI 356', termId: 'spring-2025' },
    ],
    tally: { counted: 4, required: 32, unit: 'UNITS' },
  },
  {
    id: 'req-cumulative-gpa',
    name: 'Cumulative GPA 2.0+',
    tier: 'university',
    source: 'stars',
    status: 'satisfied',
    satisfiedBy: [],
    tally: { counted: 3.42, required: 2, unit: 'GPA' },
  },
  {
    id: 'req-composition',
    name: 'Composition/Writing',
    tier: 'university',
    source: 'stars',
    status: 'unsatisfied',
    reason:
      'Your report has this as not met. WRIT 150 is complete and WRIT 340 is in progress, so it should close once that grade posts.',
    satisfiedBy: [
      { code: 'WRIT 150', termId: 'spring-2024' },
      { code: 'WRIT 340', termId: 'spring-2025' },
    ],
    tally: { counted: 4, required: 8, unit: 'UNITS' },
  },

  /* ── Computed from the catalogue requirements ──────────────────────────── */
  {
    id: 'req-cs-core',
    name: 'Computer science core',
    tier: 'major',
    source: 'computed',
    status: 'in-progress',
    satisfiedBy: [
      { code: 'CSCI 103', termId: 'fall-2022' },
      { code: 'CSCI 104', termId: 'spring-2023' },
      { code: 'CSCI 170', termId: 'fall-2023' },
      { code: 'CSCI 201', termId: 'spring-2024' },
      { code: 'CSCI 270', termId: 'fall-2024' },
      { code: 'CSCI 350', termId: 'spring-2025' },
      { code: 'CSCI 356', termId: 'spring-2025' },
      { code: 'CSCI 310', termId: 'fall-2025' },
      { code: 'CSCI 353', termId: 'fall-2025' },
      { code: 'CSCI 360', termId: 'spring-2026' },
      { code: 'CSCI 401', termId: 'spring-2026' },
    ],
    tally: { counted: 36, required: 46, unit: 'UNITS' },
  },
  {
    id: 'req-core-electives',
    name: 'Core electives',
    tier: 'major',
    source: 'computed',
    status: 'satisfied',
    satisfiedBy: [
      { code: 'CSCI 402', termId: 'fall-2026' },
      { code: 'CSCI 420', termId: 'fall-2026' },
      { code: 'CSCI 485', termId: 'spring-2027' },
      { code: 'CSCI 445L', termId: 'spring-2027' },
    ],
    tally: { counted: 16, required: 16, unit: 'UNITS' },
  },
  {
    id: 'req-mathematics',
    name: 'Mathematics',
    tier: 'major',
    source: 'computed',
    status: 'satisfied',
    satisfiedBy: [
      { code: 'MATH 125', termId: 'spring-2023' },
      { code: 'MATH 126', termId: 'fall-2023' },
      { code: 'MATH 225', termId: 'fall-2024' },
      { code: 'MATH 226', termId: 'fall-2025' },
    ],
    tally: { counted: 16, required: 16, unit: 'UNITS' },
  },
];

const WARNINGS: PlanWarning[] = [
  {
    id: 'warn-capstone-term',
    severity: 'blocking',
    message:
      'CSCI 401 has only ever run in fall terms, and this plan places it in Spring 2026. The capstone will not be available that term.',
    course: { code: 'CSCI 401', termId: 'spring-2026' },
    termId: 'spring-2026',
  },
  {
    id: 'warn-generic-transfer',
    severity: 'warning',
    message:
      'TR-PSYC is generic transfer credit. It counts toward the 128-unit minimum but cannot fill a named requirement, so treat those 4 units as free electives.',
    course: { code: 'TR-PSYC', termId: 'fall-2022' },
  },
  {
    id: 'warn-seminar-late',
    severity: 'warning',
    message:
      'GESM 120 is a first-year seminar. Taking it in your fourth year is allowed, but seats go to first-year students first.',
    course: { code: 'GESM 120', termId: 'spring-2026' },
    termId: 'spring-2026',
  },
  {
    id: 'warn-no-double-count',
    // docs/reference/03 lists no-double-counting among the things that must be
    // computed whatever tier a requirement sits in, because adding a course can
    // break it. Stating the result of that check is part of the contract.
    severity: 'info',
    message:
      'ESRM 150 is transfer credit matched to a named USC course, so it fills one requirement and is not counted twice. Nothing else in this plan is claimed against two requirements.',
    course: { code: 'ESRM 150', termId: 'fall-2022' },
  },
];

const FIXED_RESULT: AnalysisResult = {
  verdict: 'not-yet',
  headline:
    'This plan does not reach the degree yet: two requirements are unmet and the capstone is scheduled in a term it is not offered.',
  units: { counted: 120, required: 128, unit: 'UNITS' },
  reusedFromReportDated: SAMPLE_REPORT_PREPARED,
  requirements: REQUIREMENTS,
  warnings: WARNINGS,
  isSample: true,
};

/**
 * @param _input The student's situation and their whole timeline.
 *               Deliberately unused: see above.
 */
export function analyzePlan(_input: AnalysisInput): Promise<AnalysisResult> {
  void _input;
  return Promise.resolve(structuredClone(FIXED_RESULT));
}
