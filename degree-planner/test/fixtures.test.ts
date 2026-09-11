import { describe, expect, it } from 'vitest';
import { analyzePlan } from '../src/data/analyzePlan';
import { parseStarsReport } from '../src/data/parseStarsReport';
import { samplePlan, sampleSituation } from '../src/data/sampleStudent';
import { buildTimeline } from '../src/domain/terms';
import type { CourseRef, PlanTerm } from '../src/domain/types';

/**
 * Fixture coherence.
 *
 * The fake STARS student, the sample plan and the fixed analysis result have to
 * describe the same person, or a perfectly good UI looks broken. This does by
 * machine what the brief asks to be done by hand before every commit.
 */
function resolves(terms: PlanTerm[], ref: CourseRef): boolean {
  if (!ref.termId) return false;
  const term = terms.find((entry) => entry.id === ref.termId);
  return Boolean(term?.courses.some((course) => course.code === ref.code));
}

describe('the fixtures tell one coherent story', () => {
  const timeline = buildTimeline(sampleSituation, samplePlan);

  it('every requirement reference resolves to a course in that term', async () => {
    const result = await analyzePlan({ situation: sampleSituation, terms: timeline });
    const dangling = result.requirements.flatMap((requirement) =>
      requirement.satisfiedBy
        .filter((ref) => !resolves(timeline, ref))
        .map((ref) => `${requirement.id}: ${ref.code} @ ${ref.termId}`),
    );
    expect(dangling).toEqual([]);
  });

  it('every warning reference resolves to a course or a term in the plan', async () => {
    const result = await analyzePlan({ situation: sampleSituation, terms: timeline });
    const termIds = new Set(timeline.map((term) => term.id));
    const dangling = result.warnings.flatMap((warning) => {
      const problems: string[] = [];
      if (warning.course && !resolves(timeline, warning.course)) {
        problems.push(`${warning.id}: ${warning.course.code} @ ${warning.course.termId}`);
      }
      if (warning.termId && !termIds.has(warning.termId)) {
        problems.push(`${warning.id}: term ${warning.termId}`);
      }
      return problems;
    });
    expect(dangling).toEqual([]);
  });

  it('reaches every state the UI designs for', async () => {
    const result = await analyzePlan({ situation: sampleSituation, terms: timeline });
    const statuses = result.requirements.map((requirement) => requirement.status);
    expect(statuses).toContain('unsatisfied');
    expect(statuses).toContain('in-progress');
    expect(statuses).toContain('satisfied');

    const unsatisfied = result.requirements.filter((r) => r.status === 'unsatisfied');
    expect(unsatisfied.length).toBeGreaterThan(0);
    for (const requirement of unsatisfied) {
      expect(requirement.reason, `${requirement.id} needs a reason`).toBeTruthy();
    }

    const severities = result.warnings.map((warning) => warning.severity);
    expect(severities).toContain('warning');
    expect(severities).toContain('blocking');

    const blocking = result.warnings.find((warning) => warning.severity === 'blocking');
    expect(blocking?.course?.code).toBeTruthy();
    expect(blocking?.termId).toBeTruthy();

    expect(result.isSample).toBe(true);
  });

  it('the fake STARS report describes the same student as the sample', async () => {
    const parsed = await parseStarsReport(new File(['x'], 'r.pdf'));
    expect(parsed.situation.studentName).toBe(sampleSituation.studentName);
    expect(parsed.situation.major).toBe(sampleSituation.major);
    expect(parsed.situation.catalogueYear).toBe(sampleSituation.catalogueYear);
    expect(parsed.situation.completedCourses).toEqual(sampleSituation.completedCourses);
    expect(parsed.situation.source).toBe('stars');
  });

  it('locks the past from the data, never from today’s date', () => {
    const locked = timeline.filter((term) => term.status !== 'planned');
    const planned = timeline.filter((term) => term.status === 'planned');
    expect(locked.length).toBeGreaterThan(0);
    expect(planned.length).toBeGreaterThan(0);
    // Four academic years, one column each.
    const years = new Set(timeline.map((term) => (term.season === 'fall' ? term.year : term.year - 1)));
    expect(years.size).toBe(4);
  });
});
