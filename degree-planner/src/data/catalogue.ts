import type { Catalogue, CatalogueCourse } from '../domain/types';
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

// GAP(catalogue): there is no source yet for course titles and unit counts, so
// src/data/catalogue/courses.json is a hand-made sample of about forty USC
// courses. The picker cannot offer anything outside it.
// GAP(catalogue): the picker has no way to know which terms a course is offered
// in. The analysis layer already warns about a course placed in a term it is
// not offered, so the two need to agree on where that fact comes from.
// GAP(catalogue): the review form needs the list of majors, minors and
// catalogue years a student can choose from. Those three lists are invented
// here and should come from the same place the requirements do.

let inflight: Promise<Catalogue> | null = null;

function isCourse(value: unknown): value is CatalogueCourse {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.code === 'string' &&
    typeof candidate.title === 'string' &&
    typeof candidate.units === 'number'
  );
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
    !isStringArray(candidate.majors) ||
    !isStringArray(candidate.minors) ||
    !isStringArray(candidate.catalogueYears)
  ) {
    throw new Error('Catalogue data is missing its majors, minors or catalogue years.');
  }
  return {
    sourceLabel:
      typeof candidate.sourceLabel === 'string' ? candidate.sourceLabel : 'Sample course data',
    courses: [...candidate.courses].sort((a, b) => a.code.localeCompare(b.code)),
    majors: candidate.majors,
    minors: candidate.minors,
    catalogueYears: candidate.catalogueYears,
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

/** Filters on code and title. Display filtering, not eligibility. */
export function searchCourses(courses: CatalogueCourse[], query: string): CatalogueCourse[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return courses;
  return courses.filter(
    (course) =>
      course.code.toLowerCase().includes(needle) || course.title.toLowerCase().includes(needle),
  );
}
