const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/**
 * `2025-02-14` → `14 February 2025`, the way a STARS report writes a date
 * (`"expectedGraduation": "16 May 2027"`).
 *
 * Parsed by hand rather than through `Date`, so the answer does not depend on
 * the reader's time zone or locale, and today's date is never consulted. Text
 * that is not an ISO date is passed through untouched — the parser does not
 * emit this field yet, so whatever arrives is shown as it arrived.
 */
export function formatReportDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
  if (!match) return value;
  const [, year, month, day] = match;
  const name = MONTHS[Number(month) - 1];
  if (!name) return value;
  return `${Number(day)} ${name} ${year}`;
}
