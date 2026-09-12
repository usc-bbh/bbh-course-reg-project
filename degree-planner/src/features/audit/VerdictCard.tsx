import type { AnalysisResult, Verdict } from '../../domain/types';
import { formatUnits } from '../../domain/terms';
import { CheckCircleIcon, FilledSquareIcon, InfoIcon } from '../../components/icons';

const VERDICT: Record<Verdict, { label: string; tone: string; icon: typeof InfoIcon }> = {
  'on-track': { label: 'On track', tone: 'text-satisfied', icon: CheckCircleIcon },
  'not-yet': { label: 'Not yet', tone: 'text-unsatisfied', icon: FilledSquareIcon },
  unknown: { label: 'Not enough information', tone: 'text-inprogress', icon: InfoIcon },
};

/**
 * Verdict first, in plain language.
 *
 * The verdict carries its weight through type size and a cardinal rule, not
 * through a coloured panel — cardinal is the brand here and cannot also mean
 * "unsatisfied". The verdict word itself uses the same status vocabulary as
 * everything else in the panel: an icon, a label, and a colour, in that order.
 */
export function VerdictCard({ result, unmetCount }: { result: AnalysisResult; unmetCount: number }) {
  const verdict = VERDICT[result.verdict];
  const Icon = verdict.icon;
  const underway = result.requirements.filter((entry) => entry.status === 'in-progress').length;
  const done = result.requirements.filter((entry) => entry.status === 'satisfied').length;
  const percent =
    result.unitsRequired > 0
      ? Math.min(100, Math.round((result.unitsCounted / result.unitsRequired) * 100))
      : 0;

  return (
    <div className="print-block border-l-[3px] border-l-cardinal bg-surface px-5 py-5">
      <p className={`flex items-center gap-2 text-small font-semibold ${verdict.tone}`}>
        <Icon size={15} />
        {verdict.label}
      </p>
      <p className="wordmark mt-2 text-title leading-snug text-ink">{result.headline}</p>

      <dl className="mt-4 flex flex-wrap gap-x-7 gap-y-2">
        {[
          { label: 'Not met', value: unmetCount },
          { label: 'Under way', value: underway },
          { label: 'Satisfied', value: done },
        ].map((count) => (
          <div key={count.label}>
            <dt className="text-micro text-ink-4">{count.label}</dt>
            <dd className="tnum text-small font-medium text-ink">{count.value}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-5">
        <div className="flex items-baseline justify-between text-small">
          <span className="text-ink-3">Units counted</span>
          <span className="tnum font-medium text-ink">
            {formatUnits(result.unitsCounted)} of {formatUnits(result.unitsRequired)}
          </span>
        </div>
        <div
          data-print="hide"
          className="mt-1.5 h-2 w-full overflow-hidden rounded-pill bg-line"
          role="img"
          aria-label={`${formatUnits(result.unitsCounted)} of ${formatUnits(
            result.unitsRequired,
          )} units counted toward the degree`}
        >
          <div className="h-full rounded-pill bg-cardinal" style={{ width: `${percent}%` }} />
        </div>
      </div>
    </div>
  );
}
