import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { CatalogueCourse, PlanTerm, TermId } from '../../domain/types';
import { formatUnits, termLabel } from '../../domain/terms';
import { searchCourses } from '../../data/catalogue';
import { useCatalogue } from '../../data/useCatalogue';
import { Button } from '../../components/Button';
import { SearchIcon } from '../../components/icons';

const MAX_OPTIONS = 40;

export interface CoursePickerProps {
  termId: TermId;
  termName: string;
  /** Every term, so the picker can say where a course already sits. */
  allTerms: PlanTerm[];
  onAdd: (course: CatalogueCourse) => void;
  onClose: () => void;
}

/**
 * A combobox over the sample course list.
 *
 * Keyboard is the primary path: arrow keys move the active option, Enter adds
 * it, Escape closes and puts focus back on the trigger. `aria-activedescendant`
 * keeps focus in the text field the whole time, which is what screen readers
 * expect from this pattern.
 */
export function CoursePicker({ termId, termName, allTerms, onAdd, onClose }: CoursePickerProps) {
  const { state, retry } = useCatalogue();
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const baseId = useId();
  const listboxId = `${baseId}-listbox`;

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const catalogue = state.status === 'ready' ? state.catalogue : null;

  const options = useMemo(() => {
    if (!catalogue) return [];
    return searchCourses(catalogue.courses, query).slice(0, MAX_OPTIONS);
  }, [catalogue, query]);

  useEffect(() => {
    const list = listRef.current;
    const active = list?.querySelector<HTMLElement>('[data-active="true"]');
    active?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex, options.length]);

  // "Already in Fall 2027" — a statement of fact, with no judgement attached.
  const placements = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const term of allTerms) {
      for (const course of term.courses) {
        const list = map.get(course.code);
        const label = termLabel(term);
        if (list) list.push(label);
        else map.set(course.code, [label]);
      }
    }
    return map;
  }, [allTerms]);

  const commit = (course: CatalogueCourse | undefined) => {
    if (!course) return;
    onAdd(course);
    setQuery('');
    setActiveIndex(0);
    inputRef.current?.focus();
  };

  return (
    <div className="anim-expand rounded-card border border-line-strong bg-surface p-2.5 shadow-raise">
      <div className="flex items-center gap-2 rounded-field border border-line-strong bg-surface px-2.5 focus-within:border-cardinal">
        <SearchIcon className="shrink-0 text-ink-4" />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={options.length > 0}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={
            options.length > 0 ? `${listboxId}-option-${activeIndex}` : undefined
          }
          aria-label={`Search for a course to add to ${termName}`}
          placeholder="Search by code or title"
          autoComplete="off"
          className="w-full bg-transparent py-2 text-[13.5px] text-ink outline-none placeholder:text-ink-5"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActiveIndex(0);
          }}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault();
              setActiveIndex((index) => (options.length ? (index + 1) % options.length : 0));
            } else if (event.key === 'ArrowUp') {
              event.preventDefault();
              setActiveIndex((index) =>
                options.length ? (index - 1 + options.length) % options.length : 0,
              );
            } else if (event.key === 'Home') {
              event.preventDefault();
              setActiveIndex(0);
            } else if (event.key === 'End') {
              event.preventDefault();
              setActiveIndex(Math.max(options.length - 1, 0));
            } else if (event.key === 'Enter') {
              event.preventDefault();
              commit(options[activeIndex]);
            } else if (event.key === 'Escape') {
              event.preventDefault();
              event.stopPropagation();
              onClose();
            }
          }}
        />
      </div>

      {state.status === 'pending' ? (
        <p className="px-1 py-3 text-[13px] text-ink-4">Loading the course list…</p>
      ) : null}

      {state.status === 'failed' ? (
        <div role="alert" className="px-1 py-3 text-[13px] text-ink-2">
          <p className="font-medium text-ink">The course list did not load.</p>
          <p className="mt-0.5">{state.message}</p>
          <Button size="sm" className="mt-2" onClick={retry}>
            Try again
          </Button>
        </div>
      ) : null}

      {catalogue ? (
        <ul
          ref={listRef}
          id={listboxId}
          role="listbox"
          aria-label={`Courses you can add to ${termName}`}
          className="mt-2 max-h-64 overflow-y-auto"
        >
          {options.length === 0 ? (
            <li className="px-2 py-3 text-[13px] text-ink-4">
              No course in the sample list matches “{query}”.
            </li>
          ) : (
            options.map((course, index) => {
              const already = placements.get(course.code);
              return (
                <li
                  key={course.code}
                  id={`${listboxId}-option-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                  data-active={index === activeIndex}
                  className={`cursor-pointer rounded-chip px-2 py-1.5 ${
                    index === activeIndex ? 'bg-gold-wash' : ''
                  }`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    commit(course);
                  }}
                >
                  <span className="flex items-baseline gap-2">
                    <span className="course-code text-[12.5px] text-ink">{course.code}</span>
                    <span className="tnum ml-auto shrink-0 text-[11.5px] text-ink-3">
                      {formatUnits(course.units)} units
                    </span>
                  </span>
                  <span className="block truncate text-[12px] leading-snug text-ink-3">
                    {course.title}
                  </span>
                  {already ? (
                    <span className="block truncate text-[11px] text-ink-4">
                      Already in {already.join(', ')}
                    </span>
                  ) : null}
                </li>
              );
            })
          )}
        </ul>
      ) : null}

      <div className="mt-2 flex items-center justify-between gap-2 border-t border-line-soft pt-2">
        <p className="text-[11.5px] text-ink-4">
          Adding to {termName}. Enter adds, Escape closes.
        </p>
        <Button size="sm" onClick={onClose}>
          Done
        </Button>
      </div>
      <span className="sr-only" data-testid={`picker-term-${termId}`} />
    </div>
  );
}
