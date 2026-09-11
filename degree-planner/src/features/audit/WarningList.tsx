import type { PlanWarning, Selection } from '../../domain/types';
import { StatusTag } from '../../components/StatusTag';
import { warningPresentation } from '../../components/status';

const ORDER: Record<PlanWarning['severity'], number> = { blocking: 0, warning: 1, info: 2 };

export interface WarningListProps {
  warnings: PlanWarning[];
  selection: Selection;
  onSelect: (selection: Selection) => void;
}

/** Severity is carried by icon and text label, never by colour alone. */
export function WarningList({ warnings, selection, onSelect }: WarningListProps) {
  if (warnings.length === 0) return null;
  const sorted = [...warnings].sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);

  return (
    <section aria-labelledby="warnings-heading" className="print-block border-t border-line-soft">
      <h3 id="warnings-heading" className="px-4 pt-4 pb-2 text-[13px] font-semibold text-ink">
        Worth a look ({warnings.length})
      </h3>
      <ul className="flex flex-col gap-2 px-4 pb-4">
        {sorted.map((warning) => {
          const presentation = warningPresentation(warning.severity);
          const selected = selection?.kind === 'warning' && selection.id === warning.id;
          const targets = Boolean(warning.course?.termId ?? warning.termId);
          return (
            <li key={warning.id} className="print-block">
              <button
                type="button"
                aria-pressed={selected}
                className={`w-full rounded-card border px-3 py-2.5 text-left transition-[box-shadow,border-color] duration-150 ${presentation.surface} ${
                  selected ? 'shadow-raise ring-2 ring-cardinal' : ''
                }`}
                onClick={() => onSelect(selected ? null : { kind: 'warning', id: warning.id })}
              >
                <span className="flex items-center gap-2">
                  <StatusTag presentation={presentation} />
                  {warning.course ? (
                    <span className="course-code ml-auto text-[11.5px] text-ink-3">
                      {warning.course.code}
                    </span>
                  ) : null}
                </span>
                <span className="mt-1 block text-[13px] leading-relaxed text-ink-2">
                  {warning.message}
                </span>
                {targets && selected ? (
                  <span className="mt-1 block text-[11.5px] text-ink-4" data-print="hide">
                    Highlighted in the plan.
                  </span>
                ) : null}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
