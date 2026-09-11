import { useMemo, useState } from 'react';
import type { ClassStanding, Season, StudentSituation } from '../../domain/types';
import { SEASONS, seasonLabel } from '../../domain/terms';
import { useCatalogue } from '../../data/useCatalogue';
import { Button, IconButton } from '../../components/Button';
import { Field, Select, TextInput } from '../../components/Field';
import { CloseIcon, PlusIcon } from '../../components/icons';
import { CourseRowsEditor } from './CourseRowsEditor';

const STANDINGS: ClassStanding[] = ['freshman', 'sophomore', 'junior', 'senior'];
const STANDING_LABEL: Record<ClassStanding, string> = {
  freshman: 'First year',
  sophomore: 'Second year',
  junior: 'Third year',
  senior: 'Fourth year or beyond',
};

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
  const [minorToAdd, setMinorToAdd] = useState('');

  const catalogue = catalogueState.status === 'ready' ? catalogueState.catalogue : null;

  const majorOptions = useMemo(() => withCurrent(catalogue?.majors, draft.major), [catalogue, draft.major]);
  const yearOptions = useMemo(
    () => withCurrent(catalogue?.catalogueYears, draft.catalogueYear),
    [catalogue, draft.catalogueYear],
  );
  const minorOptions = (catalogue?.minors ?? []).filter((minor) => !draft.minors.includes(minor));

  const patch = (changes: Partial<StudentSituation>) => setDraft((current) => ({ ...current, ...changes }));

  return (
    <form
      className="mx-auto w-full max-w-4xl px-4 py-8"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(draft);
      }}
    >
      <h1 className="text-[24px] leading-tight font-semibold text-ink">
        {mode === 'first' ? 'Check your details' : 'Edit your details'}
      </h1>
      <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-ink-2">
        {mode === 'first'
          ? 'Nothing here is read from a server, and nothing is sent to one. Correct anything that is wrong before you go on — the plan and the check both build on it.'
          : 'Changes apply straight away and the check re-runs.'}
      </p>

      {catalogueState.status === 'failed' ? (
        <div
          role="status"
          className="mt-5 flex flex-wrap items-center gap-3 rounded-card border border-warning-line bg-warning-wash px-4 py-3 text-[13px] text-ink-2"
        >
          <span>
            The course list did not load, so majors and catalogue years are free text for now.
          </span>
          <Button size="sm" onClick={retry}>
            Try again
          </Button>
        </div>
      ) : null}

      <section className="mt-6 grid gap-4 sm:grid-cols-2">
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
                value={draft.catalogueYear}
                onChange={(event) => patch({ catalogueYear: event.target.value })}
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
                value={draft.catalogueYear}
                onChange={(event) => patch({ catalogueYear: event.target.value })}
              />
            )
          }
        </Field>

        <Field label="Class standing">
          {({ id }) => (
            <Select
              id={id}
              value={draft.classStanding}
              onChange={(event) => patch({ classStanding: event.target.value as ClassStanding })}
            >
              {STANDINGS.map((standing) => (
                <option key={standing} value={standing}>
                  {STANDING_LABEL[standing]}
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
              <TextInput
                id={id}
                className="tnum"
                inputMode="numeric"
                value={String(draft.entryTerm.year)}
                onChange={(event) => {
                  const year = Number(event.target.value);
                  patch({
                    entryTerm: {
                      ...draft.entryTerm,
                      year: Number.isFinite(year) ? year : draft.entryTerm.year,
                    },
                  });
                }}
              />
            )}
          </Field>
        </div>

        <Field label="Transfer units" hint="Units brought in from elsewhere, as one total.">
          {({ id, describedBy }) => (
            <TextInput
              id={id}
              className="tnum"
              inputMode="decimal"
              aria-describedby={describedBy}
              value={String(draft.transferUnits)}
              onChange={(event) => {
                const units = Number(event.target.value);
                patch({ transferUnits: Number.isFinite(units) ? units : 0 });
              }}
            />
          )}
        </Field>
      </section>

      <section className="mt-6">
        <h2 className="text-[14px] font-semibold text-ink">Minors</h2>
        {draft.minors.length > 0 ? (
          <ul className="mt-2 flex flex-wrap gap-2">
            {draft.minors.map((minor) => (
              <li
                key={minor}
                className="inline-flex items-center gap-1 rounded-pill border border-line bg-surface py-1 pr-1 pl-3 text-[13px] text-ink"
              >
                {minor}
                <IconButton
                  label={`Remove the ${minor} minor`}
                  size="sm"
                  onClick={() => patch({ minors: draft.minors.filter((entry) => entry !== minor) })}
                >
                  <CloseIcon size={13} />
                </IconButton>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-[13px] text-ink-4">None declared.</p>
        )}

        <div className="mt-3 flex flex-wrap items-end gap-2">
          <Field label="Add a minor" className="min-w-56 flex-1">
            {({ id }) =>
              minorOptions.length > 0 ? (
                <Select
                  id={id}
                  value={minorToAdd}
                  onChange={(event) => setMinorToAdd(event.target.value)}
                >
                  <option value="">Choose a minor</option>
                  {minorOptions.map((minor) => (
                    <option key={minor} value={minor}>
                      {minor}
                    </option>
                  ))}
                </Select>
              ) : (
                <TextInput
                  id={id}
                  value={minorToAdd}
                  onChange={(event) => setMinorToAdd(event.target.value)}
                />
              )
            }
          </Field>
          <Button
            className="mb-0.5"
            disabled={!minorToAdd.trim()}
            onClick={() => {
              const minor = minorToAdd.trim();
              if (!minor || draft.minors.includes(minor)) return;
              patch({ minors: [...draft.minors, minor] });
              setMinorToAdd('');
            }}
          >
            <PlusIcon />
            Add minor
          </Button>
        </div>
      </section>

      <div className="mt-8 flex flex-col gap-8">
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

      <div className="sticky bottom-0 -mx-4 mt-8 flex flex-wrap justify-end gap-2 border-t border-line bg-canvas/95 px-4 py-3 backdrop-blur-sm">
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
