import type { AnalysisResult, Selection, TermId, WarningSeverity } from '../../domain/types';

/** One key for "this course, in this term". */
export function courseKey(termId: TermId, code: string): string {
  return `${termId}::${code}`;
}

export interface Highlight {
  /** Courses the current selection points at. */
  courseKeys: Set<string>;
  /** Terms the current selection points at. */
  termIds: Set<TermId>;
  /** Courses any warning references, at all times — the small indicator. */
  warnedCourses: Map<string, WarningSeverity>;
  /** Terms any warning references, at all times. */
  warnedTerms: Map<TermId, WarningSeverity>;
}

const EMPTY: Highlight = {
  courseKeys: new Set(),
  termIds: new Set(),
  warnedCourses: new Map(),
  warnedTerms: new Map(),
};

const SEVERITY_RANK: Record<WarningSeverity, number> = { info: 0, warning: 1, blocking: 2 };

function keepStronger(
  map: Map<string, WarningSeverity>,
  key: string,
  severity: WarningSeverity,
): void {
  const existing = map.get(key);
  if (!existing || SEVERITY_RANK[severity] > SEVERITY_RANK[existing]) map.set(key, severity);
}

/**
 * Turns the current selection into the set of things the timeline should light
 * up. Pure lookup over what the analysis result already said — nothing here
 * decides which courses satisfy anything.
 */
export function buildHighlight(result: AnalysisResult | null, selection: Selection): Highlight {
  if (!result) return EMPTY;

  const warnedCourses = new Map<string, WarningSeverity>();
  const warnedTerms = new Map<TermId, WarningSeverity>();
  for (const warning of result.warnings) {
    if (warning.course?.termId) {
      keepStronger(warnedCourses, courseKey(warning.course.termId, warning.course.code), warning.severity);
    }
    if (warning.termId) keepStronger(warnedTerms, warning.termId, warning.severity);
  }

  const courseKeys = new Set<string>();
  const termIds = new Set<TermId>();

  if (selection?.kind === 'requirement') {
    // Courses only. A requirement points at specific courses, so ringing whole
    // terms as well would say less, louder.
    const requirement = result.requirements.find((entry) => entry.id === selection.id);
    for (const ref of requirement?.satisfiedBy ?? []) {
      if (!ref.termId) continue;
      courseKeys.add(courseKey(ref.termId, ref.code));
    }
  } else if (selection?.kind === 'warning') {
    const warning = result.warnings.find((entry) => entry.id === selection.id);
    if (warning?.course?.termId) {
      courseKeys.add(courseKey(warning.course.termId, warning.course.code));
      termIds.add(warning.course.termId);
    }
    if (warning?.termId) termIds.add(warning.termId);
  }

  return { courseKeys, termIds, warnedCourses, warnedTerms };
}

/** How many references a selection has, so the UI can say when there are none. */
export function highlightCount(highlight: Highlight): number {
  return highlight.courseKeys.size + highlight.termIds.size;
}
