import type { StudentSituation } from '../../domain/types';

/**
 * Has the student edited themselves out from under the verdicts we reused?
 *
 * `docs/reference/03-degree-planner-architecture.md` lists the conditions that
 * invalidate reusing STARS' university and college verdicts. Two of them are a
 * text edit away in the review form:
 *
 *   - **Scope.** Reuse is "valid only while what-ifs stay within one school…
 *     Cross-school changes are currently out of scope and should warn and route
 *     the student to an advisor." Nothing here knows which school a major
 *     belongs to, so this reports the major *change*, not its school.
 *   - **Catalog year.** "A student changing catalog year changes the upper-tier
 *     rules, so the reused verdict would be for the wrong year."
 *
 * This compares two strings and reports the difference. It does not decide
 * whether any requirement is met, and it must not start to.
 */
export interface ReportDrift {
  field: 'major' | 'catalogYear';
  label: string;
  onReport: string;
  now: string;
  consequence: string;
}

export function reportDrift(situation: StudentSituation): ReportDrift[] {
  const basis = situation.reportBasis;
  if (!basis) return [];

  const drift: ReportDrift[] = [];

  if (situation.major.trim() && situation.major !== basis.major) {
    drift.push({
      field: 'major',
      label: 'Major',
      onReport: basis.major,
      now: situation.major,
      consequence:
        'The university and school requirements below were read from a report for your old major. They still apply if the new major is in the same school; if it is not, an advisor has to confirm them.',
    });
  }

  if (situation.catalogYear.trim() && situation.catalogYear !== basis.catalogYear) {
    drift.push({
      field: 'catalogYear',
      label: 'Catalogue year',
      onReport: basis.catalogYear,
      now: situation.catalogYear,
      consequence:
        'Requirements are set by catalogue year, so the verdicts read from your report are for a different set of rules than the one you are now planning under.',
    });
  }

  return drift;
}
