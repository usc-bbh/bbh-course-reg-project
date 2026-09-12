import { createContext, useContext } from 'react';
import type {
  Plan,
  PlanCourse,
  PlanTerm,
  Season,
  Selection,
  StudentSituation,
  TermId,
} from '../domain/types';
import { academicYearStart, compareTerms, makeTermId } from '../domain/terms';

/**
 * One store for the situation and the plan, plus the single selection value the
 * cross-highlighting reads. Context and a reducer — no new state library.
 */

export interface RemovedCourse {
  termId: TermId;
  index: number;
  course: PlanCourse;
}

export interface PlannerState {
  /** False until the saved copy has been read, after mount. */
  hydrated: boolean;
  situation: StudentSituation | null;
  plan: Plan;
  selection: Selection;
  /** A one-off message: saved data discarded, plan imported, and so on. */
  notice: string | null;
  /** The last removal, kept only long enough for Undo. */
  undoable: RemovedCourse | null;
}

export const initialState: PlannerState = {
  hydrated: false,
  situation: null,
  plan: { schemaVersion: 1, terms: [] },
  selection: null,
  notice: null,
  undoable: null,
};

export type PlannerAction =
  | { type: 'hydrated'; situation: StudentSituation | null; plan: Plan; notice: string | null }
  | { type: 'start'; situation: StudentSituation; plan: Plan }
  | { type: 'situation-changed'; situation: StudentSituation }
  | { type: 'add-course'; termId: TermId; course: PlanCourse }
  | { type: 'move-course'; courseId: string; toTermId: TermId }
  | { type: 'remove-course'; termId: TermId; courseId: string }
  | { type: 'undo-remove' }
  | { type: 'dismiss-undo' }
  | { type: 'add-term'; season: Season; year: number }
  | { type: 'remove-term'; termId: TermId }
  | { type: 'add-year' }
  | { type: 'select'; selection: Selection }
  | { type: 'imported'; situation: StudentSituation; plan: Plan }
  | { type: 'reset-plan' }
  | { type: 'clear-all' }
  | { type: 'dismiss-notice' };

export function newCourseId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `c-${crypto.randomUUID()}`;
  }
  fallbackSeq += 1;
  return `c-${fallbackSeq}`;
}
let fallbackSeq = 0;

function sortTerms(terms: PlanTerm[]): PlanTerm[] {
  return [...terms].sort(compareTerms);
}

function mapTerms(plan: Plan, fn: (term: PlanTerm) => PlanTerm): Plan {
  return { ...plan, terms: plan.terms.map(fn) };
}

/**
 * The academic years a plan covers: four from the entry term, plus any year the
 * student has already added terms to.
 */
export function plannedYearRange(situation: StudentSituation, plan: Plan): number[] {
  const entryStart = academicYearStart({
    season: situation.entryTerm.season,
    year: situation.entryTerm.year,
  });
  const years = new Set<number>();
  for (let index = 0; index < 4; index += 1) years.add(entryStart + index);
  for (const course of [...situation.completedCourses, ...situation.inProgressCourses]) {
    const [, rawYear] = course.termId.split('-');
    const season = course.termId.split('-')[0] as Season;
    const year = Number(rawYear);
    if (Number.isFinite(year)) years.add(academicYearStart({ season, year }));
  }
  for (const term of plan.terms) years.add(academicYearStart(term));
  return [...years].sort((a, b) => a - b);
}

/** Empty fall and spring terms for the years the student has not lived yet. */
export function defaultPlannedTerms(situation: StudentSituation): PlanTerm[] {
  const taken = new Set(
    [...situation.completedCourses, ...situation.inProgressCourses].map((course) => course.termId),
  );
  const entryStart = academicYearStart({
    season: situation.entryTerm.season,
    year: situation.entryTerm.year,
  });
  const terms: PlanTerm[] = [];
  for (let offset = 0; offset < 4; offset += 1) {
    const startYear = entryStart + offset;
    const candidates: Array<{ season: Season; year: number }> = [
      { season: 'fall', year: startYear },
      { season: 'spring', year: startYear + 1 },
    ];
    for (const candidate of candidates) {
      // Nothing before the student arrived. A spring entrant does not get an
      // empty Fall term for the year they were not here.
      if (compareTerms(candidate, situation.entryTerm) < 0) continue;
      const id = makeTermId(candidate.season, candidate.year);
      if (taken.has(id)) continue;
      terms.push({ id, season: candidate.season, year: candidate.year, status: 'planned', courses: [] });
    }
  }
  return sortTerms(terms);
}

