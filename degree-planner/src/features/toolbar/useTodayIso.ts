import { useSyncExternalStore } from 'react';
import { isoDate } from './planFile';

/**
 * Today's date, as `2026-09-11`, for the printed plan only.
 *
 * It is read through `useSyncExternalStore` so the first render never depends
 * on it: the shell renders an empty string and the real date arrives once the
 * component is running in a browser. Nothing else in this app reads the clock —
 * a term is in the past because its status says so, never because of today's
 * date.
 */
const subscribeToNothing = () => () => {};

let cached: string | null = null;

function readClient(): string {
  if (cached === null) cached = isoDate(new Date());
  return cached;
}

function readShell(): string {
  return '';
}

export function useTodayIso(): string {
  return useSyncExternalStore(subscribeToNothing, readClient, readShell);
}
