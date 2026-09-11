import type { ButtonHTMLAttributes, ReactNode, Ref } from 'react';

type Variant = 'primary' | 'secondary' | 'quiet' | 'danger';
type Size = 'sm' | 'md';

const BASE =
  'inline-flex items-center justify-center gap-2 rounded-control font-medium ' +
  'transition-[background-color,border-color,color,box-shadow] duration-150 ' +
  'disabled:cursor-not-allowed disabled:opacity-55';

const VARIANTS: Record<Variant, string> = {
  // Cardinal is the brand and the primary action. It never means "unsatisfied".
  primary:
    'bg-cardinal text-white border border-cardinal hover:bg-cardinal-deep hover:border-cardinal-deep active:bg-cardinal-deep',
  secondary:
    'bg-surface text-ink border border-line-strong hover:border-ink-5 hover:bg-surface-2 active:bg-surface-sunk',
  quiet:
    'bg-transparent text-ink-3 border border-transparent hover:bg-surface-sunk hover:text-ink active:bg-line-soft',
  danger:
    'bg-surface text-danger border border-danger-line hover:bg-danger-wash active:bg-danger-wash',
};

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-2.5 text-[12.5px]',
  md: 'h-9.5 px-3.5 text-[13.5px]',
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  /** React 19 passes refs to function components as an ordinary prop. */
  ref?: Ref<HTMLButtonElement>;
  children: ReactNode;
}

export function Button({
  variant = 'secondary',
  size = 'md',
  className = '',
  type = 'button',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}

/**
 * An icon-only button. `label` becomes the accessible name — a real label, not
 * a title attribute, because a title is invisible to keyboard and touch users.
 */
export function IconButton({
  label,
  variant = 'quiet',
  size = 'md',
  className = '',
  type = 'button',
  children,
  ...rest
}: Omit<ButtonProps, 'children'> & { label: string; children: ReactNode }) {
  const box = size === 'sm' ? 'h-7 w-7' : 'h-9 w-9';
  return (
    <button
      type={type}
      aria-label={label}
      className={`${BASE} ${VARIANTS[variant]} ${box} rounded-chip p-0 ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
