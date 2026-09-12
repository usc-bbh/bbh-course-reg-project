import { useState, type InputHTMLAttributes } from 'react';

type PassThrough = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'value' | 'onChange' | 'onBlur' | 'type'
>;

export interface NumberInputProps extends PassThrough {
  value: number;
  onCommit: (value: number) => void;
  /** Values outside the range are not committed; the field keeps the text. */
  min?: number;
  max?: number;
  /** Whole numbers only — used for years. */
  integer?: boolean;
}

/**
 * A number field that lets a person type.
 *
 * A naive `Number(event.target.value)` field is unusable: clearing it commits
 * 0 (so an entry year silently becomes year 0), and typing "4." commits 4 and
 * rewrites the field, so "4.5" can never be reached.
 *
 * This keeps what was typed as-is while the field has focus, commits only
 * values that parse and fall inside the range, and falls back to the committed
 * value on blur — so a half-typed or nonsense entry can never end up in the
 * student's situation.
 */
export function NumberInput({
  value,
  onCommit,
  min,
  max,
  integer = false,
  className = '',
  ...rest
}: NumberInputProps) {
  const [draft, setDraft] = useState<string | null>(null);

  const shown = draft ?? String(value);

  return (
    <input
      type="text"
      inputMode={integer ? 'numeric' : 'decimal'}
      value={shown}
      className={className}
      onChange={(event) => {
        const text = event.target.value;
        setDraft(text);

        if (text.trim() === '') return;
        const parsed = Number(text);
        if (!Number.isFinite(parsed)) return;
        if (integer && !Number.isInteger(parsed)) return;
        if (min !== undefined && parsed < min) return;
        if (max !== undefined && parsed > max) return;
        onCommit(parsed);
      }}
      onBlur={() => setDraft(null)}
      {...rest}
    />
  );
}
