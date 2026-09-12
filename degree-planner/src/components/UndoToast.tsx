import { useEffect, useRef } from 'react';
import { Button, IconButton } from './Button';
import { CloseIcon, UndoIcon } from './icons';

export interface UndoToastProps {
  /** What was removed, named in the message. */
  courseCode: string;
  termName: string;
  onUndo: () => void;
  onDismiss: () => void;
}

/**
 * The undo after a removal.
 *
 * Focus moves to the Undo button as soon as the toast appears, because an undo
 * a mouse can reach and a keyboard cannot is not an undo. Dismissing it puts
 * focus back on the term's "Add course" button, which is where the removed row
 * used to be.
 */
export function UndoToast({ courseCode, termName, onUndo, onDismiss }: UndoToastProps) {
  const undoRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    undoRef.current?.focus();
  }, []);

  return (
    <div
      role="status"
      data-print="hide"
      className="anim-rise fixed inset-x-3 bottom-20 z-40 mx-auto flex max-w-md items-center gap-3 rounded-card border border-line bg-ink px-3 py-2.5 text-surface shadow-overlay sm:inset-x-auto sm:left-1/2 sm:w-md sm:-translate-x-1/2 xl:bottom-5"
    >
      <p className="min-w-0 flex-1 text-small">
        Removed <span className="course-code">{courseCode}</span> from {termName}.
      </p>
      <Button
        ref={undoRef}
        size="sm"
        className="border-transparent bg-surface text-ink hover:bg-surface-2"
        onClick={onUndo}
      >
        <UndoIcon size={14} />
        Undo
      </Button>
      <IconButton
        label="Dismiss"
        size="sm"
        className="text-line-strong hover:bg-ink-2 hover:text-surface"
        onClick={onDismiss}
      >
        <CloseIcon size={14} />
      </IconButton>
    </div>
  );
}
