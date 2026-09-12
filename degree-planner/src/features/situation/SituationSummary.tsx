import type { StudentSituation } from '../../domain/types';
import { formatUnits, seasonLabel } from '../../domain/terms';
import { Button } from '../../components/Button';
import { PencilIcon } from '../../components/icons';

const STANDING_LABEL: Record<StudentSituation['classStanding'], string> = {
  freshman: 'First year',
  sophomore: 'Second year',
  junior: 'Third year',
  senior: 'Fourth year',
};

/**
 * The compact, editable summary across the top of the workspace. Editing it
 * re-runs the check, because the check takes the situation as an input.
 */
export function SituationSummary({
  situation,
  onEdit,
}: {
  situation: StudentSituation;
  onEdit: () => void;
}) {
  const facts: Array<{ label: string; value: string }> = [
    { label: 'Major', value: situation.major || 'Not set' },
    {
      label: situation.minors.length === 1 ? 'Minor' : 'Minors',
      value: situation.minors.length > 0 ? situation.minors.join(', ') : 'None',
    },
    { label: 'Catalogue year', value: situation.catalogueYear },
    { label: 'Standing', value: STANDING_LABEL[situation.classStanding] },
    {
      label: 'Started',
      value: `${seasonLabel(situation.entryTerm.season)} ${situation.entryTerm.year}`,
    },
    { label: 'Transfer units', value: formatUnits(situation.transferUnits) },
    {
      label: 'Coursework on file',
      value: `${situation.completedCourses.length} completed, ${situation.inProgressCourses.length} in progress`,
    },
  ];

  return (
    <section
      aria-labelledby="situation-heading"
      className="print-block border-b border-line bg-surface"
    >
      <div className="mx-auto flex w-full max-w-[1600px] flex-wrap items-start gap-x-8 gap-y-4 px-5 py-5 sm:px-8">
        <div className="min-w-0 flex-1">
          <h1 id="situation-heading" className="wordmark text-title text-ink">
            {situation.studentName || 'Your degree plan'}
          </h1>
          {/* On a phone each fact is one row, label left and value right, so the
              summary stays a few lines instead of pushing the plan off screen.
              From tablet up it spreads out as a row of labelled values. */}
          <dl className="mt-3 flex flex-col sm:flex-row sm:flex-wrap sm:gap-x-8 sm:gap-y-3">
            {facts.map((fact) => (
              <div
                key={fact.label}
                className="flex items-baseline justify-between gap-4 border-b border-line-soft py-1.5 last:border-0 sm:block sm:min-w-0 sm:border-0 sm:py-0"
              >
                <dt className="shrink-0 text-micro text-ink-4">{fact.label}</dt>
                <dd className="tnum text-right text-small text-ink sm:text-left">{fact.value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <Button size="sm" onClick={onEdit} data-print="hide" className="mt-0.5">
          <PencilIcon />
          Edit details
        </Button>
      </div>
    </section>
  );
}
