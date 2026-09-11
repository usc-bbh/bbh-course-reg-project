import type { AnalysisInput, AnalysisResult, PlanWarning, Requirement } from '../domain/types';
import { buildTimeline } from '../domain/terms';
import { TERM, samplePlan, sampleSituation } from './sampleStudent';

/**
 * STUB. Ignores the situation and the plan it is given and returns the same
 * result every time.
 *
 * This is the thing that will eventually decide whether a plan reaches a
 * degree. It does not exist yet, and faking its reasoning here would hide
 * exactly the gaps this project is meant to surface. So: no requirement
 * checking, no prerequisite rules, no offering-term rules, no unit-load rules —
 * in this file or anywhere else in this app.
 *
 * `test/stubs.test.ts` asserts that two materially different plans produce a
 * deeply equal result, so this stays a stub.
 *
 * Every reference below resolves to a course that really sits in that term in
 * `sampleStudent.ts`. `test/fixtures.test.ts` checks that by hand-verification
 * so the UI never looks broken because the fixture disagreed with itself.
 */

// GAP(analysis): every warning needs a course code and a term id, not just a
// message, or the timeline cannot highlight what the warning is about.
// GAP(analysis): every unsatisfied requirement needs a student-readable
// `reason`. "Unsatisfied" on its own gives a student nothing to act on.
// GAP(analysis): requirements need a stable `category` from a fixed vocabulary
// so the panel can group them. We are inventing 'University' / 'Pre-major' /
// 'Major' / 'Minor' here; the real layer should own that list.
// GAP(analysis): `satisfiedBy` must reference courses by code AND term, because
// the same course code can legitimately appear in two terms of a draft plan.
// GAP(analysis): `isSample` must be set to false by the real implementation.
// The sample badge is driven entirely by this field, so when the real analysis
// layer lands the badge disappears with no change to any component.
// GAP(analysis): the UI renders `unitsCounted` of `unitsRequired` as the one
// progress figure a student sees. We do not know whether transfer units are
// inside that count, and we are not allowed to work it out here — the real
// layer has to say.
// GAP(analysis): is the echoed `terms` array authoritative? The UI ignores it
// and draws the timeline from its own store. We need to know whether the real
// layer may reorder or annotate the plan it is given — and if it may not, we
// would rather drop the field than keep two sources of truth for one plan.

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

/**
 * @param _input The student's situation and their whole timeline.
 *               Deliberately unused: see above.
 */
export function analyzePlan(_input: AnalysisInput): Promise<AnalysisResult> {
  void _input;
  return Promise.resolve(structuredClone(FIXED_RESULT));
}

/** Reads the year out of a term id for use in fixed copy. Not date logic. */
function yearOf(termId: string): string {
  return termId.split('-')[1] ?? '';
}
