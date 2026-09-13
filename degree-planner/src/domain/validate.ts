import type {
  CreditSource,
  ReportBasis,
  ParsedStarsReport,
  Plan,
  PlanCourse,
  PlanExportFile,
  PlanTerm,
  Season,
  SituationSource,
  StarsBlockStatus,
  StarsRequirementBlock,
  StudentSituation,
  TakenCourse,
  TermStatus,
} from './types';

/**
 * Hand-written guards for anything that arrives from outside the running app:
 * a file the student chose to import, or whatever is sitting in localStorage
 * from a previous visit.
 *
 * Each guard returns the reason it rejected something, so the UI can name the
 * actual problem instead of saying "invalid file".
 */

export type Checked<T> = { ok: true; value: T } | { ok: false; problem: string };

const SEASONS: Season[] = ['fall', 'spring', 'summer'];
const TERM_STATUSES: TermStatus[] = ['completed', 'in-progress', 'planned'];
const CLASS_LEVELS: ParsedStarsReport['classLevel'][] = [
  'Freshman',
  'Sophomore',
  'Junior',
  'Senior',
];
const SOURCES: SituationSource[] = ['stars', 'manual', 'sample'];
const CREDIT_SOURCES: CreditSource[] = ['usc', 'transfer_specific', 'transfer_generic'];
const BLOCK_STATUSES: StarsBlockStatus[] = ['ok', 'no', 'ip'];

/** Bumped when a stored shape changes in a way older data cannot satisfy. */
export const SCHEMA_VERSION = 2;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function str(value: unknown): value is string {
  return typeof value === 'string';
}

