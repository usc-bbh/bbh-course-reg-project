import type { Season, TermId } from './types';

/**
 * USC term codes.
 *
 * Every other module in this repo speaks five-digit USC term codes: the STARS
 * parser emits them on each course row (`"20243"`), `catalog/` keys its scrape
 * by them, and `docs/parser-brief.md` §6 pins the format —
 *
 *     YYYY + one digit, where 1 = spring, 2 = summer, 3 = fall.
 *     So 20243 is fall 2024 and 20251 is spring 2025.
 *
 * The planner keeps readable ids internally (`fall-2024`) because they show up
 * in exported files and in test failures, and converts at the data seam. This
 * file is that seam: it is the only place the two vocabularies meet.
 *
 * Converting a code to a season and a year is string parsing, not degree
 * logic. Nothing here decides whether a term is in the past.
 */

const SEASON_BY_DIGIT: Record<string, Season> = {
  '1': 'spring',
  '2': 'summer',
  '3': 'fall',
};

const DIGIT_BY_SEASON: Record<Season, string> = {
  spring: '1',
  summer: '2',
  fall: '3',
};

/** `"20243"` → `"fall-2024"`. Returns null for anything that is not a code. */
export function termIdFromUscCode(code: string): TermId | null {
  const parsed = parseUscTermCode(code);
  return parsed ? `${parsed.season}-${parsed.year}` : null;
}

export function parseUscTermCode(code: string): { season: Season; year: number } | null {
  if (!/^\d{5}$/.test(code)) return null;
  const year = Number(code.slice(0, 4));
  const season = SEASON_BY_DIGIT[code.slice(4)];
  if (!season || !Number.isFinite(year)) return null;
  return { season, year };
}

/** `"fall-2024"` → `"20243"`, for anything handed back to another module. */
export function uscCodeFromTermId(termId: TermId): string | null {
  const [season, rawYear] = termId.split('-');
  const digit = season ? DIGIT_BY_SEASON[season as Season] : undefined;
  if (!digit || !rawYear || !/^\d{4}$/.test(rawYear)) return null;
  return `${rawYear}${digit}`;
}

/**
 * Course codes.
 *
 * `catalog/README.md` and `validator/README.md` both normalise to
 * `"DEPT NNN"` with a single space, and the validator says so explicitly:
 * "Course codes are normalized to `DEPT ###` (single space) everywhere in this
 * module." The STARS parser's README shows `"BUAD304"` with no space while its
 * own committed fixture shows `"CSCI 103"` with one — see the gap log in
 * parseStarsReport.ts. We normalise on the way in so the planner matches the
 * two modules that have agreed with each other.
 */
export function normalizeCourseCode(raw: string): string {
  const trimmed = raw.trim().toUpperCase().replace(/\s+/g, ' ');
  if (trimmed.includes(' ')) return trimmed;
  // "BUAD304L" → "BUAD 304L"; leaves transfer placeholders like "TR-PSYC" alone.
  const split = /^([A-Z]{2,5})(\d.*)$/.exec(trimmed);
  return split ? `${split[1]} ${split[2]}` : trimmed;
}

/**
 * Generic transfer credit appears as a placeholder row, not a course:
 * `TR-PSYC`, `TR-COMP-1`, `TR-NUTRITION` (docs/parser-brief.md §7). It carries
 * units but names no USC course.
 */
export function isTransferPlaceholder(code: string): boolean {
  return /^TR-/i.test(code.trim());
}
