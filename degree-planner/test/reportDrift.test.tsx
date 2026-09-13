import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { reportDrift } from '../src/features/situation/reportDrift';
import { ReportDriftNotice } from '../src/features/situation/ReportDriftNotice';
import { blankSituation } from '../src/features/situation/blankSituation';
import { sampleSituation } from './sample';

/**
 * docs/reference/03 ends with the conditions that invalidate reusing a tier's
 * verdict. Two of them — a change of major that may cross schools, and a change
 * of catalogue year — are a text edit away in the review form, so the UI has to
 * notice them. Nothing here judges a requirement; it compares two strings.
 */
describe('drift from the report the verdicts were read from', () => {
  it('says nothing while the situation still matches the report', () => {
    expect(reportDrift(sampleSituation())).toEqual([]);
    render(<ReportDriftNotice situation={sampleSituation()} />);
    expect(screen.queryByText(/no longer matches the report/i)).toBeNull();
  });

  it('says nothing for a student who never uploaded a report', () => {
    const manual = { ...blankSituation(), major: 'Computer Science' };
    expect(manual.reportBasis).toBeNull();
    expect(reportDrift(manual)).toEqual([]);
  });

  it('names both values when the major is edited', () => {
    const drift = reportDrift({ ...sampleSituation(), major: 'Business Administration' });
    expect(drift).toHaveLength(1);
    expect(drift[0]?.field).toBe('major');
    expect(drift[0]?.onReport).toBe('Computer Science');
    expect(drift[0]?.now).toBe('Business Administration');
  });

  it('names both values when the catalogue year is edited', () => {
    const drift = reportDrift({ ...sampleSituation(), catalogYear: '2026-2027' });
    expect(drift).toHaveLength(1);
    expect(drift[0]?.field).toBe('catalogYear');
    expect(drift[0]?.onReport).toBe('2023-2024');
    expect(drift[0]?.now).toBe('2026-2027');
  });

  it('reports both at once, and says what each one costs', () => {
    const situation = {
      ...sampleSituation(),
      major: 'Business Administration',
      catalogYear: '2026-2027',
    };
    expect(reportDrift(situation).map((item) => item.field)).toEqual(['major', 'catalogYear']);

    render(<ReportDriftNotice situation={situation} />);
    expect(screen.getByText(/no longer matches the report/i)).toBeInTheDocument();
    expect(screen.getByText(/an advisor has to confirm them/i)).toBeInTheDocument();
    expect(screen.getByText(/a different set of rules/i)).toBeInTheDocument();
  });

  it('stays quiet while a field is being cleared mid-edit', () => {
    // An empty major is a half-typed one, not a change of programme.
    expect(reportDrift({ ...sampleSituation(), major: '' })).toEqual([]);
    expect(reportDrift({ ...sampleSituation(), catalogYear: '  ' })).toEqual([]);
  });
});
