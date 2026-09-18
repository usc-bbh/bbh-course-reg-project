import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { courseTitle, searchCourses, toCatalogue } from '../src/data/catalogue';
import type { CatalogueCourse } from '../src/domain/types';

/**
 * The sample course file against the schema it claims to follow.
 *
 * An earlier version of this file carried five of the ten fields
 * `catalog/README.md` documents and `"term_code": null` on every course, and
 * nothing caught it, because the guard only checked the five fields the UI
 * happened to read. These tests check the file against the contract rather than
 * against what the UI needs, so the day Agastya's real scrape drops in, the
 * failure is here and not in the picker.
 */
const RAW: unknown = JSON.parse(
  readFileSync(resolve(process.cwd(), 'src/data/catalogue/courses.json'), 'utf8'),
);

const scrape = RAW as {
  schema_version: string;
  terms: Record<string, string>;
  terms_data: Record<string, CatalogueCourse[]>;
  offering_frequency: Record<string, { terms_offered: string[]; count: number }>;
};

const COURSE_FIELDS = [
  'course_name',
  'units',
  'description',
  'term_code',
  'has_lab',
  'has_discussion',
  'has_d_clearance',
  'has_restrictions',
  'section_counts',
  'sections',
];

describe('the sample course file', () => {
  it('is the top-level shape catalog/README.md documents for v6', () => {
    expect(scrape.schema_version).toBe('6.0');
    expect(Object.keys(scrape.terms).length).toBeGreaterThan(0);
    // terms_data is keyed by term code, and each value is an array, not a dict.
    for (const [term, courses] of Object.entries(scrape.terms_data)) {
      expect(scrape.terms, `${term} is not in the terms map`).toHaveProperty(term);
      expect(Array.isArray(courses)).toBe(true);
    }
  });

  it('carries every field the course object documents, on every course', () => {
    for (const [term, courses] of Object.entries(scrape.terms_data)) {
      for (const course of courses) {
        expect(Object.keys(course).sort(), `${course.course_name} in ${term}`).toEqual(
          [...COURSE_FIELDS].sort(),
        );
        // "Matches the parent key in terms_data" — the README's own words.
        expect(course.term_code, `${course.course_name} in ${term}`).toBe(term);
      }
    }
  });

  it('names every course in the DEPT NNN form the whole repo agrees on', () => {
    for (const courses of Object.values(scrape.terms_data)) {
      for (const course of courses) {
        expect(course.course_name).toMatch(/^[A-Z]+ \d+[A-Za-z]*$/);
      }
    }
  });

  it('keeps section_counts and sections telling the same story', () => {
    for (const courses of Object.values(scrape.terms_data)) {
      for (const course of courses) {
        for (const [kind, group] of Object.entries(course.sections)) {
          expect(course.section_counts[kind as 'lectures']).toBe(group?.length);
        }
        // "Only non-empty groups are present."
        expect(Object.values(course.sections).every((group) => (group?.length ?? 0) > 0)).toBe(true);
        expect(course.has_lab).toBe('labs' in course.sections);
        expect(course.has_discussion).toBe('discussions' in course.sections);
      }
    }
  });

  it('has offering_frequency agree with the terms the course actually appears in', () => {
    // This is the invariant a real scrape has for free, because the frequency
    // object is derived from the same pass. The planner's only blocking warning
    // rests on terms_offered, so a sample that disagreed with itself would be
    // demonstrating a bug rather than a feature.
    const seen = new Map<string, string[]>();
    for (const [term, courses] of Object.entries(scrape.terms_data)) {
      for (const course of courses) {
        seen.set(course.course_name, [...(seen.get(course.course_name) ?? []), term]);
      }
    }
    for (const [name, terms] of seen) {
      const entry = scrape.offering_frequency[name];
      expect(entry, `${name} has no offering_frequency entry`).toBeDefined();
      expect([...(entry?.terms_offered ?? [])].sort()).toEqual([...terms].sort());
      expect(entry?.count).toBe(terms.length);
    }
    for (const name of Object.keys(scrape.offering_frequency)) {
      expect(seen.has(name), `${name} has a frequency but appears in no term`).toBe(true);
    }
  });
});

/**
 * Built inside each test rather than in the describe body: a describe body that
 * throws takes the whole file down as a collection error, and "no tests ran" is
 * a much worse signal than a named assertion failure.
 */
function built() {
  return toCatalogue(RAW);
}

describe('the transform the planner applies', () => {

  it('flattens the term-nested arrays to one entry per course', () => {
    const catalogue = built();
    const names = catalogue.courses.map((course) => course.course_name);
    expect(new Set(names).size).toBe(names.length);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
  });

  it('keeps the newest scraped term’s entry for each course', () => {
    const catalogue = built();
    // USC term codes sort chronologically as strings, so the newest is last.
    expect(catalogue.scrapedTerms[0]).toBe(
      [...Object.keys(scrape.terms)].sort().reverse()[0],
    );
    for (const course of catalogue.courses) {
      const offered = scrape.offering_frequency[course.course_name]?.terms_offered ?? [];
      expect(course.term_code).toBe([...offered].sort().reverse()[0]);
    }
  });

  it('carries the scraped window through, so “no data” is not “not offered”', () => {
    const catalogue = built();
    expect(catalogue.scrapedTerms.length).toBeGreaterThan(0);
    // The sample student's plan runs to Spring 2027 (20271), past the window.
    expect(catalogue.scrapedTerms).not.toContain('20271');
  });

  it('rejects a course that is missing a documented field', () => {
    const broken = structuredClone(scrape) as unknown as typeof scrape;
    const first = Object.keys(broken.terms_data)[0] ?? '';
    const course = broken.terms_data[first]?.[0];
    if (course) delete (course as Partial<CatalogueCourse>).term_code;
    expect(() => toCatalogue(broken)).toThrow(/not a list of courses/);
  });

  it('rejects a frequency label outside the documented four', () => {
    const broken = structuredClone(scrape) as unknown as typeof scrape;
    const first = Object.keys(broken.offering_frequency)[0] ?? '';
    const entry = broken.offering_frequency[first];
    if (entry) (entry as { frequency_label?: string }).frequency_label = 'sometimes';
    expect(() => toCatalogue(broken)).toThrow(/offering frequencies/);
  });
});

describe('what the picker shows', () => {

  it('matches on code and on description', () => {
    const catalogue = built();
    expect(searchCourses(catalogue.courses, 'CSCI 485')).toHaveLength(1);
    expect(searchCourses(catalogue.courses, 'capstone').length).toBeGreaterThan(0);
    expect(searchCourses(catalogue.courses, 'zzzz')).toHaveLength(0);
  });

  it('falls back to the code when a description has no first sentence', () => {
    const catalogue = built();
    const course = catalogue.courses[0];
    expect(course).toBeDefined();
    if (!course) return;
    expect(courseTitle({ ...course, description: '' })).toBe(course.course_name);
  });
});
