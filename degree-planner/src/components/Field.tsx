import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from 'react';

const CONTROL =
  'w-full rounded-field border border-line-strong bg-surface px-3 py-2 text-[13.5px] text-ink ' +
  'transition-[border-color,box-shadow] duration-150 placeholder:text-ink-5 ' +
  'hover:border-ink-5 disabled:bg-surface-sunk disabled:text-ink-4';

export function Field({
  label,
  hint,
  children,
  className = '',
}: {
  label: string;
  hint?: string;
  children: (props: { id: string; describedBy: string | undefined }) => ReactNode;
  className?: string;
}) {
  const id = useId();
  const hintId = `${id}-hint`;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block text-[12.5px] font-medium text-ink-2">
        {label}
      </label>
      {children({ id, describedBy: hint ? hintId : undefined })}
      {hint ? (
        <p id={hintId} className="mt-1 text-[12px] text-ink-4">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function TextInput({ className = '', ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${CONTROL} ${className}`} {...rest} />;
}

export function Select({ className = '', ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`${CONTROL} ${className}`} {...rest} />;
}
