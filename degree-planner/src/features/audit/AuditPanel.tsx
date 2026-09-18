import type { Selection } from '../../domain/types';
import type { AnalysisState } from '../../state/useAnalysis';
import { Button } from '../../components/Button';
import { InfoIcon } from '../../components/icons';
import { unmetCount } from './unmetCount';
import { VerdictCard } from './VerdictCard';
import { RequirementList } from './RequirementList';
import { WarningList } from './WarningList';

export interface AuditPanelProps {
  state: AnalysisState;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  onRetry: () => void;
}

/**
 * The audit: verdict first, then what is missing, then what is worth a look.
 *
 * Live wiring, fixed answers. The check re-runs whenever the situation or the
 * plan changes, and the stub returns the same result every time — so edits will
 * not move these numbers. The badge below says so, on screen and in print.
 */
export function AuditPanel({ state, selection, onSelect, onRetry }: AuditPanelProps) {
  const result =
    state.status === 'ready' ? state.result : state.status === 'pending' ? state.previous : null;

  if (state.status === 'failed') {
    return (
      <div role="alert" className="px-5 py-6">
        <p className="text-body font-semibold text-ink">We could not check this plan.</p>
        <p className="mt-1 text-small leading-relaxed text-ink-2">
          {state.message} Your plan is untouched and you can keep editing it.
        </p>
        <Button className="mt-3" onClick={onRetry}>
          Check again
        </Button>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="px-5 py-6">
        <p className="text-body text-ink-3" role="status">
          {state.status === 'pending' ? 'Checking your plan…' : 'Add your details to see a check.'}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {result.isSample ? <SampleBadge /> : null}

      {state.status === 'pending' ? (
        <p className="px-5 pt-4 text-micro text-ink-4" role="status">
          Checking your plan…
        </p>
      ) : null}

      <VerdictCard result={result} unmetCount={unmetCount(result)} />

      <div className="border-t border-line-soft pt-5">
        <RequirementList
          requirements={result.requirements}
          selection={selection}
          onSelect={onSelect}
        />
      </div>

      <WarningList warnings={result.warnings} selection={selection} onSelect={onSelect} />
    </div>
  );
}

/**
 * Driven entirely by `AnalysisResult.isSample`. When the real analysis layer
 * lands and returns false, this disappears with no change to any component.
 */
export function SampleBadge({ className = '' }: { className?: string }) {
  return (
    <p
      className={`print-block flex items-start gap-2.5 border-b border-warning-line bg-warning-wash px-5 py-3.5 text-small leading-relaxed text-ink-2 ${className}`}
    >
      <span className="mt-0.5 shrink-0 text-warning">
        <InfoIcon size={14} />
      </span>
      <span>
        <span className="font-semibold text-ink">Sample results.</span> These do not reflect your
        edits yet.
      </span>
    </p>
  );
}
