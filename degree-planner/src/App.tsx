import { useEffect, useMemo, useRef, useState } from 'react';
import type { CatalogueCourse, Plan, Selection, StudentSituation, TermId } from './domain/types';
import { buildTimeline, termLabel } from './domain/terms';
import { defaultPlannedTerms, newCourseId, usePlanner } from './state/plannerStore';
import { clearSaved } from './state/persistence';
import { useAnalysis } from './state/useAnalysis';
import { samplePlan } from './data/sampleStudent';
import { AppHeader } from './components/AppHeader';
import { ErrorBoundary } from './components/ErrorBoundary';
import { UndoToast } from './components/UndoToast';
import { SituationEntry } from './features/situation/SituationEntry';
import { SituationReview } from './features/situation/SituationReview';
import { SituationSummary } from './features/situation/SituationSummary';
import { PlanTimeline } from './features/plan/PlanTimeline';
import { AuditPanel, SampleBadge } from './features/audit/AuditPanel';
import { unmetCount } from './features/audit/unmetCount';
import { AuditSheet } from './features/audit/AuditSheet';
import { buildHighlight } from './features/audit/highlight';
import { PlanToolbar } from './features/toolbar/PlanToolbar';
import { useTodayIso } from './features/toolbar/useTodayIso';

type Origin = 'stars' | 'sample' | 'manual';

interface ReviewState {
  situation: StudentSituation;
  mode: 'first' | 'edit';
  origin: Origin;
}

