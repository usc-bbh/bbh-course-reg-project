import type { StudentSituation } from '../../domain/types';
import { PLAN_BASE_YEAR, SAMPLE_CATALOGUE_YEAR } from '../../data/sampleStudent';

/**
 * What "Enter it myself" starts from.
 *
 * The entry term defaults to PLAN_BASE_YEAR rather than to the current year on
 * purpose: nothing in this app reads today's date to decide what a plan looks
 * like, so the same build shows the same thing in January as in September. The
 * field is the first one in the form and the student changes it in one step.
 */
// GAP(other): nothing tells us what a manual-entry student should see first, so
// the entry term is seeded from PLAN_BASE_YEAR and the catalogue year from the
// sample. Both are editable, and both are guesses.
export function blankSituation(): StudentSituation {
  return {
    studentName: '',
    major: '',
    minors: [],
    catalogueYear: SAMPLE_CATALOGUE_YEAR,
    classStanding: 'freshman',
    entryTerm: { season: 'fall', year: PLAN_BASE_YEAR },
    transferUnits: 0,
    completedCourses: [],
    inProgressCourses: [],
    source: 'manual',
  };
}
