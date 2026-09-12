/**
 * Bounds for the numbers a student types.
 *
 * These are sanity limits on form input, not degree rules: they stop a typo
 * from putting a course in the year 5 or a term at 4,000 units. Nothing here
 * decides whether a plan is valid — that is the analysis layer's job.
 */
export const YEAR_MIN = 1900;
export const YEAR_MAX = 2200;

/** A single course's units. USC's largest undergraduate courses are 8. */
export const UNITS_MAX = 24;

/** Transfer credit carried in, as one total. */
export const TRANSFER_UNITS_MAX = 200;
