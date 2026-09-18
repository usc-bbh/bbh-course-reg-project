import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

export interface MenuItem {
  key: string;
  label: string;
  run: () => void;
  /** Destructive items sit below a rule and carry the danger colour. */
  danger?: boolean;
}

export interface MenuButtonProps {
  /** The accessible name of the trigger. */
  label: string;
  /** What the trigger shows. */
  children: ReactNode;
  items: MenuItem[];
  /** Shown in place of the list when there is nothing to offer. */
  emptyMessage?: string;
  triggerClassName: string;
  align?: 'left' | 'right';
}

/**
 * One menu implementation, used by the Move to… menu on a course and by the
 * plan's secondary actions.
 *
 * Arrow keys move between items, Home and End jump to the ends, Escape closes
 * and returns focus to the trigger, and Tab leaves without stealing focus back.
 */
export function MenuButton({
  label,
  children,
  items,
  emptyMessage,
  triggerClassName,
  align = 'right',
}: MenuButtonProps) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const menuId = useId();

  const close = (restoreFocus = true) => {
    setOpen(false);
    if (restoreFocus) triggerRef.current?.focus();
  };

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      const menu = menuRef.current;
      if (menu && !menu.contains(event.target as Node) && event.target !== triggerRef.current) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const entries = menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]');
    if (!entries || entries.length === 0) return;
    const target = entries[Math.min(activeIndex, entries.length - 1)];
    target?.focus();
  }, [open, activeIndex]);

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        className={triggerClassName}
        onClick={() => {
          setActiveIndex(0);
          setOpen((value) => !value);
        }}
      >
        {children}
      </button>

      {open ? (
        <div
          ref={menuRef}
          id={menuId}
          role="menu"
          aria-label={label}
          className={`anim-expand absolute top-full z-30 mt-1 min-w-56 rounded-card border border-line-strong bg-surface py-1 shadow-overlay ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.preventDefault();
              event.stopPropagation();
              close();
            } else if (event.key === 'ArrowDown') {
              event.preventDefault();
              setActiveIndex((index) => (index + 1) % items.length);
            } else if (event.key === 'ArrowUp') {
              event.preventDefault();
              setActiveIndex((index) => (index - 1 + items.length) % items.length);
            } else if (event.key === 'Home') {
              event.preventDefault();
              setActiveIndex(0);
            } else if (event.key === 'End') {
              event.preventDefault();
              setActiveIndex(items.length - 1);
            } else if (event.key === 'Tab') {
              close(false);
            }
          }}
        >
          {emptyMessage ? <p className="px-4 py-2.5 text-small text-ink-4">{emptyMessage}</p> : null}
          {items.map((item) => (
            <button
              key={item.key}
              type="button"
              role="menuitem"
              tabIndex={-1}
              className={`block w-full px-4 py-2.5 text-left text-body hover:bg-surface-sunk ${
                item.danger ? 'border-t border-line-soft text-danger' : 'text-ink'
              }`}
              onClick={() => {
                close();
                item.run();
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
