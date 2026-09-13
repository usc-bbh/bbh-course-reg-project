import { describe, expect, it } from 'vitest';
import { analyzePlan } from '../src/data/analyzePlan';
import { parseStarsReport } from '../src/data/parseStarsReport';
import { SAMPLE_REPORT_PREPARED, samplePlan, sampleStarsReport } from '../src/data/sampleStudent';
import { buildTimeline } from '../src/domain/terms';
import { situationFromReport } from '../src/domain/situation';
import type { CourseRef, PlanTerm } from '../src/domain/types';
import { sampleSituation } from './sample';

/**
 * Fixture coherence.
 *
 * The fake STARS report, the sample plan and the fixed analysis result have to
 * describe the same person, or a perfectly good UI looks broken. This does by
 * machine what the brief asks to be done by hand before every commit.
 */
function resolves(terms: PlanTerm[], ref: CourseRef): boolean {
  if (!ref.termId) return false;
  const term = terms.find((entry) => entry.id === ref.termId);
  return Boolean(term?.courses.some((course) => course.code === ref.code));
}

describe('the fixtures tell one coherent story', () => {
  const timeline = buildTimeline(sampleSituation(), samplePlan);

  it('every requirement reference resolves to a course in that term', async () => {
    const result = await analyzePlan({ situation: sampleSituation(), terms: timeline });
    const dangling = result.requirements.flatMap((requirement) =>
      requirement.satisfiedBy
        .filter((ref) => !resolves(timeline, ref))
        .map((ref) => `${requirement.id}: ${ref.code} @ ${ref.termId}`),
    );
    expect(dangling).toEqual([]);
  });

  it('every warning reference resolves to a course or a term in the plan', async () => {
    const result = await analyzePlan({ situation: sampleSituation(), terms: timeline });
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
    const result = await analyzePlan({ situation: sampleSituation(), terms: timeline });
    const statuses = result.requirements.map((requirement) => requirement.status);
    expect(statuses).toContain('unsatisfied');
    expect(statuses).toContain('in-progress');
    expect(statuses).toContain('satisfied');

    for (const requirement of result.requirements.filter((r) => r.status === 'unsatisfied')) {
      expect(requirement.reason, `${requirement.id} needs a reason`).toBeTruthy();
    }

    const severities = result.warnings.map((warning) => warning.severity);
    expect(severities).toContain('info');
    expect(severities).toContain('warning');
    expect(severities).toContain('blocking');

    const blocking = result.warnings.find((warning) => warning.severity === 'blocking');
    expect(blocking?.course?.code).toBeTruthy();
    expect(blocking?.termId).toBeTruthy();

    expect(result.isSample).toBe(true);
  });

  it('splits requirements by tier the way the architecture doc does', async () => {
    // docs/reference/03: university and college verdicts are reused from the
    // report, major and minor are computed.
    const result = await analyzePlan({ situation: sampleSituation(), terms: timeline });
    const reused = result.requirements.filter((entry) => entry.source === 'stars');
    const computed = result.requirements.filter((entry) => entry.source === 'computed');

    expect(reused.length).toBeGreaterThan(0);
    expect(computed.length).toBeGreaterThan(0);
    // Nothing reused may claim a tier the doc says we compute.
    expect(reused.every((entry) => entry.tier === 'university' || entry.tier === 'college')).toBe(true);
    expect(computed.every((entry) => entry.tier === 'major' || entry.tier === 'minor')).toBe(true);
    // And reusing a verdict means inheriting its date, which must be surfaced.
    expect(result.reusedFromReportDated).toBe(SAMPLE_REPORT_PREPARED);
  });

  it('carries every STARS block through to a requirement', async () => {
    const result = await analyzePlan({ situation: sampleSituation(), terms: timeline });
    const reusedNames = result.requirements
      .filter((entry) => entry.source === 'stars')
      .map((entry) => entry.name);
    for (const block of sampleStarsReport.requirements) {
      expect(reusedNames, `${block.label} was dropped`).toContain(block.label);
    }
  });

  it('the fake report and the situation describe the same student', async () => {
    const parsed = await parseStarsReport(new File(['x'], 'r.pdf'));
    expect(parsed).not.toBeNull();
    if (!parsed) return;
    const situation = situationFromReport(parsed);
    expect(situation.major).toBe(sampleStarsReport.major);
    expect(situation.catalogYear).toBe(sampleStarsReport.catalogYear);
    expect(situation.classLevel).toBe(sampleStarsReport.classLevel);
    expect(situation.completedCourses).toHaveLength(sampleStarsReport.completedCourses.length);
    expect(situation.source).toBe('stars');
  });

  it('locks the past from the data, never from today’s date', () => {
    const locked = timeline.filter((term) => term.status !== 'planned');
    const planned = timeline.filter((term) => term.status === 'planned');
    expect(locked.length).toBeGreaterThan(0);
    expect(planned.length).toBeGreaterThan(0);
  });

  it('plans through the expected graduation on the report', () => {
    // The report says 16 May 2027, so the last planned term is Spring 2027.
    expect(sampleStarsReport.expectedGraduation).toContain('2027');
    expect(timeline[timeline.length - 1]?.id).toBe('spring-2027');
  });
});
