import { describe, expect, it } from 'vitest';
import { buildExport, exportFileName, readImport } from '../src/features/toolbar/planFile';
import { samplePlan } from '../src/data/sampleStudent';
import { sampleSituation } from './sample';
import { SCHEMA_VERSION, checkExportFile } from '../src/domain/validate';

const FIXED_DAY = new Date(2026, 8, 11);

describe('export and import', () => {
  it('names the file without the student in it', () => {
    expect(exportFileName(FIXED_DAY)).toBe('degree-plan-2026-09-11.json');
    expect(exportFileName(FIXED_DAY)).not.toMatch(/Samplewood/i);
  });

  it('round-trips through the validator', async () => {
    const payload = buildExport(sampleSituation(), samplePlan, FIXED_DAY);
    const file = new File([JSON.stringify(payload)], 'degree-plan.json', {
      type: 'application/json',
    });
    const imported = await readImport(file);
    expect(imported.ok).toBe(true);
    if (!imported.ok) return;
    expect(imported.value.situation).toEqual(sampleSituation());
    expect(imported.value.plan).toEqual(samplePlan);
  });

  it('names the actual problem when the file is cut short', async () => {
    const payload = JSON.stringify(buildExport(sampleSituation(), samplePlan, FIXED_DAY));
    const truncated = new File([payload.slice(0, payload.length / 2)], 'half.json');
    const imported = await readImport(truncated);
    expect(imported.ok).toBe(false);
    if (imported.ok) return;
    expect(imported.problem).toMatch(/cut short/);
  });

  it('rejects a file that is valid JSON but not a plan', () => {
    const checked = checkExportFile({ hello: 'world' });
    expect(checked.ok).toBe(false);
    if (checked.ok) return;
    expect(checked.problem).toMatch(/not a plan file|not exported/);
  });

  it('rejects a plan file whose plan is missing', () => {
    const checked = checkExportFile({
      schemaVersion: SCHEMA_VERSION,
      kind: 'plansc.degree-planner.export',
      exportedOn: '2026-09-11',
      situation: sampleSituation(),
    });
    expect(checked.ok).toBe(false);
    if (checked.ok) return;
    expect(checked.problem).toMatch(/plan is missing/);
  });
});
