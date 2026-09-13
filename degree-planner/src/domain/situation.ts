import type {
  EntryTerm,
  ParsedStarsReport,
  StarsCourseRow,
  StarsSummarySlice,
  StudentSituation,
  TakenCourse,
} from './types';
import { normalizeCourseCode, parseUscTermCode, termIdFromUscCode } from './uscTerms';
import { compareTerms } from './terms';

/**
 * The seam between the STARS parser's object and what the planner holds.
 *
 * Everything here is renaming, normalising and sorting. Nothing decides whether
 * a requirement is met — the report's own verdicts are carried through
 * untouched in `starsRequirements` for the analysis layer to reuse, per
 * docs/reference/03-degree-planner-architecture.md.
 */

function toTakenCourse(row: StarsCourseRow): TakenCourse | null {
  const termId = termIdFromUscCode(row.term);
  // GAP(stars): a row whose term code we cannot read has nowhere to go on a
  // timeline. We drop it from the timeline rather than invent a term; it still
  // shows in the review form so the student can correct it.
  if (!termId) return null;
  const course: TakenCourse = {
    code: normalizeCourseCode(row.code),
    title: row.title,
    units: row.units,
    termId,
    source: row.source ?? 'usc',
  };
  if (row.grade) course.grade = row.grade;
  return course;
}

/**
 * The term the student arrived.
 *
 * Prefers the report's own value. Falling back to the earliest course term is
 * sorting, not inference about the calendar — and it is the same answer for
 * every student who has not transferred in mid-degree.
 */
export function deriveEntryTerm(report: ParsedStarsReport): EntryTerm {
  const stated = report.entryTerm ? parseUscTermCode(report.entryTerm) : null;
  if (stated) return stated;

  const terms = [...report.completedCourses, ...report.inProgressCourses]
    .map((row) => parseUscTermCode(row.term))
    .filter((term): term is EntryTerm => term !== null)
    .sort(compareTerms);

  return terms[0] ?? { season: 'fall', year: new Date().getFullYear() };
}

export function situationFromReport(
  report: ParsedStarsReport,
  studentName = '',
): StudentSituation {
  return {
    studentName,
    degree: report.degree,
    major: report.major,
    concentration: report.concentration,
    minor: report.minor,
    catalogYear: report.catalogYear,
    classLevel: report.classLevel,
    entryTerm: deriveEntryTerm(report),
    transferUnits: report.transferUnits,
    completedCourses: report.completedCourses
      .map(toTakenCourse)
      .filter((course): course is TakenCourse => course !== null),
    inProgressCourses: report.inProgressCourses
      .map(toTakenCourse)
      .filter((course): course is TakenCourse => course !== null),
    starsRequirements: report.requirements,
    reportBasis: { major: report.major, catalogYear: report.catalogYear },
    source: 'stars',
  };
}

/**
 * The five fields `validator/README.md` documents as the `stars_summary` slice
 * Tanzil's next-semester validator reads, and it states it assumes no others
 * are present.
 *
 * It takes the **report**, not the planner's situation, and that is the whole
 * point of the signature. The slice needs a GPA for GPA-threshold
 * prerequisites; the planner keeps no GPA, because nothing on screen uses one.
 * Building the slice from a situation would mean inventing that number, so this
 * reads it from the one object that actually has it.
 *
 * The planner does not call the validator — that is a different tool and out of
 * scope here. This exists so the same student can be handed to it without a
 * translation step, and so the two modules stay honest about the seam.
 */
export function toStarsSummary(report: ParsedStarsReport): StarsSummarySlice {
  const codes = (rows: StarsCourseRow[]) => rows.map((row) => normalizeCourseCode(row.code));
  return {
    major: report.major,
    classLevel: report.classLevel,
    gpa: report.gpa,
    completedCourses: report.completedCourses.map((row) => {
      const entry: { code: string; grade?: string } = { code: normalizeCourseCode(row.code) };
      if (row.grade) entry.grade = row.grade;
      return entry;
    }),
    inProgressCourses: codes(report.inProgressCourses).map((code) => ({ code })),
  };
}

/** Units a student has actually banked, transfer credit included. */
export function earnedUnits(situation: StudentSituation): number {
  return situation.completedCourses.reduce((total, course) => total + course.units, 0);
}
