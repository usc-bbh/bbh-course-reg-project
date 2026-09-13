import type {
  Plan,
  PlanCourse,
  PlanTerm,
  Season,
  StudentSituation,
  TakenCourse,
  TermId,
} from './types';

/**
 * Term arithmetic for display only.
 *
 * Everything here counts, groups, sorts or formats what it was given. Nothing
 * here decides whether a requirement is met, whether a term is overloaded, or
 * whether a term is in the past — a term's `status` comes from the data, never
 * from comparing to today's date.
 */

export const SEASONS: Season[] = ['fall', 'spring', 'summer'];

const SEASON_LABEL: Record<Season, string> = {
  fall: 'Fall',
  spring: 'Spring',
  summer: 'Summer',
};

/** Order within one academic year: Fall, then Spring, then Summer. */
const SEASON_ORDER: Record<Season, number> = { fall: 0, spring: 1, summer: 2 };

export function makeTermId(season: Season, year: number): TermId {
  return `${season}-${year}`;
}

export function parseTermId(id: TermId): { season: Season; year: number } | null {
  const [season, rawYear] = id.split('-');
  const year = Number(rawYear);
  if (!season || !SEASONS.includes(season as Season) || !Number.isFinite(year)) return null;
  return { season: season as Season, year };
}

export function termLabel(term: Pick<PlanTerm, 'season' | 'year'>): string {
  return `${SEASON_LABEL[term.season]} ${term.year}`;
}

export function seasonLabel(season: Season): string {
  return SEASON_LABEL[season];
}

/**
 * The calendar year an academic year starts in. Fall 2026, Spring 2027 and
 * Summer 2027 all belong to the 2026-2027 academic year.
 */
export function academicYearStart(term: Pick<PlanTerm, 'season' | 'year'>): number {
  return term.season === 'fall' ? term.year : term.year - 1;
}

export function academicYearLabel(startYear: number): string {
  return `${startYear}–${startYear + 1}`;
}

export function compareTerms(
  a: Pick<PlanTerm, 'season' | 'year'>,
  b: Pick<PlanTerm, 'season' | 'year'>,
): number {
  const yearDiff = academicYearStart(a) - academicYearStart(b);
  if (yearDiff !== 0) return yearDiff;
  return SEASON_ORDER[a.season] - SEASON_ORDER[b.season];
}

/** Sums a term's units and shows the total. No judgement about the number. */
export function termUnits(term: PlanTerm): number {
  return round1(term.courses.reduce((total, course) => total + course.units, 0));
}

export function totalUnits(terms: PlanTerm[]): number {
  return round1(terms.reduce((total, term) => total + termUnits(term), 0));
}

/** Keeps 16.5 from rendering as 16.499999999999996. */
export function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

export function formatUnits(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/** Deterministic id so the same course in the same term is the same row. */
function takenCourseId(course: TakenCourse): string {
  return `${course.termId}:${course.code}`;
}

function toPlanCourse(course: TakenCourse): PlanCourse {
  const planCourse: PlanCourse = {
    id: takenCourseId(course),
    code: course.code,
    title: course.title,
    units: course.units,
    source: course.source,
  };
  if (course.grade) planCourse.grade = course.grade;
  return planCourse;
}

/**
 * The whole timeline: the student's history (locked) followed by the terms
 * they are planning (editable), in chronological order.
 *
 * History is derived from the situation rather than stored alongside the plan,
 * so a correction in the review form shows up in the timeline immediately.
 */
export function buildTimeline(situation: StudentSituation, plan: Plan): PlanTerm[] {
  const historical = new Map<TermId, PlanTerm>();

  const place = (course: TakenCourse, status: 'completed' | 'in-progress') => {
    const parsed = parseTermId(course.termId);
    // GAP(stars): a completed course whose term we can't read has nowhere to go
    // on the timeline. We drop it from the timeline rather than invent a term;
    // it still shows in the review form so the student can correct it.
    if (!parsed) return;

    let term = historical.get(course.termId);
    if (!term) {
      term = {
        id: course.termId,
        season: parsed.season,
        year: parsed.year,
        status,
        courses: [],
      };
      historical.set(course.termId, term);
    }
    if (status === 'in-progress') term.status = 'in-progress';
    if (!term.courses.some((existing) => existing.code === course.code)) {
      term.courses.push(toPlanCourse(course));
    }
  };

  situation.completedCourses.forEach((course) => place(course, 'completed'));
  situation.inProgressCourses.forEach((course) => place(course, 'in-progress'));

  // A student can record coursework in a term they were also planning — say
  // they finish Spring 2027 and type it into the review form. History wins the
  // status, because the term is behind them now, but nothing is thrown away:
  // whatever they had planned there is folded into the same term. Removing the
  // completed course in the review form puts the planned term back.
  const planned: PlanTerm[] = [];
  for (const term of plan.terms) {
    const past = historical.get(term.id);
    if (!past) {
      planned.push(term);
      continue;
    }
    for (const course of term.courses) {
      if (!past.courses.some((existing) => existing.code === course.code)) {
        past.courses.push(course);
      }
    }
  }

  return [...historical.values(), ...planned].sort(compareTerms);
}

export interface AcademicYear {
  startYear: number;
  label: string;
  terms: PlanTerm[];
}

/** One column per academic year, Fall above Spring above Summer. */
export function groupByAcademicYear(terms: PlanTerm[]): AcademicYear[] {
  const byYear = new Map<number, PlanTerm[]>();
  for (const term of terms) {
    const start = academicYearStart(term);
    const bucket = byYear.get(start);
    if (bucket) bucket.push(term);
    else byYear.set(start, [term]);
  }
  return [...byYear.entries()]
    .sort(([a], [b]) => a - b)
    .map(([startYear, yearTerms]) => ({
      startYear,
      label: academicYearLabel(startYear),
      terms: [...yearTerms].sort(compareTerms),
    }));
}

export function isLocked(term: PlanTerm): boolean {
  return term.status !== 'planned';
}

/**
 * Every term a course appears in. Used to note "already in Fall 2027" beside a
 * picker option — a statement of fact with no judgement attached to it.
 */
export function findCourseTerms(terms: PlanTerm[], code: string): PlanTerm[] {
  return terms.filter((term) => term.courses.some((course) => course.code === code));
}

/** The four academic years a student starting in `entryTerm` would expect. */
export function defaultAcademicYears(entryYear: number, count = 4): number[] {
  return Array.from({ length: count }, (_, index) => entryYear + index);
}
