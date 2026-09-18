import type { Plan, StudentSituation } from '../domain/types';
import { SCHEMA_VERSION, checkPlan, checkSituation } from '../domain/validate';

/**
 * Persistence.
 *
 * Only parsed fields and the plan are ever written — never the uploaded file,
 * never anything that could be a raw report. Everything lives under one prefix
 * so "Clear all data" can remove this app's keys and leave every other app on
 * the origin alone.
 *
 * Nothing here runs during the first paint. `readSaved()` is called from an
 * effect after mount, because a static build renders its HTML before any
 * browser storage exists and branching on storage during render is how a page
 * ends up showing one thing on the server and another in the browser.
 */

export const STORAGE_PREFIX = 'plansc.degreePlanner.';
export const STORAGE_KEY = `${STORAGE_PREFIX}v1`;

interface SavedShape {
  schemaVersion: 2;
  situation: StudentSituation | null;
  plan: Plan;
}

export type ReadResult =
  | { kind: 'empty' }
  | { kind: 'loaded'; situation: StudentSituation | null; plan: Plan }
  | { kind: 'discarded'; reason: string };

function storage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    // Private browsing and blocked-cookie settings both throw on access.
    return null;
  }
}

export function readSaved(): ReadResult {
  const store = storage();
  if (!store) return { kind: 'empty' };

  let raw: string | null;
  try {
    raw = store.getItem(STORAGE_KEY);
  } catch {
    return { kind: 'empty' };
  }
  if (!raw) return { kind: 'empty' };

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return { kind: 'discarded', reason: 'the saved copy could not be read' };
  }

  if (typeof parsed !== 'object' || parsed === null) {
    return { kind: 'discarded', reason: 'the saved copy could not be read' };
  }
  const candidate = parsed as Record<string, unknown>;
  if (candidate.schemaVersion !== SCHEMA_VERSION) {
    return { kind: 'discarded', reason: 'it was saved by an earlier version of this planner' };
  }

  const plan = checkPlan(candidate.plan);
  if (!plan.ok) return { kind: 'discarded', reason: plan.problem };

  if (candidate.situation === null || candidate.situation === undefined) {
    return { kind: 'loaded', situation: null, plan: plan.value };
  }
  const situation = checkSituation(candidate.situation);
  if (!situation.ok) return { kind: 'discarded', reason: situation.problem };

  return { kind: 'loaded', situation: situation.value, plan: plan.value };
}

export function writeSaved(situation: StudentSituation | null, plan: Plan): void {
  const store = storage();
  if (!store) return;
  const payload: SavedShape = { schemaVersion: 2, situation, plan };
  try {
    store.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // A full or unavailable quota must never take the app down. The student
    // keeps working in memory; the autosave line reports the failure.
    throw new Error('not-saved');
  }
}

/** Removes this app's keys only. Anything else on the origin is left alone. */
export function clearSaved(): void {
  const store = storage();
  if (!store) return;
  try {
    const doomed: string[] = [];
    for (let index = 0; index < store.length; index += 1) {
      const key = store.key(index);
      if (key && key.startsWith(STORAGE_PREFIX)) doomed.push(key);
    }
    doomed.forEach((key) => store.removeItem(key));
  } catch {
    // Nothing to do: if storage cannot be read it cannot be holding data.
  }
}
