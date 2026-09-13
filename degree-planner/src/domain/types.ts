/**
 * The contract.
 *
 * Every shape here is reconciled against what the other modules in this repo
 * already document, rather than invented:
 *
 *   stars-parser/README.md            the parser's output object, field for field
 *   fixtures/stars/mock_stars_report.json  the committed sample of that object
 *   validator/README.md               the `stars_summary` slice Tanzil's validator reads
 *   catalog/README.md                 Agastya's course object and offering_frequency
 *   docs/parser-brief.md §6, §7       per-course `term` and `source`, and why they matter here
 *   docs/reference/01-reading-a-stars-report.md  the OK / NO / IP status codes
 *   docs/reference/03-degree-planner-architecture.md  which tiers are reused vs computed
 *
 * CONTRIBUTING.md says to read the producer's own README rather than infer a
 * shape from its code. Where this file departs from one of those documents, it
 * says so and there is a matching GAP marker at the seam.
 */

export type Season = 'fall' | 'spring' | 'summer';
export type TermStatus = 'completed' | 'in-progress' | 'planned';
export type SituationSource = 'stars' | 'manual' | 'sample';

/** Term ids are deterministic and readable: `fall-2026`. See uscTerms.ts. */
export type TermId = string;

/* ── The STARS parser's output ─────────────────────────────────────────────
   Abhi and Agastya own this. Shape copied from stars-parser/README.md and
   checked against fixtures/stars/mock_stars_report.json. */

/** `docs/reference/01`: OK complete, NO incomplete, IP satisfied only if in-progress counts. */
export type StarsBlockStatus = 'ok' | 'no' | 'ip';

/**
 * Where a credit came from (`docs/parser-brief.md` §6, §7).
 *
 * This distinction is load-bearing for a planner and not for the validator:
 * both transfer kinds count toward the 128-unit total, but only
 * `transfer_specific` can satisfy a prerequisite or fill a named requirement.
 * Generic credit is free elective units.
 */
export type CreditSource = 'usc' | 'transfer_specific' | 'transfer_generic';

export interface StarsCourseRow {
  /** Raw five-digit USC term code, e.g. `"20243"`. Kept raw, per the brief. */
  term: string;
  code: string;
  title: string;
  units: number;
  /** Exactly as printed. `TR` for transfer credit; not always a letter. */
  grade?: string;
  source?: CreditSource;
}

export interface StarsRequirementBlock {
  label: string;
  status: StarsBlockStatus;
}

/** The object `parseStarsReport` resolves with. Mirrors stars-parser/README.md. */
export interface ParsedStarsReport {
  degree: string;
  major: string;
  concentration: string | null;
  majorCode: string;
  programCode: string;
  catalogYear: string;
  classLevel: 'Freshman' | 'Sophomore' | 'Junior' | 'Senior';
  expectedGraduation: string;
  gpa: number;
  upperDivisionGpa: number;
  completedCourses: StarsCourseRow[];
  inProgressCourses: StarsCourseRow[];
  transferUnits: number;
  minor: string | null;
  isTransfer: boolean;
  studiedAbroad: boolean;
  isStudentAthlete: boolean;
  requirements: StarsRequirementBlock[];
  /**
   * Not in the parser's output today. `docs/reference/01` §"What is in a
   * report" lists "term of USC entrance" in the pertinent-data section, so the
   * report has it. See the GAP in parseStarsReport.ts.
   */
  entryTerm?: string;
}

/* ── What the planner holds ───────────────────────────────────────────────── */

export interface TakenCourse {
  code: string;
  title: string;
  units: number;
  termId: TermId;
  /** Omitted for in-progress coursework. */
  grade?: string;
  source: CreditSource;
}

export interface EntryTerm {
  season: Season;
  year: number;
}

/**
 * What the reused STARS verdicts were read under.
 *
 * `docs/reference/03-degree-planner-architecture.md` closes with the conditions
 * that invalidate reusing a tier: a what-if that crosses schools, and a change
 * of catalog year — "the reused verdict would be for the wrong year". A student
 * can trigger both from the review form by editing two text fields. Keeping the
 * report's own values lets the UI say so. It is provenance, not a judgement:
 * comparing two strings is all the planner does with it.
 */
export interface ReportBasis {
  major: string;
  catalogYear: string;
}

export interface StudentSituation {
  studentName: string;
  degree: string;
  major: string;
  concentration: string | null;
  /** Singular and nullable, because that is what the parser emits. */
  minor: string | null;
  /** `'2024-2025'`. The parser calls this `catalogYear`. */
  catalogYear: string;
  classLevel: ParsedStarsReport['classLevel'];
  entryTerm: EntryTerm;
  /** The report's own total. Transfer rows also carry their own units. */
  transferUnits: number;
  completedCourses: TakenCourse[];
  inProgressCourses: TakenCourse[];
  /** STARS' own verdicts, carried forward untouched. See AnalysisResult. */
  starsRequirements: StarsRequirementBlock[];
  /** What those verdicts were read under. `null` when nothing was read. */
  reportBasis: ReportBasis | null;
  source: SituationSource;
}

