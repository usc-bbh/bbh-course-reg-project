import type { PlanCourse, PlanTerm, TermId } from '../../domain/types';
import { termLabel } from '../../domain/terms';
import { MenuButton, type MenuItem } from '../../components/MenuButton';
import { MoreIcon } from '../../components/icons';

export interface MoveToMenuProps {
  course: PlanCourse;
  currentTermId: TermId;
  /** Planned terms only — locked terms are not destinations. */
  destinations: PlanTerm[];
  onMove: (toTermId: TermId) => void;
  onRemove: () => void;
}

const TRIGGER =
  'inline-flex h-7 w-7 items-center justify-center rounded-chip border border-transparent ' +
  'text-ink-4 transition-colors duration-150 hover:bg-line-soft hover:text-ink';

/**
 * The Move to… menu.
 *
 * This is the supported path for moving a course, not a fallback: it is the
 * only one that works by keyboard, with a screen reader, and on touch. Drag and
 * drop is layered on top of it, and the app is completely usable with dragging
 * turned off.
 */
export function MoveToMenu({
  course,
  currentTermId,
  destinations,
  onMove,
  onRemove,
}: MoveToMenuProps) {
  const targets = destinations.filter((term) => term.id !== currentTermId);
  const items: MenuItem[] = [
    ...targets.map((term) => ({
      key: term.id,
      label: `Move to ${termLabel(term)}`,
      run: () => onMove(term.id),
    })),
    { key: 'remove', label: 'Remove from plan', run: onRemove, danger: true },
  ];

  return (
    <MenuButton
      label={`Move or remove ${course.code}`}
      items={items}
      triggerClassName={TRIGGER}
      {...(targets.length === 0
        ? { emptyMessage: 'There is nowhere else to put this yet. Add a term first.' }
        : {})}
    >
      <MoreIcon />
    </MenuButton>
  );
}
