import { useState } from 'react';
import type { Requirement, TallyUnit } from '../../domain/types';
import type { Selection } from '../../domain/types';
import { formatUnits } from '../../domain/terms';
import { ChevronDownIcon, ChevronRightIcon } from '../../components/icons';
import { StatusTag } from '../../components/StatusTag';
import { requirementPresentation } from '../../components/status';

const TALLY_LABEL: Record<TallyUnit, string> = {
  UNITS: 'units',
  COURSES: 'courses',
  'SUB-GROUP(S)': 'sub-requirements',
  GPA: 'grade points',
};

export interface RequirementListProps {
  requirements: Requirement[];
  selection: Selection;
  onSelect: (selection: Selection) => void;
}

/**
 * Missing before done: unmet requirements are expanded with their reason,
 * in-progress ones follow, and satisfied ones collapse behind a count.
 */
export function RequirementList({ requirements, selection, onSelect }: RequirementListProps) {
  const [showSatisfied, setShowSatisfied] = useState(false);

  const unmet = requirements.filter((requirement) => requirement.status === 'unsatisfied');
  const inProgress = requirements.filter((requirement) => requirement.status === 'in-progress');
  const satisfied = requirements.filter((requirement) => requirement.status === 'satisfied');

  return (
    <section aria-labelledby="requirements-heading" className="print-block">
      <h3 id="requirements-heading" className="px-5 text-small font-semibold text-ink">
        Missing before you are done
      </h3>
      <p className="px-5 pt-1 pb-3 text-micro text-ink-5" data-print="hide">
        Select any requirement or warning to highlight it in the plan. Escape clears it.
      </p>

      {unmet.length === 0 ? (
        <p className="px-5 pb-4 text-small text-ink-3">Nothing is outstanding in this check.</p>
      ) : (
        <ul className="flex flex-col">
          {unmet.map((requirement) => (
            <RequirementRow
              key={requirement.id}
              requirement={requirement}
              expanded
              selected={selection?.kind === 'requirement' && selection.id === requirement.id}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}

      {inProgress.length > 0 ? (
        <>
          <h3 className="px-5 pt-6 pb-3 text-small font-semibold text-ink">Under way</h3>
          <ul className="flex flex-col">
            {inProgress.map((requirement) => (
              <RequirementRow
                key={requirement.id}
                requirement={requirement}
                expanded={false}
                selected={selection?.kind === 'requirement' && selection.id === requirement.id}
                onSelect={onSelect}
              />
            ))}
          </ul>
        </>
      ) : null}

      {satisfied.length > 0 ? (
        <div className="mt-5 border-t border-line-soft">
          <button
            type="button"
            className="flex w-full items-center gap-2 px-5 py-3.5 text-left text-small text-ink-2 hover:bg-surface-2"
            aria-expanded={showSatisfied}
            onClick={() => setShowSatisfied((value) => !value)}
            data-print="hide"
          >
            {showSatisfied ? <ChevronDownIcon /> : <ChevronRightIcon />}
            <span className="font-medium text-ink">{satisfied.length} satisfied</span>
            <span className="text-ink-4">
              {showSatisfied ? 'Hide the list' : 'Show the list'}
            </span>
          </button>
          {showSatisfied ? (
            <ul className="anim-expand flex flex-col pb-2">
              {satisfied.map((requirement) => (
                <RequirementRow
                  key={requirement.id}
                  requirement={requirement}
                  expanded={false}
                  selected={selection?.kind === 'requirement' && selection.id === requirement.id}
                  onSelect={onSelect}
                />
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function RequirementRow({
  requirement,
  expanded,
  selected,
  onSelect,
}: {
  requirement: Requirement;
  expanded: boolean;
  selected: boolean;
  onSelect: (selection: Selection) => void;
}) {
  const presentation = requirementPresentation(requirement.status);
  const hasRefs = requirement.satisfiedBy.some((ref) => ref.termId);

  return (
    <li className="print-block">
      <button
        type="button"
        aria-pressed={selected}
        className={`w-full border-l-[3px] px-5 py-3.5 text-left transition-colors duration-150 hover:bg-surface-2 ${
          selected ? 'border-l-cardinal bg-gold-wash' : 'border-l-transparent'
        }`}
        onClick={() => onSelect(selected ? null : { kind: 'requirement', id: requirement.id })}
      >
        <span className="flex items-baseline justify-between gap-3">
          <span
            className={`text-body text-ink ${presentation.emphatic ? 'font-semibold' : 'font-medium'}`}
          >
            {requirement.name}
          </span>
          <StatusTag presentation={presentation} className="self-center" />
        </span>

        <span className="mt-0.5 flex flex-wrap items-baseline gap-x-3 text-micro text-ink-4">
          <span className="capitalize">{requirement.tier}</span>
          {requirement.tally ? (
            <span className="tnum">
              {formatUnits(requirement.tally.counted)} of {formatUnits(requirement.tally.required)}{' '}
              {TALLY_LABEL[requirement.tally.unit]}
            </span>
          ) : null}
          {requirement.source === 'stars' ? <span>read from your report</span> : null}
        </span>

        {expanded && requirement.reason ? (
          <span className="mt-1.5 block text-small leading-relaxed text-ink-2">
            {requirement.reason}
          </span>
        ) : null}

        {hasRefs && selected ? (
          <span className="mt-1.5 block text-micro text-ink-4" data-print="hide">
            Highlighted in the plan.
          </span>
        ) : null}
      </button>
    </li>
  );
}