function num(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function checkTakenCourse(value: unknown): TakenCourse | null {
  if (!isRecord(value)) return null;
  if (!str(value.code) || !str(value.title) || !num(value.units) || !str(value.termId)) return null;
  const course: TakenCourse = {
    code: value.code,
    title: value.title,
    units: value.units,
    termId: value.termId,
    source:
      str(value.source) && CREDIT_SOURCES.includes(value.source as CreditSource)
        ? (value.source as CreditSource)
        : 'usc',
  };
  if (str(value.grade) && value.grade.length > 0) course.grade = value.grade;
  return course;
}

function checkPlanCourse(value: unknown): PlanCourse | null {
  if (!isRecord(value)) return null;
  if (!str(value.id) || !str(value.code) || !str(value.title) || !num(value.units)) return null;
  const course: PlanCourse = {
    id: value.id,
    code: value.code,
    title: value.title,
    units: value.units,
  };
  if (str(value.grade) && value.grade.length > 0) course.grade = value.grade;
  if (str(value.source) && CREDIT_SOURCES.includes(value.source as CreditSource)) {
    course.source = value.source as CreditSource;
  }
  return course;
}

function checkPlanTerm(value: unknown): PlanTerm | null {
  if (!isRecord(value)) return null;
  if (!str(value.id) || !num(value.year)) return null;
  if (!str(value.season) || !SEASONS.includes(value.season as Season)) return null;
  if (!str(value.status) || !TERM_STATUSES.includes(value.status as TermStatus)) return null;
  if (!Array.isArray(value.courses)) return null;
  const courses: PlanCourse[] = [];
  for (const raw of value.courses) {
    const course = checkPlanCourse(raw);
    if (!course) return null;
    courses.push(course);
  }
  return {
    id: value.id,
    season: value.season as Season,
    year: value.year,
    status: value.status as TermStatus,
    courses,
  };
}

function checkStarsRequirements(value: unknown): StarsRequirementBlock[] {
  if (!Array.isArray(value)) return [];
  const blocks: StarsRequirementBlock[] = [];
  for (const raw of value) {
    if (!isRecord(raw) || !str(raw.label)) continue;
    if (!str(raw.status) || !BLOCK_STATUSES.includes(raw.status as StarsBlockStatus)) continue;
    blocks.push({ label: raw.label, status: raw.status as StarsBlockStatus });
  }
  return blocks;
}

function checkReportBasis(value: unknown): ReportBasis | null {
  if (!isRecord(value)) return null;
  if (!str(value.major) || !str(value.catalogYear)) return null;
  return { major: value.major, catalogYear: value.catalogYear };
}

export function checkSituation(value: unknown): Checked<StudentSituation> {
  if (!isRecord(value)) return { ok: false, problem: 'the situation is missing' };
  if (!str(value.studentName) || !str(value.major) || !str(value.catalogYear)) {
    return { ok: false, problem: 'the situation is missing a name, major or catalogue year' };
  }
  if (!str(value.classLevel) || !CLASS_LEVELS.includes(value.classLevel as 'Junior')) {
    return { ok: false, problem: 'the class level is not one USC uses' };
  }
  if (
    !isRecord(value.entryTerm) ||
    !str(value.entryTerm.season) ||
    !SEASONS.includes(value.entryTerm.season as Season) ||
    !num(value.entryTerm.year)
  ) {
    return { ok: false, problem: 'the entry term is missing or unreadable' };
  }
  if (!num(value.transferUnits)) return { ok: false, problem: 'the transfer units are missing' };
  if (!Array.isArray(value.completedCourses) || !Array.isArray(value.inProgressCourses)) {
    return { ok: false, problem: 'the coursework lists are missing' };
  }

  const completedCourses: TakenCourse[] = [];
  for (const raw of value.completedCourses) {
    const course = checkTakenCourse(raw);
    if (!course) return { ok: false, problem: 'one of the completed courses is unreadable' };
    completedCourses.push(course);
  }
  const inProgressCourses: TakenCourse[] = [];
  for (const raw of value.inProgressCourses) {
    const course = checkTakenCourse(raw);
    if (!course) return { ok: false, problem: 'one of the in-progress courses is unreadable' };
    inProgressCourses.push(course);
  }

  const source: SituationSource =
    str(value.source) && SOURCES.includes(value.source as SituationSource)
      ? (value.source as SituationSource)
      : 'manual';

  return {
    ok: true,
    value: {
      studentName: value.studentName,
      degree: str(value.degree) ? value.degree : '',
      major: value.major,
      concentration: str(value.concentration) ? value.concentration : null,
      minor: str(value.minor) && value.minor.length > 0 ? value.minor : null,
      catalogYear: value.catalogYear,
      classLevel: value.classLevel as ParsedStarsReport['classLevel'],
      entryTerm: {
        season: value.entryTerm.season as Season,
        year: value.entryTerm.year,
      },
      transferUnits: value.transferUnits,
      completedCourses,
      inProgressCourses,
      starsRequirements: checkStarsRequirements(value.starsRequirements),
      reportBasis: checkReportBasis(value.reportBasis),
      source,
    },
  };
}

export function checkPlan(value: unknown): Checked<Plan> {
  if (!isRecord(value)) return { ok: false, problem: 'the plan is missing' };
  if (value.schemaVersion !== SCHEMA_VERSION) {
    return { ok: false, problem: 'the plan was written by a different version of this planner' };
  }
  if (!Array.isArray(value.terms)) return { ok: false, problem: 'the plan has no terms' };
  const terms: PlanTerm[] = [];
  for (const raw of value.terms) {
    const term = checkPlanTerm(raw);
    if (!term) return { ok: false, problem: 'one of the terms in the plan is unreadable' };
    terms.push(term);
  }
  return { ok: true, value: { schemaVersion: SCHEMA_VERSION, terms } };
}

/** Validates a file the student picked with "Import plan". */
export function checkExportFile(value: unknown): Checked<PlanExportFile> {
  if (!isRecord(value)) {
    return { ok: false, problem: 'this file is not a plan file' };
  }
  if (value.kind !== 'plansc.degree-planner.export') {
    return { ok: false, problem: 'this file was not exported by the degree planner' };
  }
  if (value.schemaVersion !== SCHEMA_VERSION) {
    return { ok: false, problem: 'this file was written by a different version of the planner' };
  }
  const situation = checkSituation(value.situation);
  if (!situation.ok) return situation;
  const plan = checkPlan(value.plan);
  if (!plan.ok) return plan;
  return {
    ok: true,
    value: {
      schemaVersion: SCHEMA_VERSION,
      kind: 'plansc.degree-planner.export',
      exportedOn: str(value.exportedOn) ? value.exportedOn : '',
      situation: situation.value,
      plan: plan.value,
    },
  };
}
