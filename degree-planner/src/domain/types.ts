/**
 * The contract.
 *
 * Every shape the UI consumes lives here. Components import from this file and
 * never from a stub's internals, so swapping in the real STARS parser or the
 * real analysis layer is an import change in `src/data/` and nothing else.
 */

export type Season = 'fall' | 'spring' | 'summer';
export type TermStatus = 'completed' | 'in-progress' | 'planned';
export type SituationSource = 'stars' | 'manual' | 'sample';
export type ClassStanding = 'freshman' | 'sophomore' | 'junior' | 'senior';

/** Term ids are deterministic and readable: `fall-2026`. */
export type TermId = string;

export interface CourseRef {
  code: string;
  termId: TermId | null;
}

export interface TakenCourse {
  code: string;
  title: string;
  units: number;
  termId: TermId;
  /** Omitted for in-progress coursework. */
  grade?: string;
}

export interface EntryTerm {
  season: Season;
  year: number;
}

export interface StudentSituation {
  studentName: string;
  major: string;
  minors: string[];
  /** '2024-2025' */
  catalogueYear: string;
  classStanding: ClassStanding;
  entryTerm: EntryTerm;
  transferUnits: number;
  completedCourses: TakenCourse[];
  inProgressCourses: TakenCourse[];
  source: SituationSource;
}

export interface PlanCourse {
  id: string;
  code: string;
  title: string;
  units: number;
  /** Present only on completed coursework, carried through for display. */
  grade?: string;
}

export interface PlanTerm {
  id: TermId;
  season: Season;
  year: number;
  status: TermStatus;
  courses: PlanCourse[];
}

/**
 * The terms the student is *planning*.
 *
 * Completed and in-progress terms are not stored here — they are derived from
 * `StudentSituation.completedCourses` / `inProgressCourses` by
 * `buildTimeline()`. One fact, one home: correcting a completed course in the
 * review form updates the locked part of the timeline immediately, and
 * "Reset plan" can empty this object without touching the student's history.
 */
export interface Plan {
  schemaVersion: 1;
  terms: PlanTerm[];
}

export type Verdict = 'on-track' | 'not-yet' | 'unknown';
export type RequirementStatus = 'satisfied' | 'in-progress' | 'unsatisfied';
export type WarningSeverity = 'info' | 'warning' | 'blocking';

export interface Requirement {
  id: string;
  name: string;
  category: string;
  status: RequirementStatus;
  /** Required whenever status is 'unsatisfied'. */
  reason?: string;
  /** Drives cross-highlighting in the timeline. */
  satisfiedBy: CourseRef[];
  unitsCounted?: number;
  unitsRequired?: number;
}

export interface PlanWarning {
  id: string;
  severity: WarningSeverity;
  message: string;
  /** Drives cross-highlighting in the timeline. */
  course?: CourseRef;
  termId?: TermId;
}

export interface AnalysisResult {
  verdict: Verdict;
  /** One plain-language sentence, student-facing. */
  headline: string;
  unitsCounted: number;
  unitsRequired: number;
  /**
   * The plan echoed back. The UI does NOT render this — the timeline is drawn
   * from the store, because two sources of truth for one plan is how a UI
   * starts lying. See the GAP in src/data/analyzePlan.ts.
   */
  terms: PlanTerm[];
  requirements: Requirement[];
  warnings: PlanWarning[];
  /** True while results come from the stub; drives the sample badge. */
  isSample: boolean;
}

/** What the analysis layer is handed. The stub ignores all of it. */
export interface AnalysisInput {
  situation: StudentSituation;
  /** The whole timeline: locked history first, then planned terms. */
  terms: PlanTerm[];
}

/** What the STARS parser hands back. The stub ignores the file. */
export interface ParsedStarsReport {
  situation: StudentSituation;
}

/* ── Catalogue ─────────────────────────────────────────────────────────── */

export interface CatalogueCourse {
  code: string;
  title: string;
  units: number;
}

export interface Catalogue {
  /** Human-readable label for where this data came from. */
  sourceLabel: string;
  courses: CatalogueCourse[];
  majors: string[];
  minors: string[];
  catalogueYears: string[];
}

/* ── Cross-highlighting ────────────────────────────────────────────────── */

/**
 * What the student currently has selected in the audit panel. A single value,
 * so selecting something new clears the last one and Escape clears everything.
 */
export type Selection =
  | { kind: 'requirement'; id: string }
  | { kind: 'warning'; id: string }
  | null;

/* ── Export file ───────────────────────────────────────────────────────── */

export interface PlanExportFile {
  schemaVersion: 1;
  kind: 'plansc.degree-planner.export';
  exportedOn: string;
  situation: StudentSituation;
  plan: Plan;
}
