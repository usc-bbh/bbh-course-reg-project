import { useEffect, useMemo, useState } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  pointerWithin,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import type { CatalogueCourse, PlanTerm, Season, Selection, TermId } from '../../domain/types';
import { groupByAcademicYear } from '../../domain/terms';
import { Button } from '../../components/Button';
import { PlusIcon } from '../../components/icons';
import type { Highlight } from '../audit/highlight';
import { YearColumn } from './YearColumn';

export interface PlanTimelineProps {
  /** The whole timeline: locked history first, then the planned terms. */
  timeline: PlanTerm[];
  /** Planned terms only — the legal destinations for a move. */
  destinations: PlanTerm[];
  highlight: Highlight;
  selection: Selection;
  onAddYear: () => void;
  onAddTerm: (season: Season, year: number) => void;
  onAddCourse: (termId: TermId, course: CatalogueCourse) => void;
  onMoveCourse: (courseId: string, toTermId: TermId) => void;
  onRemoveCourse: (termId: TermId, courseId: string) => void;
  onRemoveTerm: (termId: TermId) => void;
}

export function PlanTimeline({
  timeline,
  destinations,
  highlight,
  selection,
  onAddYear,
  onAddTerm,
  onAddCourse,
  onMoveCourse,
  onRemoveCourse,
  onRemoveTerm,
}: PlanTimelineProps) {
  const years = useMemo(() => groupByAcademicYear(timeline), [timeline]);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  const sensors = useSensors(
    // A few pixels of travel before a drag starts, so a click on the handle
    // never turns into an accidental move.
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

  const draggingCourse = draggingId
    ? timeline.flatMap((term) => term.courses).find((course) => course.id === draggingId)
    : undefined;

  // Bring the first highlighted thing into view when a selection is made.
  useEffect(() => {
    if (!selection) return;
    const firstCourse = [...highlight.courseKeys][0];
    const firstTerm = [...highlight.termIds][0];
    const selectorTarget = firstCourse
      ? `[data-course-key="${cssEscape(firstCourse)}"]`
      : firstTerm
        ? `[data-term-id="${cssEscape(firstTerm)}"]`
        : null;
    if (!selectorTarget) return;
    const element = document.querySelector(selectorTarget);
    if (!(element instanceof HTMLElement)) return;
    const reduced =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    element.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'nearest', inline: 'nearest' });
  }, [selection, highlight]);

  const onDragStart = (event: DragStartEvent) => setDraggingId(String(event.active.id));

  const onDragEnd = (event: DragEndEvent) => {
    setDraggingId(null);
    const over = event.over;
    if (!over) return;
    if (over.data.current?.locked === true) return;
    const from = event.active.data.current?.termId;
    const to = String(over.id);
    if (from === to) return;
    onMoveCourse(String(event.active.id), to);
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={pointerWithin}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragCancel={() => setDraggingId(null)}
    >
      <div className="relative">
        {/* The rail the year markers sit on. Years are a sequence, not a set. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-[0.7rem] hidden h-px bg-line-strong xl:block"
        />
        <div data-print-grid className="relative grid gap-x-7 gap-y-12 md:grid-cols-2 xl:grid-cols-4">
          {years.map((year, index) => (
            <YearColumn
              key={year.startYear}
              year={year}
              index={index}
              allTerms={timeline}
              destinations={destinations}
              highlight={highlight}
              onAddTerm={onAddTerm}
              onAddCourse={onAddCourse}
              onMoveCourse={onMoveCourse}
              onRemoveCourse={onRemoveCourse}
              onRemoveTerm={onRemoveTerm}
            />
          ))}
        </div>
      </div>

      <div className="mt-10" data-print="hide">
        <Button size="sm" onClick={onAddYear}>
          <PlusIcon size={14} />
          Add another year
        </Button>
      </div>

      <DragOverlay dropAnimation={null}>
        {draggingCourse ? (
          <div className="rounded-chip border border-cardinal bg-surface px-2 py-1.5 text-small shadow-overlay">
            <span className="course-code text-ink">{draggingCourse.code}</span>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

/** Minimal escaping for the attribute selectors above. */
function cssEscape(value: string): string {
  return value.replace(/["\\]/g, '\\$&');
}
