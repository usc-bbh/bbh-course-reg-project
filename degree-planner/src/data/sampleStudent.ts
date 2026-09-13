import type { ParsedStarsReport, Plan, StarsCourseRow } from '../domain/types';

/**
 * The sample student.
 *
 * This is `fixtures/stars/mock_stars_report.json` — the repo's canonical shared
 * fixture, described there as "the parser's expected OUTPUT and the validator's
 * stars_summary INPUT". Same student, same terms, same grades, same requirement
 * blocks, so the planner, the parser tests and the next-semester validator all
 * talk about one person.
 *
 * Two things are added on top of the committed file, both of which
 * `docs/parser-brief.md` §6–7 asks the parser to start emitting:
 *   - `source` on every course row, and
 *   - two transfer rows, one specific and one generic, because the brief calls
 *     that distinction out as mattering "a lot for the degree planner".
 *
 * Everything else is copied, not invented. PLAN_BASE_YEAR is the fixture's own
 * entry year; bump it and the whole demo moves forward together.
 */
export const PLAN_BASE_YEAR = 2022;

/** USC term codes, straight from the fixture. 1 = spring, 2 = summer, 3 = fall. */
export const TERM_CODE = {
  fall1: '20223',
  spring1: '20231',
  fall2: '20233',
  spring2: '20241',
  fall3: '20243',
  spring3: '20251',
  fall4: '20253',
  spring4: '20261',
  fall5: '20263',
  spring5: '20271',
} as const;

const completedCourses: StarsCourseRow[] = [
  // Transfer credit, both kinds (docs/parser-brief.md §7). Both count toward
  // the 128-unit total; only the specific one can fill a named requirement.
  { term: TERM_CODE.fall1, code: 'ESRM 150', title: 'Introduction to Statistics', units: 4, grade: 'TR', source: 'transfer_specific' },
  { term: TERM_CODE.fall1, code: 'TR-PSYC', title: 'Transfer credit, psychology', units: 4, grade: 'TR', source: 'transfer_generic' },
  // USC coursework, exactly as the fixture records it.
  { term: TERM_CODE.fall1, code: 'CSCI 103', title: 'Introduction to Programming', units: 4, grade: 'A-', source: 'usc' },
  { term: TERM_CODE.spring1, code: 'CSCI 104', title: 'Data Structures and Object-Oriented Design', units: 4, grade: 'B+', source: 'usc' },
  { term: TERM_CODE.spring1, code: 'MATH 125', title: 'Calculus I', units: 4, grade: 'A', source: 'usc' },
  { term: TERM_CODE.fall2, code: 'CSCI 170', title: 'Discrete Methods in Computer Science', units: 4, grade: 'B', source: 'usc' },
  { term: TERM_CODE.fall2, code: 'MATH 126', title: 'Calculus II', units: 4, grade: 'B-', source: 'usc' },
  { term: TERM_CODE.spring2, code: 'CSCI 201', title: 'Principles of Software Development', units: 4, grade: 'A-', source: 'usc' },
  { term: TERM_CODE.spring2, code: 'WRIT 150', title: 'Writing and Critical Reasoning', units: 4, grade: 'A', source: 'usc' },
  { term: TERM_CODE.fall3, code: 'CSCI 270', title: 'Introduction to Algorithms', units: 4, grade: 'B+', source: 'usc' },
  { term: TERM_CODE.fall3, code: 'MATH 225', title: 'Linear Algebra and Linear Differential Equations', units: 4, grade: 'B', source: 'usc' },
];

const inProgressCourses: StarsCourseRow[] = [
  { term: TERM_CODE.spring3, code: 'CSCI 350', title: 'Introduction to Systems Programming', units: 4, source: 'usc' },
  { term: TERM_CODE.spring3, code: 'CSCI 356', title: 'Introduction to Computer Systems Engineering', units: 4, source: 'usc' },
  { term: TERM_CODE.spring3, code: 'WRIT 340', title: 'Advanced Writing', units: 4, source: 'usc' },
];

/**
 * The parsed report, field for field as stars-parser/README.md documents it.
 * `entryTerm` is the one addition — see the GAP in parseStarsReport.ts.
 */
