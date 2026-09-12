import { useEffect, useId, useRef, useState } from 'react';
import { useDndContext, useDroppable } from '@dnd-kit/core';
import type { CatalogueCourse, PlanTerm, TermId, WarningSeverity } from '../../domain/types';
import { formatUnits, isLocked, termLabel, termUnits } from '../../domain/terms';
import { Button, IconButton } from '../../components/Button';
import { LockIcon, PlusIcon, TrashIcon } from '../../components/icons';
import type { Highlight } from '../audit/highlight';
import { courseKey } from '../audit/highlight';
import { CourseRow } from './CourseRow';
import { CoursePicker } from './CoursePicker';

const STATUS_LABEL: Record<PlanTerm['status'], string> = {
  completed: 'Completed',
  'in-progress': 'In progress',
  planned: 'Planned',
};

export interface TermCardProps {
  term: PlanTerm;
  allTerms: PlanTerm[];
  destinations: PlanTerm[];
  highlight: Highlight;
  onAddCourse: (termId: TermId, course: CatalogueCourse) => void;
  onMoveCourse: (courseId: string, toTermId: TermId) => void;
  onRemoveCourse: (termId: TermId, courseId: string) => void;
  onRemoveTerm: (termId: TermId) => void;
}

export function TermCard({
  term,
  allTerms,
  destinations,
  highlight,
  onAddCourse,
  onMoveCourse,
  onRemoveCourse,
  onRemoveTerm,
}: TermCardProps) {
  const locked = isLocked(term);
  const [picking, setPicking] = useState(false);
  const addButtonRef = useRef<HTMLButtonElement | null>(null);
  const restoreFocus = useRef(false);
  const headingId = useId();

  const { active } = useDndContext();
  const { setNodeRef, isOver } = useDroppable({ id: term.id, data: { locked } });

  const dragging = active !== null;
  const validTarget = dragging && !locked;
  const invalidTarget = dragging && locked;

  const termHighlighted = highlight.termIds.has(term.id);
  const warnedSeverity: WarningSeverity | undefined = highlight.warnedTerms.get(term.id);
  const units = termUnits(term);

  // Escape anywhere in the picker closes it — the search field handles its own,
  // this covers focus sitting on Done or on an option.
  useEffect(() => {
    if (!picking) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        restoreFocus.current = true;
        setPicking(false);
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [picking]);

  // Focus goes back to the trigger once it is on the page again, which is a
  // render after the picker closes.
  useEffect(() => {
    if (picking || !restoreFocus.current) return;
    restoreFocus.current = false;
    addButtonRef.current?.focus();
  }, [picking]);

  const closePicker = () => {
    restoreFocus.current = true;
    setPicking(false);
  };

  return (
    <section
      ref={setNodeRef}
      aria-labelledby={headingId}
      data-term-id={term.id}
      className={`print-term relative rounded-card border transition-[border-color,background-color,box-shadow] duration-150 ${
        locked ? 'border-line bg-surface-sunk' : 'border-line bg-surface'
      } ${termHighlighted ? 'is-highlighted' : ''} ${
        isOver && validTarget ? 'border-cardinal bg-gold-wash shadow-raise' : ''
      } ${isOver && invalidTarget ? 'border-dashed border-ink-5 bg-surface-sunk' : ''} ${
        validTarget && !isOver ? 'border-dashed border-line-strong' : ''
      }`}
    >
      <header className="border-b border-line-soft px-4 py-3">
        <div className="flex items-baseline justify-between gap-3">
          <h4 id={headingId} className="truncate text-body font-semibold text-ink">
            {termLabel(term)}
          </h4>
          <span className="tnum shrink-0 text-micro text-ink-3">{formatUnits(units)} units</span>
        </div>
        <p className="mt-0.5 flex items-center gap-1 text-micro text-ink-5">
          {locked ? <LockIcon size={12} /> : null}
          {STATUS_LABEL[term.status]}
        </p>
      </header>

      {warnedSeverity && !termHighlighted ? (
        <p className="sr-only">This term is mentioned by a {warnedSeverity} warning.</p>
      ) : null}

      {term.courses.length === 0 ? (
        <p className="px-4 py-6 text-small text-ink-5">
          {locked ? 'No coursework recorded.' : 'Nothing planned yet.'}
        </p>
      ) : (
        <ul className="flex flex-col gap-1 px-2 py-2.5">
          {term.courses.map((course) => (
            <CourseRow
              key={course.id}
              course={course}
              termId={term.id}
              locked={locked}
              highlighted={highlight.courseKeys.has(courseKey(term.id, course.code))}
              warned={highlight.warnedCourses.get(courseKey(term.id, course.code))}
              destinations={destinations}
              onMove={(toTermId) => onMoveCourse(course.id, toTermId)}
              onRemove={() => onRemoveCourse(term.id, course.id)}
            />
          ))}
        </ul>
      )}

      {locked ? null : (
        <div className="px-3 pt-1 pb-3" data-print="hide">
          {picking ? (
            <CoursePicker
              termId={term.id}
              termName={termLabel(term)}
              allTerms={allTerms}
              onAdd={(course) => onAddCourse(term.id, course)}
              onClose={closePicker}
            />
          ) : (
            <div className="flex items-center gap-1">
              <Button
                ref={addButtonRef}
                size="sm"
                variant="quiet"
                data-focus-key={`add-${term.id}`}
                onClick={() => setPicking(true)}
                aria-label={`Add a course to ${termLabel(term)}`}
              >
                <PlusIcon size={14} />
                Add course
              </Button>
              {term.courses.length === 0 && term.season === 'summer' ? (
                <IconButton
                  label={`Remove ${termLabel(term)}`}
                  size="sm"
                  onClick={() => onRemoveTerm(term.id)}
                >
                  <TrashIcon size={14} />
                </IconButton>
              ) : null}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
