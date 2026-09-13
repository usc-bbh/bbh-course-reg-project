import { useId, useState } from 'react';
import type { Selection } from '../../domain/types';
import type { AnalysisState } from '../../state/useAnalysis';
import { IconButton } from '../../components/Button';
import { CheckCircleIcon, CloseIcon, FilledSquareIcon, InfoIcon } from '../../components/icons';
import { useFocusTrap } from '../../components/useFocusTrap';
import { AuditPanel } from './AuditPanel';
import { unmetCount } from './unmetCount';

export interface AuditSheetProps {
  state: AnalysisState;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  onRetry: () => void;
}

/**
 * The audit on narrow screens: a bar pinned to the bottom whose collapsed state
 * still shows the verdict, opening into a sheet that traps focus and closes on
 * Escape.
 */
export function AuditSheet({ state, selection, onSelect, onRetry }: AuditSheetProps) {
  const [open, setOpen] = useState(false);
  const panelRef = useFocusTrap(open, () => setOpen(false));
  const titleId = useId();

  const result =
    state.status === 'ready' ? state.result : state.status === 'pending' ? state.previous : null;

  const summary = (() => {
    if (state.status === 'failed') {
      return { label: 'Check failed', detail: 'Open for details', tone: 'text-warning', Icon: InfoIcon };
    }
    if (!result) {
      return { label: 'Checking…', detail: '', tone: 'text-ink-3', Icon: InfoIcon };
    }
    const unmet = unmetCount(result);
    if (result.verdict === 'on-track') {
      return {
        label: 'On track',
        detail: `${result.units.counted} of ${result.units.required} units counted`,
        tone: 'text-satisfied',
        Icon: CheckCircleIcon,
      };
    }
    return {
      label: result.verdict === 'not-yet' ? 'Not yet' : 'Not enough information',
      detail: `${unmet} not met, ${result.units.counted} of ${result.units.required} units counted`,
      tone: 'text-unsatisfied',
      Icon: result.verdict === 'not-yet' ? FilledSquareIcon : InfoIcon,
    };
  })();

  const SummaryIcon = summary.Icon;

  return (
    <div className="xl:hidden" data-print="hide">
      {/* Collapsed bar. The verdict is readable without opening anything. */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/95 backdrop-blur-sm">
        <button
          type="button"
          className="flex w-full items-center gap-3 px-4 py-3 text-left"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          <span className={`shrink-0 ${summary.tone}`}>
            <SummaryIcon size={16} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-body font-semibold text-ink">{summary.label}</span>
            {summary.detail ? (
              <span className="tnum block truncate text-micro text-ink-3">{summary.detail}</span>
            ) : null}
          </span>
          <span className="shrink-0 rounded-control border border-line-strong px-2.5 py-1 text-small text-ink-2">
            Show details
          </span>
        </button>
      </div>

      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-end bg-ink/35 backdrop-blur-[2px]"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            className="anim-rise max-h-[86vh] w-full overflow-y-auto rounded-t-panel border-t border-line bg-surface shadow-overlay outline-none"
          >
            <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-line-soft bg-surface px-4 py-3">
              <h2 id={titleId} className="wordmark text-lead text-ink">
                Your plan, checked
              </h2>
              <IconButton label="Close the check" size="sm" onClick={() => setOpen(false)}>
                <CloseIcon />
              </IconButton>
            </div>
            <AuditPanel
              state={state}
              selection={selection}
              onSelect={(next) => {
                onSelect(next);
                // Selecting sends the student back to the plan to see it.
                if (next) setOpen(false);
              }}
              onRetry={onRetry}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