export interface PlanCourse {
  id: string;
  code: string;
  title: string;
  units: number;
  /** Present only on completed coursework, carried through for display. */
  grade?: string;
  /** Present on history; planned courses have not been taken yet. */
  source?: CreditSource;
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
 * the situation by `buildTimeline()`. One fact, one home: correcting a
 * completed course in the review form updates the locked part of the timeline
 * immediately, and "Reset plan" can empty this object without touching the
 * student's history.
 */
export interface Plan {
  schemaVersion: 2;
  terms: PlanTerm[];
}

/* ── What the analysis layer returns ──────────────────────────────────────── */

export type Verdict = 'on-track' | 'not-yet' | 'unknown';
export type RequirementStatus = 'satisfied' | 'in-progress' | 'unsatisfied';
export type WarningSeverity = 'info' | 'warning' | 'blocking';

/**
 * `docs/reference/03-degree-planner-architecture.md` splits the work by tier:
 * university and college verdicts are **reused** from the report, major and
 * minor are **computed** from catalogue requirements. The UI shows which,
 * because a reused verdict inherits the report's prepared date and a student
 * deserves to know that.
 */
export type RequirementTier = 'university' | 'college' | 'major' | 'minor';
export type RequirementSource = 'stars' | 'computed';

/** `docs/reference/01`: the trailing label on a tally says what the number is. */
export type TallyUnit = 'UNITS' | 'COURSES' | 'SUB-GROUP(S)' | 'GPA';

export interface RequirementTally {
  counted: number;
  required: number;
  unit: TallyUnit;
}

export interface CourseRef {
  code: string;
  termId: TermId | null;
}

export interface Requirement {
  id: string;
  /** STARS block labels are free text, e.g. "128-Unit Minimum". */
  name: string;
  tier: RequirementTier;
  source: RequirementSource;
  status: RequirementStatus;
  /** Required whenever status is 'unsatisfied'. */
  reason?: string;
  /** Drives cross-highlighting in the timeline. */
  satisfiedBy: CourseRef[];
  tally?: RequirementTally;
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
  units: RequirementTally;
  /**
   * The prepared date of the report the reused verdicts came from.
   * `docs/reference/03` §"Conditions that invalidate this": reusing a tier
   * means inheriting the report's date, so carry it through and surface it.
   */
  reusedFromReportDated: string | null;
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

/* ── The slice Tanzil's validator reads ───────────────────────────────────── */

/**
 * `validator/README.md` documents exactly five fields it reads from a STARS
 * summary and states it assumes no others are present. Producing that slice
 * here means the planner and the next-semester validator can be handed the
 * same student without a translation step.
 */
export interface StarsSummarySlice {
  major: string;
  classLevel: ParsedStarsReport['classLevel'];
  gpa: number;
  completedCourses: Array<{ code: string; grade?: string }>;
  inProgressCourses: Array<{ code: string }>;
}

/* ── Catalogue ─────────────────────────────────────────────────────────────
   Field names follow catalog/README.md's course object so swapping the sample
   for `/catalog/20263/CSCI-104.json` is a URL change. */

export type FrequencyLabel = 'every_semester' | 'most_semesters' | 'occasionally' | 'rarely';

export interface OfferingFrequency {
  /** USC term codes the course appeared in across the scrape. */
  terms_offered: string[];
  count: number;
  frequency_label: FrequencyLabel;
}

export interface CatalogueCourse {
  /** Always `"PREFIX NNN"`, space-separated, per catalog/README.md. */
  course_name: string;
  units: number;
  description: string;
  has_d_clearance: boolean;
  has_restrictions: boolean;
}

export interface Catalogue {
  /** Human-readable label for where this data came from. */
  sourceLabel: string;
  courses: CatalogueCourse[];
  offering_frequency: Record<string, OfferingFrequency>;
  degrees: string[];
  majors: string[];
  minors: string[];
  catalogYears: string[];
}

/* ── Cross-highlighting ────────────────────────────────────────────────────
   A single value, so selecting something new clears the last one and Escape
   clears everything. */

export type Selection =
  | { kind: 'requirement'; id: string }
  | { kind: 'warning'; id: string }
  | null;

/* ── Export file ───────────────────────────────────────────────────────────── */

export interface PlanExportFile {
  schemaVersion: 2;
  kind: 'plansc.degree-planner.export';
  exportedOn: string;
  situation: StudentSituation;
  plan: Plan;
}
