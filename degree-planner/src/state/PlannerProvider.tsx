import { useEffect, useMemo, useReducer, useRef, useState, type ReactNode } from 'react';
import { PlannerContext, initialState, plannerReducer } from './plannerStore';
import { readSaved, writeSaved } from './persistence';

const SAVE_DEBOUNCE_MS = 400;

/**
 * Holds the situation and the plan, reads the saved copy once after mount, and
 * writes it back on a debounce.
 *
 * The saved copy is read in an effect rather than during render. A static build
 * ships pre-rendered HTML, so anything that branches on localStorage during the
 * first paint renders one thing in the build and another in the browser.
 */
export function PlannerProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(plannerReducer, initialState);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const hydratedRef = useRef(false);

  useEffect(() => {
    if (hydratedRef.current) return;
    hydratedRef.current = true;
    const saved = readSaved();
    if (saved.kind === 'loaded') {
      dispatch({
        type: 'hydrated',
        situation: saved.situation,
        plan: saved.plan,
        notice: null,
      });
    } else if (saved.kind === 'discarded') {
      dispatch({
        type: 'hydrated',
        situation: null,
        plan: initialState.plan,
        notice: `We could not reopen your last plan because ${saved.reason}. Starting fresh.`,
      });
    } else {
      dispatch({ type: 'hydrated', situation: null, plan: initialState.plan, notice: null });
    }
  }, []);

  useEffect(() => {
    if (!state.hydrated) return;
    const timer = window.setTimeout(() => {
      setSaveState('saving');
      try {
        writeSaved(state.situation, state.plan);
        setSaveState('saved');
      } catch {
        setSaveState('error');
      }
    }, SAVE_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [state.hydrated, state.situation, state.plan]);

  const value = useMemo(() => ({ state, dispatch, saveState }), [state, saveState]);

  return <PlannerContext.Provider value={value}>{children}</PlannerContext.Provider>;
}
