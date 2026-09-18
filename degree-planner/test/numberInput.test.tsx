import { describe, expect, it, vi } from 'vitest';
import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NumberInput } from '../src/components/NumberInput';

function Harness({
  initial,
  onCommit,
  ...rest
}: {
  initial: number;
  onCommit: (value: number) => void;
  integer?: boolean;
  min?: number;
  max?: number;
}) {
  const [value, setValue] = useState(initial);
  return (
    <NumberInput
      aria-label="Amount"
      value={value}
      onCommit={(next) => {
        setValue(next);
        onCommit(next);
      }}
      {...rest}
    />
  );
}

describe('NumberInput', () => {
  it('lets a decimal be typed one character at a time', async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<Harness initial={4} onCommit={onCommit} min={0} max={24} />);

    const field = screen.getByLabelText('Amount');
    await user.clear(field);
    await user.type(field, '4.5');

    // The field kept "4." mid-way instead of rewriting it back to "4".
    expect(field).toHaveValue('4.5');
    expect(onCommit).toHaveBeenLastCalledWith(4.5);
  });

  it('does not commit anything when the field is emptied', async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<Harness initial={2026} onCommit={onCommit} integer min={1900} max={2200} />);

    const field = screen.getByLabelText('Amount');
    await user.clear(field);

    expect(field).toHaveValue('');
    expect(onCommit).not.toHaveBeenCalled();
  });

  it('restores the committed value on blur after a half-typed entry', async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<Harness initial={2026} onCommit={onCommit} integer min={1900} max={2200} />);

    const field = screen.getByLabelText('Amount');
    await user.clear(field);
    await user.type(field, '20');
    await user.tab();

    // 20 is outside the range, so it was never committed and the field snaps
    // back to the value that is actually stored.
    expect(field).toHaveValue('2026');
    expect(onCommit).not.toHaveBeenCalled();
  });

  it('refuses a fractional value on an integer field', async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<Harness initial={2026} onCommit={onCommit} integer min={1900} max={2200} />);

    const field = screen.getByLabelText('Amount');
    await user.clear(field);
    await user.type(field, '2026.5');

    expect(onCommit).toHaveBeenLastCalledWith(2026);
  });
});
