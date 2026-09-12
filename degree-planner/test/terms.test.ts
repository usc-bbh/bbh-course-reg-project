import { describe, expect, it } from 'vitest';
import type { Plan, StudentSituation, TakenCourse } from '../src/domain/types';
import { buildTimeline, groupByAcademicYear, termUnits } from '../src/domain/terms';
import { defaultPlannedTerms } from '../src/state/plannerStore';
import { samplePlan, sampleSituation } from '../src/data/sampleStudent';

function situationWith(overrides: Partial<StudentSituation>): StudentSituation {
  return { ...sampleSituation, ...overrides };
}

const completed = (code: string, termId: string): TakenCourse => ({
  code,
  title: `${code} title`,
  units: 4,
  termId,
  grade: 'A',
});

describe('buildTimeline', () => {
  it('puts history before the planned terms, in order', () => {
    const timeline = buildTimeline(sampleSituation, samplePlan);
    const ids = timeline.map((term) => term.id);
    expect(ids).toEqual([...ids].sort((a, b) => ids.indexOf(a) - ids.indexOf(b)));
    expect(timeline[0]?.status).toBe('completed');
    expect(timeline[timeline.length - 1]?.status).toBe('planned');
  });

  it('keeps planned coursework when the same term gains history', () => {
    // The student finishes Spring 2027 and records it, while that term still
    // holds the courses they had planned. Nothing may be dropped.
    const situation = situationWith({
      completedCourses: [...sampleSituation.completedCourses, completed('CSCI 353', 'spring-2027')],
    });
    const timeline = buildTimeline(situation, samplePlan);

    const spring = timeline.find((term) => term.id === 'spring-2027');
    expect(spring).toBeDefined();
    expect(spring?.status).toBe('completed');

    const codes = spring?.courses.map((course) => course.code) ?? [];
    // The completed course and everything that was planned in that term.
    expect(codes).toContain('CSCI 353');
    expect(codes).toContain('CSCI 360');
    expect(codes).toContain('GESM 120g');
    // And it appears once, not twice.
    expect(codes.filter((code) => code === 'CSCI 353')).toHaveLength(1);

    // The term is not duplicated anywhere in the timeline.
    expect(timeline.filter((term) => term.id === 'spring-2027')).toHaveLength(1);
  });

  it('drops a course whose term id cannot be read, without crashing', () => {
    const situation = situationWith({
      completedCourses: [completed('CSCI 103L', 'not-a-term')],
      inProgressCourses: [],
    });
    const timeline = buildTimeline(situation, { schemaVersion: 1, terms: [] });
    expect(timeline).toEqual([]);
  });

  it('sums a term without floating-point noise', () => {
    const term = {
      id: 'fall-2026',
      season: 'fall' as const,
      year: 2026,
      status: 'planned' as const,
      courses: [
        { id: 'a', code: 'A 1', title: 'A', units: 1.1 },
        { id: 'b', code: 'B 1', title: 'B', units: 2.2 },
      ],
    };
    expect(termUnits(term)).toBe(3.3);
  });

  it('groups summer with the spring before it', () => {
    const plan: Plan = {
      schemaVersion: 1,
      terms: [
        { id: 'fall-2026', season: 'fall', year: 2026, status: 'planned', courses: [] },
        { id: 'spring-2027', season: 'spring', year: 2027, status: 'planned', courses: [] },
        { id: 'summer-2027', season: 'summer', year: 2027, status: 'planned', courses: [] },
      ],
    };
    const situation = situationWith({ completedCourses: [], inProgressCourses: [] });
    const years = groupByAcademicYear(buildTimeline(situation, plan));
    expect(years).toHaveLength(1);
    expect(years[0]?.terms.map((term) => term.id)).toEqual([
      'fall-2026',
      'spring-2027',
      'summer-2027',
    ]);
  });
});

describe('defaultPlannedTerms', () => {
  it('never offers a term from before the student arrived', () => {
    const situation = situationWith({
      entryTerm: { season: 'spring', year: 2026 },
      completedCourses: [],
      inProgressCourses: [],
    });
    const terms = defaultPlannedTerms(situation);
    expect(terms.map((term) => term.id)).not.toContain('fall-2025');
    expect(terms[0]?.id).toBe('spring-2026');
  });

  it('gives a fall entrant four years of fall and spring', () => {
    const situation = situationWith({
      entryTerm: { season: 'fall', year: 2026 },
      completedCourses: [],
      inProgressCourses: [],
    });
    const terms = defaultPlannedTerms(situation);
    expect(terms).toHaveLength(8);
    expect(terms[0]?.id).toBe('fall-2026');
    expect(terms[7]?.id).toBe('spring-2030');
  });

  it('skips terms the student already has coursework in', () => {
    const situation = situationWith({
      entryTerm: { season: 'fall', year: 2026 },
      completedCourses: [completed('CSCI 103L', 'fall-2026')],
      inProgressCourses: [],
    });
    const terms = defaultPlannedTerms(situation);
    expect(terms.map((term) => term.id)).not.toContain('fall-2026');
  });
});
