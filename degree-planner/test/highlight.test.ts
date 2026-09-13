import { describe, expect, it } from 'vitest';
import { buildHighlight, courseKey, highlightCount } from '../src/features/audit/highlight';
import type { AnalysisResult } from '../src/domain/types';

function resultWith(warnings: AnalysisResult['warnings']): AnalysisResult {
  return {
    verdict: 'not-yet',
    headline: 'headline',
    units: { counted: 0, required: 128, unit: 'UNITS' },
    reusedFromReportDated: null,
    requirements: [
      {
        id: 'req-a',
        name: 'A requirement',
        tier: 'major',
        source: 'computed',
        status: 'unsatisfied',
        satisfiedBy: [{ code: 'CSCI 310', termId: 'fall-2025' }],
      },
    ],
    warnings,
    isSample: true,
  };
}

describe('what the timeline lights up', () => {
  it('marks courses a warning or a blocker names', () => {
    const highlight = buildHighlight(
      resultWith([
        { id: 'w1', severity: 'blocking', message: 'x', course: { code: 'CSCI 401', termId: 'spring-2026' } },
        { id: 'w2', severity: 'warning', message: 'y', course: { code: 'GESM 120', termId: 'spring-2026' } },
      ]),
      null,
    );
    expect(highlight.warnedCourses.get(courseKey('spring-2026', 'CSCI 401'))).toBe('blocking');
    expect(highlight.warnedCourses.get(courseKey('spring-2026', 'GESM 120'))).toBe('warning');
  });

  it('does not put a warning marker on a course an info note merely mentions', () => {
    const highlight = buildHighlight(
      resultWith([
        { id: 'w3', severity: 'info', message: 'z', course: { code: 'ESRM 150', termId: 'fall-2022' }, termId: 'fall-2022' },
      ]),
      null,
    );
    expect(highlight.warnedCourses.size).toBe(0);
    expect(highlight.warnedTerms.size).toBe(0);
  });

  it('still highlights an info note when the student selects it', () => {
    const highlight = buildHighlight(
      resultWith([
        { id: 'w3', severity: 'info', message: 'z', course: { code: 'ESRM 150', termId: 'fall-2022' } },
      ]),
      { kind: 'warning', id: 'w3' },
    );
    expect(highlight.courseKeys.has(courseKey('fall-2022', 'ESRM 150'))).toBe(true);
    expect(highlightCount(highlight)).toBeGreaterThan(0);
  });

  it('keeps the stronger of two warnings on the same course', () => {
    const highlight = buildHighlight(
      resultWith([
        { id: 'w1', severity: 'warning', message: 'x', course: { code: 'CSCI 401', termId: 'spring-2026' } },
        { id: 'w2', severity: 'blocking', message: 'y', course: { code: 'CSCI 401', termId: 'spring-2026' } },
      ]),
      null,
    );
    expect(highlight.warnedCourses.get(courseKey('spring-2026', 'CSCI 401'))).toBe('blocking');
  });
});
