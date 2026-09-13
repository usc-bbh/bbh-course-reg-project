import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * Colour contrast, checked against the tokens themselves.
 *
 * The Playwright suite runs axe over real pages, which is the authority — but
 * it needs a browser and a build. This reads `@theme` and does the arithmetic,
 * so a colour tweak fails in milliseconds, at the line that caused it, before
 * anyone waits for a browser.
 *
 * WCAG 2.1 AA: 4.5:1 for normal text. Every size in this app's type scale is
 * below the 18.66px-bold / 24px threshold that would allow 3:1, so 4.5 applies
 * to all of it.
 */
const CSS = readFileSync(resolve(process.cwd(), 'src/styles/index.css'), 'utf8');

function token(name: string): string {
  const match = new RegExp(`--color-${name}:\\s*(#[0-9a-fA-F]{6});`).exec(CSS);
  if (!match?.[1]) throw new Error(`--color-${name} is not defined in index.css`);
  return match[1];
}

function channel(value: number): number {
  const c = value / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const n = Number.parseInt(hex.slice(1), 16);
  return (
    0.2126 * channel((n >> 16) & 0xff) +
    0.7152 * channel((n >> 8) & 0xff) +
    0.0722 * channel(n & 0xff)
  );
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

/** Every surface a foreground token can land on. */
const BACKGROUNDS = [
  'canvas',
  'surface',
  'surface-2',
  'surface-sunk',
  'gold-wash',
  'warning-wash',
  'satisfied-wash',
  'inprogress-wash',
  'unsatisfied-wash',
  'blocking-wash',
  'danger-wash',
];

/** Every token used as text or as an icon on one of those surfaces. */
const FOREGROUNDS = [
  'ink',
  'ink-2',
  'ink-3',
  'ink-4',
  'ink-5',
  'cardinal',
  'cardinal-deep',
  'satisfied',
  'inprogress',
  'unsatisfied',
  'warning',
  'blocking',
  'danger',
];

const AA = 4.5;

describe('colour contrast', () => {
  it('sanity-checks its own arithmetic against known values', () => {
    expect(contrast('#000000', '#ffffff')).toBeCloseTo(21, 5);
    expect(contrast('#ffffff', '#ffffff')).toBeCloseTo(1, 5);
    // The canonical WCAG worked example: #767676 on white is exactly AA.
    expect(contrast('#767676', '#ffffff')).toBeGreaterThanOrEqual(AA);
    expect(contrast('#777777', '#ffffff')).toBeLessThan(AA);
  });

  it('clears AA for every text colour on every surface it can sit on', () => {
    const failures: string[] = [];
    for (const fg of FOREGROUNDS) {
      for (const bg of BACKGROUNDS) {
        const ratio = contrast(token(fg), token(bg));
        if (ratio < AA) {
          failures.push(`${fg} (${token(fg)}) on ${bg} (${token(bg)}) is ${ratio.toFixed(2)}:1`);
        }
      }
    }
    expect(failures, failures.join('\n')).toEqual([]);
  });

  it('keeps the ink scale visibly stepped, not just legal', () => {
    // Compressing the scale to pass AA is easy; compressing it until ink-4 and
    // ink-5 are the same grey is how you lose the hierarchy the design needs.
    const scale = ['ink', 'ink-2', 'ink-3', 'ink-4', 'ink-5'].map(token);
    for (let i = 1; i < scale.length; i += 1) {
      const lighter = luminance(scale[i] as string);
      const darker = luminance(scale[i - 1] as string);
      expect(lighter, `${scale[i]} is not lighter than ${scale[i - 1]}`).toBeGreaterThan(darker);
    }
  });
});
