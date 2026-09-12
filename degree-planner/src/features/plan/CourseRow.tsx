import { useDraggable } from '@dnd-kit/core';
import type { PlanCourse, PlanTerm, TermId, WarningSeverity } from '../../domain/types';
import { formatUnits } from '../../domain/terms';
import { DragHandleIcon, OctagonIcon, TriangleIcon } from '../../components/icons';
import { MoveToMenu } from './MoveToMenu';

export interface CourseRowProps {
  course: PlanCourse;
  termId: TermId;
  locked: boolean;
  highlighted: boolean;
  /** Set when a warning references this course, at all times. */
  warned: WarningSeverity | undefined;
  destinations: PlanTerm[];
  onMove: (toTermId: TermId) => void;
  onRemove: () => void;
}

/**
 * One course in a term.
 *
 * The code leads, because that is what a student scans a plan by; the title
 * sits under it in quieter type so it stays readable in a 240px year column
 * instead of being cut off mid-word.
 */
export function CourseRow({
  course,
  termId,
  locked,
  highlighted,
  warned,
  destinations,
  onMove,
  onRemove,
}: CourseRowProps) {
  const { setNodeRef, listeners, transform, isDragging } = useDraggable({
    id: course.id,
    disabled: locked,
    data: { termId },
  });

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  const warningLabel =
    warned === 'blocking'
      ? 'A blocking warning mentions this course'
      : 'A warning mentions this course';

  return (
    <li
      ref={setNodeRef}
      style={style}
      data-course-key={`${termId}::${course.code}`}
      className={`print-plain group relative rounded-chip py-2 pr-2.5 pl-6 ${
        isDragging ? 'z-20 opacity-90 shadow-raise' : ''
      } ${highlighted ? 'is-highlighted' : 'bg-transparent'} ${
        locked ? '' : 'hover:bg-surface-sunk'
      }`}
    >
      {/* The handle sits in the row's left gutter so the code and the title
          share one left edge, and codes line up across every term. */}
      {locked ? null : (
        <span
          {...listeners}
          tabIndex={-1}
          aria-hidden="true"
          data-drag-handle
          data-print="hide"
          className="absolute top-2.5 left-1 cursor-grab text-line-strong group-hover:text-ink-4 active:cursor-grabbing"
        >
          <DragHandleIcon size={14} />
        </span>
      )}

      <div className="flex items-center gap-2.5">
        <span className="course-code shrink-0 text-small text-ink">{course.code}</span>

        {warned ? (
          <span className={warned === 'blocking' ? 'shrink-0 text-blocking' : 'shrink-0 text-warning'}>
            {warned === 'blocking' ? <OctagonIcon size={13} /> : <TriangleIcon size={13} />}
            <span className="sr-only">{warningLabel}</span>
          </span>
        ) : null}

        <span className="ml-auto flex shrink-0 items-center gap-2">
          {course.grade ? (
            <span className="tnum text-micro font-medium text-ink-3">{course.grade}</span>
          ) : null}
          <span className="tnum text-micro text-ink-4">{formatUnits(course.units)}</span>
          {locked ? null : (
            <span data-print="hide">
              <MoveToMenu
                course={course}
                currentTermId={termId}
                destinations={destinations}
                onMove={onMove}
                onRemove={onRemove}
              />
            </span>
          )}
        </span>
      </div>

      <p className="mt-0.5 truncate text-micro leading-snug text-ink-5" title={course.title}>
        {course.title}
      </p>
    </li>
  );
}
