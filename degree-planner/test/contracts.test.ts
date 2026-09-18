import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { parseStarsReport } from '../src/data/parseStarsReport';
import { sampleStarsReport } from '../src/data/sampleStudent';
import { situationFromReport, toStarsSummary } from '../src/domain/situation';
import {
  isTransferPlaceholder,
  normalizeCourseCode,
  termIdFromUscCode,
  uscCodeFromTermId,
} from '../src/domain/uscTerms';

/**
 * The seams with other modules.
 *
 * CONTRIBUTING.md: "read the producer's own README rather than infer the shape
 * from its code." These tests hold this app to the shapes those documents
 * describe, so a drift on either side breaks here instead of surfacing as a
 * broken app weeks later — which is the reason fixtures/stars/ exists at all.
 */

/** The repo's canonical shared fixture, read from disk rather than copied. */
const COMMITTED_FIXTURE = JSON.parse(
  readFileSync(resolve(process.cwd(), '../fixtures/stars/mock_stars_report.json'), 'utf8'),
) as Record<string, unknown>;

describe('the STARS parser contract', () => {
  it('uses every field the committed shared fixture uses', () => {
    // fixtures/stars/README.md calls this file "the parser's expected OUTPUT
    // and the validator's stars_summary INPUT".
    const theirs = Object.keys(COMMITTED_FIXTURE).sort();
    const ours = Object.keys(sampleStarsReport).sort();
    const missing = theirs.filter((key) => !ours.includes(key));
    expect(missing, `our stub is missing fields the fixture has: ${missing.join(', ')}`).toEqual([]);
  });

  it('describes the same student as the committed fixture', () => {
    for (const key of ['degree', 'major', 'majorCode', 'programCode', 'catalogYear', 'classLevel', 'gpa'] as const) {
      expect(sampleStarsReport[key], `${key} differs from the shared fixture`).toEqual(
        COMMITTED_FIXTURE[key],
      );
    }
  });

  it('carries the report’s own requirement verdicts through untouched', () => {
    expect(sampleStarsReport.requirements).toEqual(COMMITTED_FIXTURE.requirements);
  });

  it('keeps minor singular and nullable, the way the parser emits it', () => {
    expect(sampleStarsReport.minor).toBeNull();
    expect(situationFromReport(sampleStarsReport).minor).toBeNull();
  });

  it('resolves rather than rejects, and can resolve with null', async () => {
    // stars-parser/README.md: "If both fail, returns null so the UI can prompt
    // the student to fill in their info manually."
    const result = await parseStarsReport(new File(['x'], 'r.pdf'));
    expect(result).not.toBeNull();
    // The type has to permit null, or the UI would never handle that path.
    const widened: Awaited<ReturnType<typeof parseStarsReport>> = null;
    expect(widened).toBeNull();
  });
});

describe('USC term codes', () => {
  it('decodes the digits docs/parser-brief.md §6 specifies', () => {
    // "1 = spring, 2 = summer, 3 = fall. So 20243 is fall 2024 and 20251 is spring 2025."
    expect(termIdFromUscCode('20243')).toBe('fall-2024');
    expect(termIdFromUscCode('20251')).toBe('spring-2025');
    expect(termIdFromUscCode('20252')).toBe('summer-2025');
  });

  it('round-trips every term code in the committed fixture', () => {
    const rows = [
      ...(COMMITTED_FIXTURE.completedCourses as Array<{ term: string }>),
      ...(COMMITTED_FIXTURE.inProgressCourses as Array<{ term: string }>),
    ];
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) {
      const termId = termIdFromUscCode(row.term);
      expect(termId, `could not decode ${row.term}`).not.toBeNull();
      expect(uscCodeFromTermId(termId as string)).toBe(row.term);
    }
  });

  it('rejects anything that is not a five-digit code', () => {
    expect(termIdFromUscCode('fall-2024')).toBeNull();
    expect(termIdFromUscCode('2024')).toBeNull();
    expect(termIdFromUscCode('20249')).toBeNull();
  });
});

describe('course codes', () => {
  it('normalises to the DEPT NNN form the validator and catalog agree on', () => {
    // validator/README.md: "normalized to DEPT ### (single space) everywhere".
    expect(normalizeCourseCode('BUAD304')).toBe('BUAD 304');
    expect(normalizeCourseCode('csci  104l')).toBe('CSCI 104L');
    expect(normalizeCourseCode('CSCI 104')).toBe('CSCI 104');
  });

  it('leaves generic transfer placeholders alone', () => {
    // docs/parser-brief.md §7: TR-PSYC "isn't a course code".
    expect(normalizeCourseCode('TR-PSYC')).toBe('TR-PSYC');
    expect(isTransferPlaceholder('TR-COMP-1')).toBe(true);
    expect(isTransferPlaceholder('CSCI 104')).toBe(false);
  });
});

describe('the validator’s stars_summary slice', () => {
  it('produces exactly the five fields validator/README.md documents', () => {
    const slice = toStarsSummary(sampleStarsReport);
    expect(Object.keys(slice).sort()).toEqual(
      ['classLevel', 'completedCourses', 'gpa', 'inProgressCourses', 'major'].sort(),
    );
    expect(slice.major).toBe('Computer Science');
    expect(slice.classLevel).toBe('Junior');
    // The GPA is the report's own, never a placeholder. The validator uses it
    // for GPA-threshold prerequisites, so a zero here would fail every one.
    expect(slice.gpa).toBe(sampleStarsReport.gpa);
    expect(slice.gpa).toBeGreaterThan(0);
    // It reads only `.code` off completed courses, plus `.grade`.
    for (const course of slice.completedCourses) {
      expect(Object.keys(course).every((key) => key === 'code' || key === 'grade')).toBe(true);
    }
    for (const course of slice.inProgressCourses) {
      expect(Object.keys(course)).toEqual(['code']);
    }
  });
});

describe('the shared fixture disagrees with itself about class level', () => {
  it('records the contradiction so it cannot be quietly inherited', () => {
    // docs/reference/01-reading-a-stars-report.md, "Class level comes from units
    // earned, not time enrolled [verified]": freshman under 32, sophomore 32 to
    // 63.9, junior 64 to 95.9, senior 96 and above.
    //
    // fixtures/stars/mock_stars_report.json earns 36 units and no transfer
    // credit, which is a SOPHOMORE, and states "Junior". The planner shows what
    // the report says and computes nothing, so it inherits the contradiction
    // either way. It matters beyond cosmetics: `classLevel` is one of the five
    // fields the next-semester validator reads, and it gates class-level
    // restricted courses.
    //
    // When this test fails, someone has fixed the fixture. Delete the test, the
    // GAP in sampleStudent.ts, and question P0 in
    // docs/degree-planner-ui-notes.md.
    const earned = (COMMITTED_FIXTURE.completedCourses as Array<{ units: number }>).reduce(
      (total, row) => total + row.units,
      0,
    );
    expect(earned).toBe(36);
    expect(COMMITTED_FIXTURE.transferUnits).toBe(0);
    expect(COMMITTED_FIXTURE.classLevel).toBe('Junior');
  });
});

describe('transfer credit', () => {
  it('keeps specific and generic credit apart', () => {
    // docs/parser-brief.md §7: both count toward 128 units, only the specific
    // kind can fill a named requirement.
    const situation = situationFromReport(sampleStarsReport);
    const sources = situation.completedCourses.map((course) => course.source);
    expect(sources).toContain('transfer_specific');
    expect(sources).toContain('transfer_generic');
    expect(sources).toContain('usc');
  });
});
