import type {
  Catalogue,
  CatalogueCourse,
  CatalogueSection,
  FrequencyLabel,
  OfferingFrequency,
  SectionType,
} from '../domain/types';
import catalogueUrl from './catalogue/courses.json?url';

/**
 * The only module in this app allowed to touch the network.
 *
 * `grep -rn "fetch(" src` must find exactly one hit, and it must be in this
 * file. Everything the catalogue serves is public course data — no part of a
 * student's situation or plan is ever sent anywhere, by this module or any
 * other. `scripts/check-privacy.mjs` enforces that on every run.
 *
 * What it fetches is the shape `catalog/README.md` documents for
 * `bbh_schedule_data_v6.json`: `terms_data` keyed by term code, each value an
 * array of course objects, plus a top-level `offering_frequency`. The README
 * says every consumer needs a transform off that shape; `flatten()` below is
 * the planner's, and it is the only thing here that is ours.
 */

// GAP(catalogue): the file this fetches is a hand-made sample, not a scrape.
// catalog/README.md says the v6 scraper "has not yet completed a full
// successful run", the last complete dataset is v5 — "missing courses from ~30
// real departments" — and neither file is committed, because running the scrape
// needs USC VPN. The picker can only offer what the sample contains.
// GAP(catalogue): `offering_frequency` is where "CSCI 401 has only ever run in
// fall terms" has to come from, and in the sample the terms are made up. Note
// that `frequency_label` cannot express seasonality — a fall-only course and a
// course that ran three scattered terms both read "occasionally" — so the fact
// the planner needs lives in `terms_offered`, not in the label.
// GAP(catalogue): catalog/README.md names the four `frequency_label` values but
// not the counts that map to them. The sample's thresholds are ours.
// GAP(catalogue): the scrape covers Spring 2024 to Fall 2026. A four-year plan
// runs past that window by construction, and for a term outside it there is no
// answer at all — which must not be read as "not offered". `scrapedTerms` is
// carried through so a consumer can tell the two apart.

let inflight: Promise<Catalogue> | null = null;

const SECTION_TYPES: SectionType[] = ['lectures', 'labs', 'discussions', 'quizzes', 'other'];
const FREQUENCY_LABELS: FrequencyLabel[] = [
  'every_semester',
  'most_semesters',
  'occasionally',
  'rarely',
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function isSection(value: unknown): value is CatalogueSection {
  if (!isRecord(value)) return false;
  return (
    typeof value.section_id === 'string' &&
    typeof value.section_type === 'string' &&
    SECTION_TYPES.includes(value.section_type as SectionType) &&
    typeof value.mode === 'string' &&
    typeof value.has_d_clearance === 'boolean' &&
    (value.link_code === null || typeof value.link_code === 'string') &&
    (value.notes === null || typeof value.notes === 'string') &&
    typeof value.instructor === 'string' &&
    isStringArray(value.days) &&
    typeof value.start_time === 'string' &&
    typeof value.end_time === 'string' &&
    typeof value.total_seats === 'number' &&
    typeof value.registered_seats === 'number' &&
    typeof value.open_seats === 'number' &&
    typeof value.is_full === 'boolean' &&
    typeof value.is_cancelled === 'boolean'
  );
}

/** Every group present must be a known section type holding real sections. */
function isSectionMap(value: unknown): value is CatalogueCourse['sections'] {
  if (!isRecord(value)) return false;
  return Object.entries(value).every(
    ([kind, group]) =>
      SECTION_TYPES.includes(kind as SectionType) &&
      Array.isArray(group) &&
      group.every(isSection),
  );
}

function isCountMap(value: unknown): value is CatalogueCourse['section_counts'] {
  if (!isRecord(value)) return false;
  return Object.entries(value).every(
    ([kind, count]) => SECTION_TYPES.includes(kind as SectionType) && typeof count === 'number',
  );
}

/** Every field catalog/README.md lists on the course object, all ten of them. */
function isCourse(value: unknown): value is CatalogueCourse {
  if (!isRecord(value)) return false;
  return (
    typeof value.course_name === 'string' &&
    typeof value.units === 'number' &&
    typeof value.description === 'string' &&
    typeof value.term_code === 'string' &&
    typeof value.has_lab === 'boolean' &&
    typeof value.has_discussion === 'boolean' &&
    typeof value.has_d_clearance === 'boolean' &&
    typeof value.has_restrictions === 'boolean' &&
    isCountMap(value.section_counts) &&
    isSectionMap(value.sections)
  );
}

function isOfferingMap(value: unknown): value is Record<string, OfferingFrequency> {
  if (!isRecord(value)) return false;
  return Object.values(value).every((entry) => {
    if (!isRecord(entry)) return false;
    return (
      isStringArray(entry.terms_offered) &&
      typeof entry.count === 'number' &&
      typeof entry.frequency_label === 'string' &&
      FREQUENCY_LABELS.includes(entry.frequency_label as FrequencyLabel)
    );
  });
}

/**
 * The transform every consumer of this data needs, per catalog/README.md: the
 * term-nested arrays become one entry per course. Newest scraped term wins,
 * because that is the entry whose sections and flags are current.
 */
function flatten(termsData: Record<string, CatalogueCourse[]>, newestFirst: string[]): CatalogueCourse[] {
  const byName = new Map<string, CatalogueCourse>();
  for (const term of newestFirst) {
    for (const course of termsData[term] ?? []) {
      if (!byName.has(course.course_name)) byName.set(course.course_name, course);
    }
  }
  return [...byName.values()].sort((a, b) => a.course_name.localeCompare(b.course_name));
}

export function toCatalogue(raw: unknown): Catalogue {
  if (!isRecord(raw)) throw new Error('Catalogue data is not an object.');
  if (!isRecord(raw.terms) || !Object.values(raw.terms).every((label) => typeof label === 'string')) {
    throw new Error('Catalogue data does not say which terms it covers.');
  }
  if (!isRecord(raw.terms_data)) {
    throw new Error('Catalogue data has no usable course list.');
  }
  const termsData: Record<string, CatalogueCourse[]> = {};
  for (const [term, courses] of Object.entries(raw.terms_data)) {
    if (!Array.isArray(courses) || !courses.every(isCourse)) {
      throw new Error(`Catalogue data for term ${term} is not a list of courses.`);
    }
    termsData[term] = courses;
  }
  if (!isOfferingMap(raw.offering_frequency)) {
    throw new Error('Catalogue data has no usable offering frequencies.');
  }

  // USC term codes sort chronologically as strings: 20263 > 20261 > 20253.
  const scrapedTerms = Object.keys(raw.terms).sort().reverse();

  return {
    sourceLabel: typeof raw.schema_version === 'string'
      ? `Sample in catalog/README.md v${raw.schema_version} shape`
      : 'Sample course data',
    courses: flatten(termsData, scrapedTerms),
    offering_frequency: raw.offering_frequency,
    scrapedTerms,
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
