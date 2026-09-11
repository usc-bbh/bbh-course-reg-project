import { useId, type ReactNode } from 'react';
import { IconButton } from './Button';
import { CloseIcon } from './icons';
import { useFocusTrap } from './useFocusTrap';

export interface DialogProps {
  open: boolean;
  title: string;
  /** Sits under the title. Say exactly what will happen. */
  description?: ReactNode;
  children?: ReactNode;
  footer: ReactNode;
  onClose: () => void;
}

/**
 * A modal dialog that traps focus, closes on Escape, and puts focus back where
 * it came from.
 *
 * Implemented by hand rather than with <dialog showModal>, because the confirm
 * dialogs here are part of the keyboard acceptance criteria and need to behave
 * identically under test.
 */
export function Dialog({ open, title, description, children, footer, onClose }: DialogProps) {
  const panelRef = useFocusTrap(open, onClose);
  const titleId = useId();
  const descriptionId = useId();

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/35 p-0 backdrop-blur-[2px] sm:items-center sm:p-6"
      data-print="hide"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        tabIndex={-1}
        className="anim-rise w-full max-w-lg rounded-t-panel border border-line bg-surface shadow-overlay outline-none sm:rounded-panel"
      >
        <div className="flex items-start justify-between gap-3 border-b border-line-soft px-5 py-4">
          <h2 id={titleId} className="text-[16px] font-semibold text-ink">
            {title}
          </h2>
          <IconButton label="Close" size="sm" onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </div>
        <div className="px-5 py-4">
          {description ? (
            <p id={descriptionId} className="text-[13.5px] leading-relaxed text-ink-2">
              {description}
            </p>
          ) : null}
          {children}
        </div>
        <div className="flex flex-wrap justify-end gap-2 border-t border-line-soft px-5 py-3.5">
          {footer}
        </div>
      </div>
    </div>
  );
}
