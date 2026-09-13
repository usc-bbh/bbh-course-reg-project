import { useMemo, useState } from 'react';
import type { ParsedStarsReport, Season, StudentSituation } from '../../domain/types';
import { SEASONS, seasonLabel } from '../../domain/terms';
import { useCatalogue } from '../../data/useCatalogue';
import { Button } from '../../components/Button';
import { CONTROL, Field, Select, TextInput } from '../../components/Field';
import { NumberInput } from '../../components/NumberInput';
import { TRANSFER_UNITS_MAX, YEAR_MAX, YEAR_MIN } from '../../domain/limits';
import { CourseRowsEditor } from './CourseRowsEditor';

/** USC's own vocabulary, as the parser and the validator both use it. */
type ClassLevel = ParsedStarsReport['classLevel'];
const CLASS_LEVELS: ClassLevel[] = ['Freshman', 'Sophomore', 'Junior', 'Senior'];

export interface SituationReviewProps {
  situation: StudentSituation;
  /** 'first' is the step after choosing a way in; 'edit' is the later return. */
  mode: 'first' | 'edit';
  onSave: (situation: StudentSituation) => void;
  onCancel: () => void;
}

/**
 * The review step: a prefilled, editable form.
 *
 * Whatever a student arrives with — a parsed report, the sample student, or a
 * blank form — they land here and confirm it. Parsed data is never perfect, so
 * correcting it is the main event rather than an afterthought.
 */
