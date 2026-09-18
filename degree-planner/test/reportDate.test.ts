import { describe, expect, it } from 'vitest';
import { formatReportDate } from '../src/features/audit/reportDate';

describe('the date a reused verdict came from', () => {
  it('reads the way a STARS report writes a date', () => {
    expect(formatReportDate('2025-02-14')).toBe('14 February 2025');
    expect(formatReportDate('2027-05-16')).toBe('16 May 2027');
    expect(formatReportDate('2024-12-01')).toBe('1 December 2024');
  });

  it('does not depend on the reader’s time zone', () => {
    // A Date-based formatter turns this into 13 February for anyone west of
    // UTC. The parser here never builds a Date, so the day cannot shift.
    expect(formatReportDate('2025-02-14')).toContain('14');
  });

  it('passes anything that is not an ISO date straight through', () => {
    // The parser does not emit this field yet, so whatever arrives is shown as
    // it arrived rather than mangled into a wrong date.
    expect(formatReportDate('14 February 2025')).toBe('14 February 2025');
    expect(formatReportDate('2025-13-01')).toBe('2025-13-01');
    expect(formatReportDate('')).toBe('');
  });
});
