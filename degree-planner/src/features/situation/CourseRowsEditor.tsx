import { useId, useState } from 'react';
import type { Season, TakenCourse } from '../../domain/types';
import { SEASONS, makeTermId, parseTermId, seasonLabel } from '../../domain/terms';
import { Button, IconButton } from '../../components/Button';
import { PlusIcon, TrashIcon } from '../../components/icons';
import { PLAN_BASE_YEAR } from '../../data/sampleStudent';

const CELL =
  'w-full rounded-chip border border-line-strong bg-surface px-2 py-1.5 text-[13px] text-ink ' +
  'transition-[border-color] duration-150 hover:border-ink-5';

export interface CourseRowsEditorProps {
  legend: string;
  hint: string;
  courses: TakenCourse[];
  withGrade: boolean;
  onChange: (courses: TakenCourse[]) => void;
}

/**
 * The editable list of coursework behind the review step.
 *
 * Parsed data is never perfect, so correcting it is the main event: every row
 * can be edited, added and removed, and the term is a real field rather than
 * something inferred.
 */
export function CourseRowsEditor({
  legend,
  hint,
  courses,
  withGrade,
  onChange,
}: CourseRowsEditorProps) {
  const groupId = useId();
  const [lastAdded, setLastAdded] = useState<number | null>(null);

  const update = (index: number, patch: Partial<TakenCourse>) => {
    onChange(courses.map((course, position) => (position === index ? { ...course, ...patch } : course)));
  };

  const updateTerm = (index: number, season: Season, year: number) => {
    update(index, { termId: makeTermId(season, year) });
  };

  const addRow = () => {
    const previous = courses[courses.length - 1];
    const template: TakenCourse = {
      code: '',
      title: '',
      units: 4,
      termId: previous?.termId ?? makeTermId('fall', PLAN_BASE_YEAR),
    };
    onChange([...courses, template]);
    setLastAdded(courses.length);
  };

  return (
    <fieldset className="min-w-0">
      <legend className="text-[14px] font-semibold text-ink">{legend}</legend>
      <p className="mt-0.5 mb-3 text-[12.5px] text-ink-3">{hint}</p>

      {courses.length === 0 ? (
        <p className="rounded-card border border-dashed border-line-strong bg-surface-2 px-3 py-4 text-[13px] text-ink-4">
          Nothing here yet.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {courses.map((course, index) => {
            const parsed = parseTermId(course.termId) ?? { season: 'fall' as Season, year: PLAN_BASE_YEAR };
            const rowLabel = course.code || `row ${index + 1}`;
            return (
              <li
                key={`${groupId}-${index}`}
                className="grid grid-cols-2 gap-2 rounded-card border border-line bg-surface p-2.5 sm:grid-cols-[7rem_1fr_4rem_5.5rem_5rem_auto]"
              >
                <input
                  className={`${CELL} course-code`}
                  value={course.code}
                  autoFocus={lastAdded === index}
                  aria-label={`Course code, ${rowLabel}`}
                  placeholder="CSCI 104L"
                  onChange={(event) => update(index, { code: event.target.value })}
                />
                <input
                  className={`${CELL} col-span-2 sm:col-span-1`}
                  value={course.title}
                  aria-label={`Course title, ${rowLabel}`}
                  placeholder="Data Structures"
                  onChange={(event) => update(index, { title: event.target.value })}
                />
                <input
                  className={`${CELL} tnum`}
                  value={String(course.units)}
                  inputMode="decimal"
                  aria-label={`Units, ${rowLabel}`}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    update(index, { units: Number.isFinite(next) ? next : 0 });
                  }}
                />
                <select
                  className={CELL}
                  value={parsed.season}
                  aria-label={`Term season, ${rowLabel}`}
                  onChange={(event) => updateTerm(index, event.target.value as Season, parsed.year)}
                >
                  {SEASONS.map((season) => (
                    <option key={season} value={season}>
                      {seasonLabel(season)}
                    </option>
                  ))}
                </select>
                <input
                  className={`${CELL} tnum`}
                  value={String(parsed.year)}
                  inputMode="numeric"
                  aria-label={`Term year, ${rowLabel}`}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    updateTerm(index, parsed.season, Number.isFinite(next) ? next : parsed.year);
                  }}
                />
                <div className="flex items-center justify-end gap-2">
                  {withGrade ? (
                    <input
                      className={`${CELL} w-14`}
                      value={course.grade ?? ''}
                      aria-label={`Grade, ${rowLabel}`}
                      placeholder="A-"
                      onChange={(event) => {
                        const grade = event.target.value;
                        const next = { ...course };
                        if (grade) next.grade = grade;
                        else delete next.grade;
                        onChange(
                          courses.map((entry, position) => (position === index ? next : entry)),
                        );
                      }}
                    />
                  ) : null}
                  <IconButton
                    label={`Remove ${rowLabel}`}
                    size="sm"
                    onClick={() => onChange(courses.filter((_, position) => position !== index))}
                  >
                    <TrashIcon />
                  </IconButton>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <Button size="sm" className="mt-3" onClick={addRow}>
        <PlusIcon />
        Add a course
      </Button>
    </fieldset>
  );
}
