import { useId, useState } from 'react';
import type { AcademicYear } from '../../domain/terms';
import type { CatalogueCourse, PlanTerm, Season, TermId } from '../../domain/types';
import { formatUnits, isLocked, totalUnits } from '../../domain/terms';
import { Button } from '../../components/Button';
import { ChevronDownIcon, ChevronRightIcon, PlusIcon } from '../../components/icons';
import type { Highlight } from '../audit/highlight';
import { TermCard } from './TermCard';

export interface YearColumnProps {
  year: AcademicYear;
  index: number;
  allTerms: PlanTerm[];
  destinations: PlanTerm[];
  highlight: Highlight;
  onAddTerm: (season: Season, year: number) => void;
  onAddCourse: (termId: TermId, course: CatalogueCourse) => void;
  onMoveCourse: (courseId: string, toTermId: TermId) => void;
  onRemoveCourse: (termId: TermId, courseId: string) => void;
  onRemoveTerm: (termId: TermId) => void;
}

/**
 * One academic year: Fall above Spring above Summer.
 *
 * The marker beside the heading sits on the rail that runs across the whole
 * timeline — filled once the year is behind the student, hollow while it is
 * still being planned. Years are a real sequence, so they are drawn as one.
 */
export function YearColumn({
  year,
  index,
  allTerms,
  destinations,
  highlight,
  onAddTerm,
  onAddCourse,
  onMoveCourse,
  onRemoveCourse,
  onRemoveTerm,
}: YearColumnProps) {
  const [collapsed, setCollapsed] = useState(false);
  const headingId = useId();
  const bodyId = `${headingId}-body`;

  const allLocked = year.terms.length > 0 && year.terms.every(isLocked);
  const hasSummer = year.terms.some((term) => term.season === 'summer');
  const units = totalUnits(year.terms);

  return (
    <div className="print-block min-w-0">
      <header className="mb-3 flex items-center gap-2">
        <span
          aria-hidden="true"
          className={`h-[9px] w-[9px] shrink-0 rounded-full border-2 ${
            allLocked ? 'border-cardinal bg-cardinal' : 'border-cardinal bg-canvas'
          }`}
        />
        <h3 id={headingId} className="bg-canvas pr-2 text-[13px] font-semibold text-ink">
          Year {index + 1}
          <span className="ml-1.5 font-normal text-ink-4 tnum">{year.label}</span>
        </h3>
        <span className="tnum ml-auto bg-canvas pl-2 text-[11.5px] text-ink-4">
          {formatUnits(units)} units
        </span>
        <button
          type="button"
          className="-mr-1 rounded-chip p-1 text-ink-4 hover:bg-surface-sunk hover:text-ink md:hidden"
          aria-expanded={!collapsed}
          aria-controls={bodyId}
          onClick={() => setCollapsed((value) => !value)}
          data-print="hide"
        >
          {collapsed ? <ChevronRightIcon /> : <ChevronDownIcon />}
          <span className="sr-only">
            {collapsed ? `Show ${year.label}` : `Hide ${year.label}`}
          </span>
        </button>
      </header>

      <div
        id={bodyId}
        className={`${collapsed ? 'hidden md:flex' : 'flex'} flex-col gap-3`}
      >
        {year.terms.map((term) => (
          <TermCard
            key={term.id}
            term={term}
            allTerms={allTerms}
            destinations={destinations}
            highlight={highlight}
            onAddCourse={onAddCourse}
            onMoveCourse={onMoveCourse}
            onRemoveCourse={onRemoveCourse}
            onRemoveTerm={onRemoveTerm}
          />
        ))}

        {hasSummer ? null : (
          <Button
            size="sm"
            variant="quiet"
            className="self-start"
            data-print="hide"
            onClick={() => onAddTerm('summer', year.startYear + 1)}
          >
            <PlusIcon size={14} />
            Add Summer {year.startYear + 1}
          </Button>
        )}
      </div>
    </div>
  );
}
