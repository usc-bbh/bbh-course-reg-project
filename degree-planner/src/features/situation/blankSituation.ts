import type { StudentSituation } from '../../domain/types';
import { PLAN_BASE_YEAR } from '../../data/sampleStudent';

/**
 * What "Enter it myself" starts from.
 *
 * The entry term defaults to PLAN_BASE_YEAR rather than to the current year on
 * purpose: nothing in this app reads today's date to decide what a plan looks
 * like, so the same build shows the same thing in January as in September. It
 * is the first field in the form and the student changes it in one step.
 */
// GAP(other): nothing tells us what a manual-entry student should see first, so
// the entry term and catalogue year are seeded from the sample. Both are
// editable, and both are guesses.
export function blankSituation(): StudentSituation {
  return {
    studentName: '',
    degree: 'BS',
    major: '',
    concentration: null,
    minor: null,
    catalogYear: '2024-2025',
    classLevel: 'Freshman',
    entryTerm: { season: 'fall', year: PLAN_BASE_YEAR },
    transferUnits: 0,
    completedCourses: [],
    inProgressCourses: [],
    starsRequirements: [],
    // Nothing was read, so nothing can go stale.
    reportBasis: null,
    source: 'manual',
  };
}
