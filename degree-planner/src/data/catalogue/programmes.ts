/**
 * The degree, major, minor and catalogue-year lists the review form offers.
 *
 * These are NOT scrape data, so they do not ride along in the fetched course
 * file and do not disappear when that request fails. They are bundled, which is
 * also the honest thing: nothing produced them but this file.
 */

// GAP(catalogue): invented. `catalogue_scraper/` holds 470 real programme files
// but for 2026-2027 only, so a student on the fixture's own 2023-2024 catalogue
// year has no list to pick from. Both fields stay editable for that reason: the
// review form falls back to the student's own value when it is not in the list.
export const PROGRAMMES = {
  majors: [
    'Computer Science',
    'Computer Science (Games)',
    'Computer Engineering and Computer Science',
    'Electrical Engineering',
    'Applied and Computational Mathematics',
    'Business Administration',
    'Economics',
    'Cognitive Science',
  ],
  minors: [
    'Mathematics',
    'Applied Analytics',
    'Computer Programming',
    'Economics',
    'Music Industry',
    'Occupational Science',
    'Sociology',
    'Technology Commercialization',
  ],
  catalogYears: ['2022-2023', '2023-2024', '2024-2025', '2025-2026', '2026-2027'],
} as const;