export const sampleStarsReport: ParsedStarsReport = {
  degree: 'BS',
  major: 'Computer Science',
  concentration: null,
  majorCode: 'CSCI',
  programCode: '1832',
  catalogYear: '2023-2024',
  classLevel: 'Junior',
  expectedGraduation: '16 May 2027',
  gpa: 3.42,
  upperDivisionGpa: 3.55,
  completedCourses,
  inProgressCourses,
  transferUnits: 8,
  minor: null,
  isTransfer: true,
  studiedAbroad: false,
  isStudentAthlete: false,
  requirements: [
    { label: '128-Unit Minimum', status: 'no' },
    { label: '64-Unit Residency', status: 'ok' },
    { label: '32-Unit Upper Division', status: 'no' },
    { label: 'Cumulative GPA 2.0+', status: 'ok' },
    { label: 'Composition/Writing', status: 'no' },
  ],
  entryTerm: TERM_CODE.fall1,
};

/** The date on the report the reused verdicts above came from. */
export const SAMPLE_REPORT_PREPARED = '2025-02-14';

// GAP(stars): the parser's output carries no student name — `fixtures/stars/`
// holds redacted reports, and `mock_stars_report.json` has no name field. The
// planner puts a name on the *sample* student so the demo reads like a person;
// a real uploaded report leaves the field blank for the student to fill in.
export const SAMPLE_STUDENT_NAME = 'Robin Samplewood';

/**
 * The terms the sample student is planning, running to the expected graduation
 * on the report. History is not repeated here — it is derived from the
 * situation by `buildTimeline()`.
 */
export const samplePlan: Plan = {
  schemaVersion: 2,
  terms: [
    {
      id: 'fall-2025',
      season: 'fall',
      year: 2025,
      status: 'planned',
      courses: [
        { id: 'p-csci310', code: 'CSCI 310', title: 'Software Engineering', units: 4 },
        { id: 'p-csci353', code: 'CSCI 353', title: 'Introduction to Internetworking', units: 4 },
        { id: 'p-ee364', code: 'EE 364', title: 'Probability and Statistics for Engineers', units: 4 },
        { id: 'p-math226', code: 'MATH 226', title: 'Calculus III', units: 4 },
      ],
    },
    {
      id: 'spring-2026',
      season: 'spring',
      year: 2026,
      status: 'planned',
      courses: [
        { id: 'p-csci360', code: 'CSCI 360', title: 'Introduction to Artificial Intelligence', units: 4 },
        { id: 'p-csci401', code: 'CSCI 401', title: 'Capstone: Design and Construction of Large Software Systems', units: 4 },
        { id: 'p-gesm120', code: 'GESM 120', title: 'Seminar in Humanistic Inquiry', units: 4 },
        { id: 'p-ee109', code: 'EE 109L', title: 'Introduction to Embedded Systems', units: 4 },
      ],
    },
    {
      id: 'fall-2026',
      season: 'fall',
      year: 2026,
      status: 'planned',
      courses: [
        { id: 'p-csci402', code: 'CSCI 402', title: 'Operating Systems', units: 4 },
        { id: 'p-csci420', code: 'CSCI 420', title: 'Computer Graphics', units: 4 },
        { id: 'p-amst101', code: 'AMST 101', title: 'Race and Class in Los Angeles', units: 4 },
        { id: 'p-bisc120', code: 'BISC 120L', title: 'General Biology: Organismal Biology and Evolution', units: 4 },
      ],
    },
    {
      id: 'spring-2027',
      season: 'spring',
      year: 2027,
      status: 'planned',
      courses: [
        { id: 'p-csci485', code: 'CSCI 485', title: 'File and Database Management', units: 4 },
        { id: 'p-csci445', code: 'CSCI 445L', title: 'Introduction to Robotics', units: 4 },
        { id: 'p-phil140', code: 'PHIL 140', title: 'Contemporary Moral and Social Issues', units: 4 },
        { id: 'p-phys151', code: 'PHYS 151L', title: 'Fundamentals of Physics I: Mechanics', units: 4 },
      ],
    },
  ],
};

/** An empty plan for a student who has not laid anything out yet. */
export function emptyPlan(): Plan {
  return { schemaVersion: 2, terms: [] };
}