export function SituationReview({ situation, mode, onSave, onCancel }: SituationReviewProps) {
  const [draft, setDraft] = useState<StudentSituation>(situation);
  const { state: catalogueState, retry } = useCatalogue();

  const catalogue = catalogueState.status === 'ready' ? catalogueState.catalogue : null;

  const majorOptions = useMemo(() => withCurrent(catalogue?.majors, draft.major), [catalogue, draft.major]);
  const yearOptions = useMemo(
    () => withCurrent(catalogue?.catalogYears, draft.catalogYear),
    [catalogue, draft.catalogYear],
  );
  const minorOptions = catalogue?.minors ?? [];

  const patch = (changes: Partial<StudentSituation>) => setDraft((current) => ({ ...current, ...changes }));

  return (
    <form
      className="mx-auto w-full max-w-4xl px-5 py-10 sm:px-8 sm:py-12"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(draft);
      }}
    >
      <h1 className="wordmark text-title leading-tight text-ink">
        {mode === 'first' ? 'Check your details' : 'Edit your details'}
      </h1>
      <p className="mt-2 max-w-2xl text-body leading-relaxed text-ink-2">
        {mode === 'first'
          ? 'Nothing here is read from a server, and nothing is sent to one. Correct anything that is wrong before you go on — the plan and the check both build on it.'
          : 'Changes apply straight away and the check re-runs.'}
      </p>

      {catalogueState.status === 'failed' ? (
        <div
          role="status"
          className="mt-5 flex flex-wrap items-center gap-3 rounded-card border border-warning-line bg-warning-wash px-4 py-3 text-small text-ink-2"
        >
          <span>
            The course list did not load, so majors and catalogue years are free text for now.
          </span>
          <Button size="sm" onClick={retry}>
            Try again
          </Button>
        </div>
      ) : null}

      <section className="mt-8 grid gap-5 sm:grid-cols-2">
        <Field label="Your name" hint="Shown on the printed plan. It stays on this device.">
          {({ id }) => (
            <TextInput
              id={id}
              value={draft.studentName}
              autoComplete="off"
              onChange={(event) => patch({ studentName: event.target.value })}
            />
          )}
        </Field>

        <Field label="Major">
          {({ id }) =>
            majorOptions.length > 0 ? (
              <Select
                id={id}
                value={draft.major}
                onChange={(event) => patch({ major: event.target.value })}
              >
                <option value="">Choose a major</option>
                {majorOptions.map((major) => (
                  <option key={major} value={major}>
                    {major}
                  </option>
                ))}
              </Select>
            ) : (
              <TextInput
                id={id}
                value={draft.major}
                onChange={(event) => patch({ major: event.target.value })}
              />
            )
          }
        </Field>

        <Field label="Catalogue year" hint="The year whose requirements you follow.">
          {({ id, describedBy }) =>
            yearOptions.length > 0 ? (
              <Select
                id={id}
                aria-describedby={describedBy}
                value={draft.catalogYear}
                onChange={(event) => patch({ catalogYear: event.target.value })}
              >
                {yearOptions.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </Select>
            ) : (
              <TextInput
                id={id}
                aria-describedby={describedBy}
                value={draft.catalogYear}
                onChange={(event) => patch({ catalogYear: event.target.value })}
              />
            )
          }
        </Field>

        <Field label="Class level">
          {({ id }) => (
            <Select
              id={id}
              value={draft.classLevel}
              onChange={(event) => patch({ classLevel: event.target.value as ClassLevel })}
            >
              {CLASS_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Started in">
            {({ id }) => (
              <Select
                id={id}
                value={draft.entryTerm.season}
                onChange={(event) =>
                  patch({ entryTerm: { ...draft.entryTerm, season: event.target.value as Season } })
                }
              >
                {SEASONS.map((season) => (
                  <option key={season} value={season}>
                    {seasonLabel(season)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label="Year">
            {({ id }) => (
              <NumberInput
                id={id}
                className={`${CONTROL} tnum`}
                value={draft.entryTerm.year}
                integer
                min={YEAR_MIN}
                max={YEAR_MAX}
                onCommit={(year) => patch({ entryTerm: { ...draft.entryTerm, year } })}
              />
            )}
          </Field>
        </div>

        <Field label="Transfer units" hint="Units brought in from elsewhere, as one total.">
          {({ id, describedBy }) => (
            <NumberInput
              id={id}
              className={`${CONTROL} tnum`}
              aria-describedby={describedBy}
              value={draft.transferUnits}
              min={0}
              max={TRANSFER_UNITS_MAX}
              onCommit={(transferUnits) => patch({ transferUnits })}
            />
          )}
        </Field>
      </section>

      <section className="mt-10 grid gap-5 sm:grid-cols-2">
        <Field
          label="Minor"
          hint="One, or none. Your report records a single minor."
        >
          {({ id, describedBy }) =>
            minorOptions.length > 0 ? (
              <Select
                id={id}
                aria-describedby={describedBy}
                value={draft.minor ?? ''}
                onChange={(event) => patch({ minor: event.target.value || null })}
              >
                <option value="">No minor</option>
                {withCurrent(minorOptions, draft.minor ?? '').map((minor) => (
                  <option key={minor} value={minor}>
                    {minor}
                  </option>
                ))}
              </Select>
            ) : (
              <TextInput
                id={id}
                aria-describedby={describedBy}
                value={draft.minor ?? ''}
                onChange={(event) => patch({ minor: event.target.value || null })}
              />
            )
          }
        </Field>

        <Field label="Concentration" hint="Leave blank if your major has none.">
          {({ id, describedBy }) => (
            <TextInput
              id={id}
              aria-describedby={describedBy}
              value={draft.concentration ?? ''}
              onChange={(event) => patch({ concentration: event.target.value || null })}
            />
          )}
        </Field>
      </section>

      <div className="mt-10 flex flex-col gap-10">
        <CourseRowsEditor
          legend="Courses you have completed"
          hint="Code, title, units, the term you took it, and the grade."
          courses={draft.completedCourses}
          withGrade
          onChange={(completedCourses) => patch({ completedCourses })}
        />
        <CourseRowsEditor
          legend="Courses you are taking now"
          hint="These are locked on the timeline but carry no grade yet."
          courses={draft.inProgressCourses}
          withGrade={false}
          onChange={(inProgressCourses) => patch({ inProgressCourses })}
        />
      </div>

      <div className="sticky bottom-0 -mx-5 mt-10 flex flex-wrap justify-end gap-2.5 border-t border-line bg-canvas/95 px-5 py-4 backdrop-blur-sm sm:-mx-8 sm:px-8">
        <Button onClick={onCancel}>{mode === 'first' ? 'Start over' : 'Cancel'}</Button>
        <Button variant="primary" type="submit">
          {mode === 'first' ? 'Continue to my plan' : 'Save details'}
        </Button>
      </div>
    </form>
  );
}

/** Keeps a value that is not in the catalogue list selectable. */
function withCurrent(options: string[] | undefined, current: string): string[] {
  if (!options) return [];
  if (!current || options.includes(current)) return options;
  return [...options, current];
}
