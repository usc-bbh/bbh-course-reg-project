import type { Catalogue, CatalogueCourse, OfferingFrequency } from '../domain/types';
import catalogueUrl from './catalogue/courses.json?url';

/**
 * The only module in this app allowed to touch the network.
 *
 * `grep -rn "fetch(" src` must find exactly one hit, and it must be in this
 * file. Everything the catalogue serves is public course data — no part of a
 * student's situation or plan is ever sent anywhere, by this module or any
 * other. `scripts/check-privacy.mjs` enforces that on every run.
 *
 * Today the "network request" is a same-origin GET for a static JSON file
 * shipped with the build. It is written as a real request on purpose: when
 * catalogue data outgrows a bundled file, the URL changes here and nothing
 * else does — and the UI has already been built against the pending and failed
 * states a real request has.
 */

// GAP(catalogue): catalog/README.md says the v6 scrape "has not yet completed a
// full successful run" and that the last complete dataset is v5, which is
// "missing courses from ~30 real departments". Neither file is committed, and
// the scrape needs USC VPN. So src/data/catalogue/courses.json is a hand-made
// sample in the documented v6 shape — the picker cannot offer anything outside
// it, and swapping in the real data is a URL change here.
// GAP(catalogue): the sample carries `offering_frequency` because that is where
// "CSCI 401 only runs in the fall" has to come from — but with no real scrape
// the terms_offered lists below are made up. The analysis layer warns on
// offering terms today, so it and this module need the same source.
// GAP(catalogue): degrees, majors, minors and catalogue years are invented
// here. catalogue_scraper/ has 470 real programme files for 2026-2027 only,
// and a student on an older catalogue year has no list to pick from.

let inflight: Promise<Catalogue> | null = null;

function isCourse(value: unknown): value is CatalogueCourse {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.course_name === 'string' &&
    typeof candidate.units === 'number' &&
    typeof candidate.description === 'string' &&
    typeof candidate.has_d_clearance === 'boolean' &&
    typeof candidate.has_restrictions === 'boolean'
  );
}

function isOfferingMap(value: unknown): value is Record<string, OfferingFrequency> {
  if (typeof value !== 'object' || value === null) return false;
  return Object.values(value as Record<string, unknown>).every((entry) => {
    if (typeof entry !== 'object' || entry === null) return false;
    const candidate = entry as Record<string, unknown>;
    return (
      Array.isArray(candidate.terms_offered) &&
      typeof candidate.count === 'number' &&
      typeof candidate.frequency_label === 'string'
    );
  });
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function toCatalogue(raw: unknown): Catalogue {
  if (typeof raw !== 'object' || raw === null) {
    throw new Error('Catalogue data is not an object.');
  }
  const candidate = raw as Record<string, unknown>;
  if (!Array.isArray(candidate.courses) || !candidate.courses.every(isCourse)) {
    throw new Error('Catalogue data has no usable course list.');
  }
  if (
    !isStringArray(candidate.degrees) ||
    !isStringArray(candidate.majors) ||
    !isStringArray(candidate.minors) ||
    !isStringArray(candidate.catalogYears)
  ) {
    throw new Error('Catalogue data is missing its degrees, majors, minors or catalogue years.');
  }
  if (!isOfferingMap(candidate.offering_frequency)) {
    throw new Error('Catalogue data has no usable offering frequencies.');
  }
  return {
    sourceLabel:
      typeof candidate.sourceLabel === 'string' ? candidate.sourceLabel : 'Sample course data',
    courses: [...candidate.courses].sort((a, b) => a.course_name.localeCompare(b.course_name)),
    offering_frequency: candidate.offering_frequency,
    degrees: candidate.degrees,
    majors: candidate.majors,
    minors: candidate.minors,
    catalogYears: candidate.catalogYears,
  };
}

/** Loads the public catalogue sample. Cached for the life of the page. */
export function loadCatalogue(): Promise<Catalogue> {
  if (!inflight) {
    inflight = fetch(catalogueUrl, { credentials: 'omit', cache: 'force-cache' })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Course list request failed (${response.status}).`);
        }
        return response.json();
      })
      .then(toCatalogue)
      .catch((error: unknown) => {
        // Let the next attempt retry rather than caching the failure.
        inflight = null;
        throw error instanceof Error ? error : new Error('Course list could not be loaded.');
      });
  }
  return inflight;
}

/** Test seam: drops the cached response so each test starts clean. */
export function resetCatalogueCache(): void {
  inflight = null;
}

/** Filters on code and description. Display filtering, not eligibility. */
export function searchCourses(courses: CatalogueCourse[], query: string): CatalogueCourse[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return courses;
  return courses.filter(
    (course) =>
      course.course_name.toLowerCase().includes(needle) ||
      course.description.toLowerCase().includes(needle),
  );
}

/**
 * The catalogue object has no course title field — `catalog/README.md` gives a
 * `description`, not a title. We show its first sentence, which is what the
 * scrape's description opens with.
 */
export function courseTitle(course: CatalogueCourse): string {
  const firstSentence = course.description.split('.')[0] ?? '';
  return firstSentence.trim() || course.course_name;
}
