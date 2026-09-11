import { describe, expect, it } from 'vitest';
import { analyzePlan } from '../src/data/analyzePlan';
import { parseStarsReport } from '../src/data/parseStarsReport';
import type { AnalysisInput, Plan, StudentSituation } from '../src/domain/types';
import { buildTimeline } from '../src/domain/terms';
import { emptyPlan, samplePlan, sampleSituation } from '../src/data/sampleStudent';

/**
 * Non-negotiable 3, made machine-checkable.
 *
 * Both adapters ignore their arguments. If anyone ever "just adds a little
 * logic for the demo", these fail.
 */
describe('the stubs stay dumb', () => {
  it('analyzePlan returns the same result for two materially different plans', async () => {
    const denseSituation: StudentSituation = sampleSituation;
    const emptySituation: StudentSituation = {
      ...sampleSituation,
      studentName: 'Someone Else',
      major: 'Economics (BA)',
      minors: [],
      catalogueYear: '2026-2027',
      classStanding: 'freshman',
      entryTerm: { season: 'spring', year: 2030 },
      transferUnits: 64,
      completedCourses: [],
      inProgressCourses: [],
    };

    const busyPlan: Plan = samplePlan;
    const bare: Plan = emptyPlan();

    const first: AnalysisInput = {
      situation: denseSituation,
      terms: buildTimeline(denseSituation, busyPlan),
    };
    const second: AnalysisInput = {
      situation: emptySituation,
      terms: buildTimeline(emptySituation, bare),
    };

    expect(first).not.toEqual(second);
    expect(await analyzePlan(first)).toEqual(await analyzePlan(second));
  });

  it('parseStarsReport returns the same result for two different files', async () => {
    const pdf = new File(['%PDF-1.7 one student'], 'report-a.pdf', { type: 'application/pdf' });
    const text = new File(['a completely different report'], 'report-b.txt', {
      type: 'text/plain',
    });

    expect(await parseStarsReport(pdf)).toEqual(await parseStarsReport(text));
  });

  it('hands back a fresh object each time, so a caller cannot corrupt the fixture', async () => {
    const input: AnalysisInput = {
      situation: sampleSituation,
      terms: buildTimeline(sampleSituation, samplePlan),
    };
    const first = await analyzePlan(input);
    const firstRequirement = first.requirements[0];
    expect(firstRequirement).toBeDefined();
    if (firstRequirement) firstRequirement.name = 'mutated';
    const second = await analyzePlan(input);
    expect(second.requirements[0]?.name).not.toBe('mutated');
  });
});
