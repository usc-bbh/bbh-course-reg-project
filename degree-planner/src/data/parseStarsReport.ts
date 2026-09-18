import type { ParsedStarsReport } from '../domain/types';
import { sampleStarsReport } from './sampleStudent';

/**
 * STUB. Ignores the file it is given and returns the same object every time.
 *
 * The real parser is Abhi and Agastya's (`stars-parser/` in this repo). Nothing
 * in this file reads a PDF, and nothing in this app parses a report.
 *
 * Two things here are copied from `stars-parser/README.md` rather than
 * invented, because CONTRIBUTING.md says to read the producer's own README:
 *
 *   1. The **shape** is the parser's documented output, field for field, and
 *      the values are `fixtures/stars/mock_stars_report.json` — the shared
 *      fixture both the parser tests and the validator already use.
 *   2. The **signature**. The real parser takes `(file, { onStatus, onProgress })`
 *      and *resolves with `null`* when both the text and OCR paths fail — its
 *      README says "returns null so the UI can prompt the student to fill in
 *      their info manually". It does not reject. The UI handles null as the
 *      parse-failure path and treats a rejection as an unexpected error.
 *
 * `test/stubs.test.ts` asserts that two different files produce a deeply equal
 * result, so this stays a stub.
 */

// GAP(stars): the report has the entry term — docs/reference/01 lists "term of
// USC entrance" in the pertinent-data section — but the parser does not emit
// it yet. The planner needs it to know where the year columns start; a spring
// entrant's four academic years are not a fall entrant's. We read it from
// `entryTerm` here and fall back to the earliest course term.
// GAP(stars): `source` per course row (usc | transfer_specific |
// transfer_generic) is specified in docs/parser-brief.md §6 but is not in the
// parser's README output example or in the committed fixture yet. Without it
// the planner cannot tell credit that can fill a requirement from credit that
// only adds units, which §7 says would understate what a student has left.
// GAP(stars): course-code spacing disagrees across the repo. The parser's
// README shows `"BUAD304"`, its own committed fixture shows `"CSCI 103"`, and
// validator/README.md says codes are normalised to `"DEPT ###"` with one space
// "everywhere in this module". We normalise on the way in (uscTerms.ts) and
// would rather the parser settle it.
// GAP(stars): `requirements[].label` is free text off the report, so there is
// no stable id to hang cross-highlighting or preferences on. Two reports for
// the same student could word a block differently.
// GAP(stars): the report's prepared date is not in the parser output.
// docs/reference/03 says a reused verdict inherits that date and it must be
// surfaced rather than presented as current. We hard-code it in analyzePlan.ts.

export interface ParseOptions {
  onStatus?: (message: string) => void;
  onProgress?: (page: number, total: number) => void;
}

/**
 * @param _file    The uploaded report. Deliberately unused: see above.
 * @param _options Progress callbacks the real parser uses for OCR. Unused here.
 * @returns The parsed report, or null if it could not be read.
 */
export function parseStarsReport(
  _file: File,
  _options: ParseOptions = {},
): Promise<ParsedStarsReport | null> {
  void _file;
  void _options;
  return Promise.resolve(structuredClone(sampleStarsReport));
}
