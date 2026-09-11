import { describe, expect, it } from 'vitest';
import { STORAGE_KEY, STORAGE_PREFIX, clearSaved, readSaved, writeSaved } from '../src/state/persistence';
import { samplePlan, sampleSituation } from '../src/data/sampleStudent';

describe('persistence', () => {
  it('round-trips the situation and the plan', () => {
    writeSaved(sampleSituation, samplePlan);
    const read = readSaved();
    expect(read.kind).toBe('loaded');
    if (read.kind !== 'loaded') return;
    expect(read.situation).toEqual(sampleSituation);
    expect(read.plan).toEqual(samplePlan);
  });

  it('reports empty when nothing has been saved', () => {
    expect(readSaved().kind).toBe('empty');
  });

  it('discards a corrupt copy instead of crashing', () => {
    window.localStorage.setItem(STORAGE_KEY, '{"schemaVersion":1,"plan":');
    const read = readSaved();
    expect(read.kind).toBe('discarded');
  });

  it('discards a copy written by an earlier version', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ schemaVersion: 0, situation: sampleSituation, plan: samplePlan }),
    );
    const read = readSaved();
    expect(read.kind).toBe('discarded');
    if (read.kind === 'discarded') expect(read.reason).toMatch(/earlier version/);
  });

  it('clearing removes only this app’s keys', () => {
    writeSaved(sampleSituation, samplePlan);
    window.localStorage.setItem(`${STORAGE_PREFIX}scratch`, 'ours');
    window.localStorage.setItem('someoneElse.key', 'theirs');

    clearSaved();

    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(window.localStorage.getItem(`${STORAGE_PREFIX}scratch`)).toBeNull();
    expect(window.localStorage.getItem('someoneElse.key')).toBe('theirs');
  });
});
