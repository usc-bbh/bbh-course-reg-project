import type { ParsedStarsReport, StudentSituation } from '../domain/types';
import { sampleSituation } from './sampleStudent';

/**
 * STUB. Ignores the file it is given and returns the same object every time.
 *
 * The real parser is Abhi and Agastya's (`stars-parser/` in this repo). Nothing
 * in this file reads a PDF, and nothing in this app parses a report — the point
 * of the stub is to find out what the UI needs from a parsed report before that
 * parser is finished, not to guess at its answers.
 *
 * `test/stubs.test.ts` asserts that two different files produce a deeply equal
 * result, so this stays a stub.
 */

// GAP(stars): the UI needs the term each completed course was taken in
// (`fall-2025`, not just a course list) so it can lay history out on a timeline
// and lock it. STARS shows a term column; we need it carried through.
// GAP(stars): the UI needs in-progress coursework separated from completed
// coursework, because in-progress terms render as locked-but-ungraded.
// GAP(stars): the UI needs entry term (season + year) to know where the four
// year columns start. Nothing in the sample reports we have states it directly.
// GAP(stars): the UI needs transfer units as a single number to show in the
// situation summary; mapping transfer credit onto specific courses is a
// separate question we have not needed yet.
// GAP(stars): the UI needs declared minors as a list. Every sample we have
// carries at most one, and `null` when there is none.
const FIXED_STARS_SITUATION: StudentSituation = {
  ...sampleSituation,
  source: 'stars',
};

/**
 * @param _file The uploaded report. Deliberately unused: see above.
 */
export function parseStarsReport(_file: File): Promise<ParsedStarsReport> {
  void _file;
  return Promise.resolve(clone({ situation: FIXED_STARS_SITUATION }));
}

function clone<T>(value: T): T {
  return structuredClone(value);
}
