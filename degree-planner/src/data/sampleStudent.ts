import type { Plan, StudentSituation, TakenCourse } from '../domain/types';
import { makeTermId } from '../domain/terms';

/**
 * The sample student.
 *
 * One fictional person, described once. The fake STARS report
 * (`parseStarsReport.ts`) and the fixed analysis result (`analyzePlan.ts`)
 * describe this same person, with the same course codes in the same terms, so
 * every reference in the audit resolves to a course you can actually see in the
 * timeline.
 *
 * Every year is derived from PLAN_BASE_YEAR. Bump that one constant and the
 * whole demo moves forward together instead of ageing into nonsense.
 */
export const PLAN_BASE_YEAR = 2024;

const Y1 = PLAN_BASE_YEAR;
const Y2 = PLAN_BASE_YEAR + 1;
const Y3 = PLAN_BASE_YEAR + 2;
const Y4 = PLAN_BASE_YEAR + 3;

export const TERM = {
  fall1: makeTermId('fall', Y1),
  spring1: makeTermId('spring', Y1 + 1),
  fall2: makeTermId('fall', Y2),
  spring2: makeTermId('spring', Y2 + 1),
  fall3: makeTermId('fall', Y3),
  spring3: makeTermId('spring', Y3 + 1),
  fall4: makeTermId('fall', Y4),
  spring4: makeTermId('spring', Y4 + 1),
} as const;

export const SAMPLE_CATALOGUE_YEAR = `${PLAN_BASE_YEAR}-${PLAN_BASE_YEAR + 1}`;

const completedCourses: TakenCourse[] = [
  // First year
  { code: 'CSCI 102L', title: 'Fundamentals of Computation', units: 2, termId: TERM.fall1, grade: 'A' },
  { code: 'CSCI 103L', title: 'Introduction to Programming', units: 4, termId: TERM.fall1, grade: 'A-' },
  { code: 'MATH 125g', title: 'Calculus I', units: 4, termId: TERM.fall1, grade: 'B+' },
  { code: 'WRIT 150', title: 'Writing and Critical Reasoning', units: 4, termId: TERM.fall1, grade: 'A' },
  { code: 'ENGR 102', title: 'Viterbi First-Year Academy', units: 2, termId: TERM.fall1, grade: 'P' },
  { code: 'CSCI 104L', title: 'Data Structures and Object-Oriented Design', units: 4, termId: TERM.spring1, grade: 'B+' },
  { code: 'CSCI 170', title: 'Discrete Methods in Computer Science', units: 4, termId: TERM.spring1, grade: 'B' },
  { code: 'MATH 126g', title: 'Calculus II', units: 4, termId: TERM.spring1, grade: 'B-' },
  { code: 'PHYS 151Lg', title: 'Fundamentals of Physics I: Mechanics', units: 4, termId: TERM.spring1, grade: 'B' },
  // Second year
  { code: 'CSCI 201', title: 'Principles of Software Development', units: 4, termId: TERM.fall2, grade: 'A-' },
  { code: 'MATH 226g', title: 'Calculus III', units: 4, termId: TERM.fall2, grade: 'B' },
  { code: 'EE 109L', title: 'Introduction to Embedded Systems', units: 4, termId: TERM.fall2, grade: 'B+' },
  { code: 'BISC 120Lg', title: 'General Biology: Organismal Biology and Evolution', units: 4, termId: TERM.fall2, grade: 'A-' },
  { code: 'CSCI 270', title: 'Introduction to Algorithms', units: 4, termId: TERM.spring2, grade: 'B+' },
  { code: 'MATH 225', title: 'Linear Algebra and Linear Differential Equations', units: 4, termId: TERM.spring2, grade: 'B' },
  { code: 'EE 364', title: 'Probability and Statistics for Engineers', units: 4, termId: TERM.spring2, grade: 'B+' },
  { code: 'CSCI 310', title: 'Software Engineering', units: 4, termId: TERM.spring2, grade: 'A-' },
];

// GAP(stars): in-progress coursework has no grade yet. We rely on the parser
// reporting it separately from completed work rather than on an empty grade
// field, because "no grade" and "grade not parsed" are different facts.
const inProgressCourses: TakenCourse[] = [
  { code: 'CSCI 350', title: 'Introduction to Operating Systems', units: 4, termId: TERM.fall3 },
  { code: 'CSCI 356', title: 'Introduction to Computer Systems', units: 4, termId: TERM.fall3 },
  { code: 'WRIT 340', title: 'Advanced Writing', units: 4, termId: TERM.fall3 },
];

export const sampleSituation: StudentSituation = {
  studentName: 'Robin Samplewood',
  major: 'Computer Science (BS)',
  minors: ['Mathematics'],
  catalogueYear: SAMPLE_CATALOGUE_YEAR,
  classStanding: 'junior',
  entryTerm: { season: 'fall', year: PLAN_BASE_YEAR },
  transferUnits: 8,
  completedCourses,
  inProgressCourses,
  source: 'sample',
};

/**
 * The terms the sample student is planning. History is not repeated here — it
 * is derived from the situation above by `buildTimeline()`.
 */
export const samplePlan: Plan = {
  schemaVersion: 1,
  terms: [
    {
      id: TERM.spring3,
      season: 'spring',
      year: Y3 + 1,
      status: 'planned',
      courses: [
        { id: 'p-csci353', code: 'CSCI 353', title: 'Introduction to Internetworking', units: 4 },
        { id: 'p-csci360', code: 'CSCI 360', title: 'Introduction to Artificial Intelligence', units: 4 },
        { id: 'p-gesm120', code: 'GESM 120g', title: 'Seminar in Humanistic Inquiry', units: 4 },
      ],
    },
    {
      id: TERM.fall4,
      season: 'fall',
      year: Y4,
      status: 'planned',
      courses: [
        { id: 'p-csci402', code: 'CSCI 402', title: 'Operating Systems', units: 4 },
        { id: 'p-math407', code: 'MATH 407', title: 'Probability Theory', units: 4 },
        { id: 'p-amst101', code: 'AMST 101g', title: 'Race and Class in Los Angeles', units: 4 },
      ],
    },
    {
      id: TERM.spring4,
      season: 'spring',
      year: Y4 + 1,
      status: 'planned',
      courses: [
        { id: 'p-csci401', code: 'CSCI 401', title: 'Capstone: Design and Construction of Large Software Systems', units: 4 },
        { id: 'p-csci420', code: 'CSCI 420', title: 'Computer Graphics', units: 4 },
        { id: 'p-math458', code: 'MATH 458', title: 'Numerical Methods', units: 4 },
      ],
    },
  ],
};

/** An empty plan for a student who has not laid anything out yet. */
export function emptyPlan(): Plan {
  return { schemaVersion: 1, terms: [] };
}