export function App() {
  const { state, dispatch, saveState } = usePlanner();
  const [review, setReview] = useState<ReviewState | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const printedOn = useTodayIso();
  const lastAnnounced = useRef('');

  const timeline = useMemo(
    () => (state.situation ? buildTimeline(state.situation, state.plan) : []),
    [state.situation, state.plan],
  );

  const { state: analysis, retry } = useAnalysis(state.situation, timeline);
  const result = analysis.status === 'ready' ? analysis.result : null;
  const highlight = useMemo(() => buildHighlight(result, state.selection), [result, state.selection]);

  // One polite announcement per new result, not one per keystroke.
  useEffect(() => {
    if (analysis.status !== 'ready') return;
    const unmet = unmetCount(analysis.result);
    const warnings = analysis.result.warnings.length;
    const message = `${unmet} ${unmet === 1 ? 'requirement' : 'requirements'} unmet, ${warnings} ${
      warnings === 1 ? 'warning' : 'warnings'
    }.`;
    if (message === lastAnnounced.current) return;
    lastAnnounced.current = message;
    setAnnouncement(message);
  }, [analysis]);

  // Escape clears the current selection, from anywhere on the page.
  useEffect(() => {
    if (!state.selection) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') dispatch({ type: 'select', selection: null });
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [state.selection, dispatch]);

  const select = (selection: Selection) => dispatch({ type: 'select', selection });

  const startFrom = (situation: StudentSituation, origin: Origin) => {
    setReview({ situation, mode: 'first', origin });
  };

  const saveReview = (situation: StudentSituation) => {
    if (!review) return;
    if (review.mode === 'edit') {
      dispatch({ type: 'situation-changed', situation });
    } else {
      // GAP(stars): a report says what a student has done, not what they intend
      // to do, so there is no proposed plan to seed from an upload. Uploads and
      // manual entry start from empty fall and spring terms for four years from
      // the entry term; only the sample student arrives with a plan already in
      // it.
      const plan: Plan =
        review.origin === 'sample'
          ? structuredClone(samplePlan)
          : { schemaVersion: 1, terms: defaultPlannedTerms(situation) };
      dispatch({ type: 'start', situation, plan });
    }
    setReview(null);
  };

  const restoreFocusToTerm = (termId: TermId) => {
    const target = document.querySelector<HTMLElement>(`[data-focus-key="add-${termId}"]`);
    target?.focus();
  };

  const addCourse = (termId: TermId, course: CatalogueCourse) => {
    dispatch({
      type: 'add-course',
      termId,
      course: { id: newCourseId(), code: course.code, title: course.title, units: course.units },
    });
  };

  /* ── Screens ─────────────────────────────────────────────────────────── */

  // A stable shell until the saved copy has been read. Never branch the first
  // paint on storage.
  if (!state.hydrated) {
    return (
      <div className="min-h-screen">
        <AppHeader />
        <p className="mx-auto max-w-3xl px-4 py-16 text-[14px] text-ink-4" role="status">
          Opening your plan…
        </p>
      </div>
    );
  }

  if (review) {
    return (
      <div className="min-h-screen">
        <AppHeader />
        <Notice notice={state.notice} onDismiss={() => dispatch({ type: 'dismiss-notice' })} />
        <ErrorBoundary area="Your details">
          <SituationReview
            situation={review.situation}
            mode={review.mode}
            onSave={saveReview}
            onCancel={() => setReview(null)}
          />
        </ErrorBoundary>
      </div>
    );
  }

  if (!state.situation) {
    return (
      <div className="min-h-screen">
        <AppHeader />
        <Notice notice={state.notice} onDismiss={() => dispatch({ type: 'dismiss-notice' })} />
        <ErrorBoundary area="This page">
          <SituationEntry onStart={startFrom} />
        </ErrorBoundary>
      </div>
    );
  }

  const situation = state.situation;
  const destinations = state.plan.terms.filter((term) => term.status === 'planned');
  const undoTerm = state.undoable
    ? timeline.find((term) => term.id === state.undoable?.termId)
    : undefined;

  return (
    <div className="min-h-screen pb-24 xl:pb-0">
      <a href="#plan" className="sr-only-focusable absolute z-50 m-2 rounded-control bg-surface px-3 py-2 text-[13px] font-medium text-ink shadow-overlay">
        Skip to the plan
      </a>

      <AppHeader />

      {/* Print-only header: no app chrome on paper, but the plan still needs
          to say whose it is and when it was printed. */}
      <div data-print="only" className="print-block px-1 pb-2">
        <p className="text-[15px] font-semibold">
          Four-year degree plan — {situation.studentName || 'Unnamed student'}
        </p>
        <p className="text-[11px]">Printed {printedOn}</p>
      </div>
      {result?.isSample ? <SampleBadge className="hidden print:flex" /> : null}

      <Notice notice={state.notice} onDismiss={() => dispatch({ type: 'dismiss-notice' })} />

      <ErrorBoundary area="Your details">
        <SituationSummary
          situation={situation}
          onEdit={() => setReview({ situation, mode: 'edit', origin: situation.source })}
        />
      </ErrorBoundary>

      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      <main
        id="plan"
        className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6"
        tabIndex={-1}
      >
        <div data-print-layout className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
          <section aria-labelledby="plan-heading" className="min-w-0">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <h2 id="plan-heading" className="text-[17px] font-semibold text-ink">
                Four-year plan
              </h2>
              <PlanToolbar
                situation={situation}
                plan={state.plan}
                saveState={saveState}
                onImport={(imported, plan) =>
                  dispatch({ type: 'imported', situation: imported, plan })
                }
                onResetPlan={() => dispatch({ type: 'reset-plan' })}
                onClearAll={() => {
                  clearSaved();
                  dispatch({ type: 'clear-all' });
                }}
              />
            </div>

            <ErrorBoundary area="The plan">
              <PlanTimeline
                timeline={timeline}
                destinations={destinations}
                highlight={highlight}
                selection={state.selection}
                onAddYear={() => dispatch({ type: 'add-year' })}
                onAddTerm={(season, year) => dispatch({ type: 'add-term', season, year })}
                onAddCourse={addCourse}
                onMoveCourse={(courseId, toTermId) =>
                  dispatch({ type: 'move-course', courseId, toTermId })
                }
                onRemoveCourse={(termId, courseId) =>
                  dispatch({ type: 'remove-course', termId, courseId })
                }
                onRemoveTerm={(termId) => dispatch({ type: 'remove-term', termId })}
              />
            </ErrorBoundary>
          </section>

          <aside
            data-print-region="audit"
            aria-labelledby="audit-heading"
            className="hidden min-w-0 xl:block print:block"
          >
            <div className="sticky top-5 rounded-panel border border-line bg-surface print:static print:border-0">
              <h2
                id="audit-heading"
                className="border-b border-line-soft px-4 py-3 text-[15px] font-semibold text-ink"
              >
                Your plan, checked
              </h2>
              <ErrorBoundary area="The check">
                <AuditPanel
                  state={analysis}
                  selection={state.selection}
                  onSelect={select}
                  onRetry={retry}
                />
              </ErrorBoundary>
            </div>
          </aside>
        </div>
      </main>

      <AuditSheet state={analysis} selection={state.selection} onSelect={select} onRetry={retry} />

      {state.undoable && undoTerm ? (
        <UndoToast
          courseCode={state.undoable.course.code}
          termName={termLabel(undoTerm)}
          onUndo={() => {
            const termId = state.undoable?.termId;
            dispatch({ type: 'undo-remove' });
            if (termId) window.setTimeout(() => restoreFocusToTerm(termId), 0);
          }}
          onDismiss={() => {
            const termId = state.undoable?.termId;
            dispatch({ type: 'dismiss-undo' });
            if (termId) window.setTimeout(() => restoreFocusToTerm(termId), 0);
          }}
        />
      ) : null}
    </div>
  );
}

function Notice({ notice, onDismiss }: { notice: string | null; onDismiss: () => void }) {
  if (!notice) return null;
  return (
    <div
      role="status"
      data-print="hide"
      className="border-b border-warning-line bg-warning-wash px-4 py-2.5 text-[13px] text-ink-2 sm:px-6"
    >
      <div className="mx-auto flex w-full max-w-[1600px] items-center gap-3">
        <span className="min-w-0 flex-1">{notice}</span>
        <button
          type="button"
          className="shrink-0 rounded-chip px-2 py-1 text-[12.5px] font-medium text-ink hover:bg-gold-dim/40"
          onClick={onDismiss}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