export function plannerReducer(state: PlannerState, action: PlannerAction): PlannerState {
  switch (action.type) {
    case 'hydrated':
      return {
        ...state,
        hydrated: true,
        situation: action.situation,
        plan: action.plan,
        notice: action.notice,
      };

    case 'start':
      return {
        ...state,
        situation: action.situation,
        plan: { ...action.plan, terms: sortTerms(action.plan.terms) },
        selection: null,
        undoable: null,
        notice: null,
      };

    case 'situation-changed':
      return { ...state, situation: action.situation };

    case 'add-course': {
      return {
        ...state,
        plan: mapTerms(state.plan, (term) =>
          term.id === action.termId && term.status === 'planned'
            ? { ...term, courses: [...term.courses, action.course] }
            : term,
        ),
        undoable: null,
      };
    }

    case 'move-course': {
      const source = state.plan.terms.find((term) =>
        term.courses.some((course) => course.id === action.courseId),
      );
      const course = source?.courses.find((item) => item.id === action.courseId);
      if (!source || !course) return state;
      if (source.id === action.toTermId) return state;
      const target = state.plan.terms.find((term) => term.id === action.toTermId);
      if (!target || target.status !== 'planned' || source.status !== 'planned') return state;

      return {
        ...state,
        plan: mapTerms(state.plan, (term) => {
          if (term.id === source.id) {
            return { ...term, courses: term.courses.filter((item) => item.id !== course.id) };
          }
          if (term.id === action.toTermId) {
            return { ...term, courses: [...term.courses, course] };
          }
          return term;
        }),
        undoable: null,
      };
    }

    case 'remove-course': {
      const term = state.plan.terms.find((item) => item.id === action.termId);
      const index = term?.courses.findIndex((item) => item.id === action.courseId) ?? -1;
      const course = index >= 0 ? term?.courses[index] : undefined;
      if (!term || !course) return state;
      return {
        ...state,
        plan: mapTerms(state.plan, (item) =>
          item.id === action.termId
            ? { ...item, courses: item.courses.filter((entry) => entry.id !== action.courseId) }
            : item,
        ),
        undoable: { termId: action.termId, index, course },
      };
    }

    case 'undo-remove': {
      const undoable = state.undoable;
      if (!undoable) return state;
      return {
        ...state,
        plan: mapTerms(state.plan, (term) => {
          if (term.id !== undoable.termId) return term;
          const courses = [...term.courses];
          courses.splice(Math.min(undoable.index, courses.length), 0, undoable.course);
          return { ...term, courses };
        }),
        undoable: null,
      };
    }

    case 'dismiss-undo':
      return state.undoable ? { ...state, undoable: null } : state;

    case 'add-term': {
      const id = makeTermId(action.season, action.year);
      if (state.plan.terms.some((term) => term.id === id)) return state;
      return {
        ...state,
        plan: {
          ...state.plan,
          terms: sortTerms([
            ...state.plan.terms,
            { id, season: action.season, year: action.year, status: 'planned', courses: [] },
          ]),
        },
      };
    }

    case 'remove-term': {
      const term = state.plan.terms.find((item) => item.id === action.termId);
      if (!term || term.status !== 'planned' || term.courses.length > 0) return state;
      return {
        ...state,
        plan: { ...state.plan, terms: state.plan.terms.filter((item) => item.id !== action.termId) },
      };
    }

    case 'add-year': {
      if (!state.situation) return state;
      const years = plannedYearRange(state.situation, state.plan);
      const nextStart = (years[years.length - 1] ?? state.situation.entryTerm.year) + 1;
      const additions: PlanTerm[] = (['fall', 'spring'] as Season[]).map((season) => {
        const year = season === 'fall' ? nextStart : nextStart + 1;
        return { id: makeTermId(season, year), season, year, status: 'planned' as const, courses: [] };
      });
      const existing = new Set(state.plan.terms.map((term) => term.id));
      return {
        ...state,
        plan: {
          ...state.plan,
          terms: sortTerms([
            ...state.plan.terms,
            ...additions.filter((term) => !existing.has(term.id)),
          ]),
        },
      };
    }

    case 'select':
      return { ...state, selection: action.selection };

    case 'imported':
      return {
        ...state,
        situation: action.situation,
        plan: { ...action.plan, terms: sortTerms(action.plan.terms) },
        selection: null,
        undoable: null,
        notice: 'Plan imported.',
      };

    case 'reset-plan':
      return {
        ...state,
        plan: mapTerms(state.plan, (term) => ({ ...term, courses: [] })),
        selection: null,
        undoable: null,
        notice: 'Plan cleared. Your situation is unchanged.',
      };

    case 'clear-all':
      return { ...initialState, hydrated: true };

    case 'dismiss-notice':
      return state.notice ? { ...state, notice: null } : state;

    default:
      return state;
  }
}

export interface PlannerContextValue {
  state: PlannerState;
  dispatch: React.Dispatch<PlannerAction>;
  /** 'saved' | 'saving' | 'error' | 'idle' — drives the quiet autosave line. */
  saveState: 'idle' | 'saving' | 'saved' | 'error';
}

export const PlannerContext = createContext<PlannerContextValue | null>(null);

export function usePlanner(): PlannerContextValue {
  const value = useContext(PlannerContext);
  if (!value) throw new Error('usePlanner must be used inside <PlannerProvider>.');
  return value;
}
