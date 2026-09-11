import { useCallback, useEffect, useState } from 'react';
import type { AnalysisResult, PlanTerm, StudentSituation } from '../domain/types';
import { analyzePlan } from '../data/analyzePlan';

export type AnalysisState =
  | { status: 'idle' }
  | { status: 'pending'; previous: AnalysisResult | null }
  | { status: 'ready'; result: AnalysisResult }
  | { status: 'failed'; message: string };

type Outcome =
  | { key: string; result: AnalysisResult }
  | { key: string; message: string }
  | null;

/**
 * The one place the analysis layer is called.
 *
 * It re-runs whenever the situation or the timeline changes. The stub returns
 * the same result every time, so edits will not change the audit — that is
 * correct, and the sample badge says so on screen. Nothing here compensates
 * for it.
 *
 * Pending is derived rather than stored: while the key of the last outcome is
 * not the key of the current inputs, the check is in flight. That keeps every
 * state change inside a promise callback, where it belongs.
 */
export function useAnalysis(
  situation: StudentSituation | null,
  terms: PlanTerm[],
): { state: AnalysisState; retry: () => void } {
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [attempt, setAttempt] = useState(0);

  // Content, not identity: the timeline is rebuilt whenever the plan changes.
  const runKey = situation ? `${attempt}::${JSON.stringify({ situation, terms })}` : null;

  useEffect(() => {
    if (!situation || runKey === null) return;
    let cancelled = false;

    analyzePlan({ situation, terms })
      .then((result) => {
        if (!cancelled) setOutcome({ key: runKey, result });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        // The shape of the failure, never the student's data.
        setOutcome({
          key: runKey,
          message:
            error instanceof Error && error.message
              ? error.message
              : 'The check could not be completed.',
        });
      });

    return () => {
      cancelled = true;
    };
  }, [runKey, situation, terms]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);

  const state = deriveState(runKey, outcome);
  return { state, retry };
}

function deriveState(runKey: string | null, outcome: Outcome): AnalysisState {
  if (runKey === null) return { status: 'idle' };
  if (!outcome || outcome.key !== runKey) {
    return { status: 'pending', previous: outcome && 'result' in outcome ? outcome.result : null };
  }
  return 'result' in outcome
    ? { status: 'ready', result: outcome.result }
    : { status: 'failed', message: outcome.message };
}
