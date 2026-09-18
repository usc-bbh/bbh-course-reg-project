import type { StudentSituation } from '../../domain/types';
import { InfoIcon } from '../../components/icons';
import { reportDrift } from './reportDrift';

/**
 * Shown when the student has edited their major or catalogue year away from
 * what their report said. It states the change and what it costs, and stops
 * there — it does not re-judge a single requirement.
 */
export function ReportDriftNotice({ situation }: { situation: StudentSituation }) {
  const drift = reportDrift(situation);
  if (drift.length === 0) return null;

  return (
    <section
      aria-labelledby="drift-heading"
      className="print-block border-b border-warning-line bg-warning-wash"
    >
      <div className="mx-auto flex w-full max-w-[1600px] items-start gap-3 px-5 py-4 sm:px-8">
        <span className="mt-0.5 shrink-0 text-warning">
          <InfoIcon size={15} />
        </span>
        <div className="min-w-0">
          <h2 id="drift-heading" className="text-body font-semibold text-ink">
            This plan no longer matches the report it was read from
          </h2>
          <ul className="mt-1.5 flex flex-col gap-1.5">
            {drift.map((item) => (
              <li key={item.field} className="text-small leading-relaxed text-ink-2">
                <span className="font-medium text-ink">{item.label}:</span> your report says{' '}
                <span className="font-medium text-ink">{item.onReport}</span>, this plan says{' '}
                <span className="font-medium text-ink">{item.now}</span>. {item.consequence}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
