import { useRef, useState, type DragEvent } from 'react';
import type { StudentSituation } from '../../domain/types';
import { parseStarsReport } from '../../data/parseStarsReport';
import { sampleSituation } from '../../data/sampleStudent';
import { Button } from '../../components/Button';
import { FileIcon, UploadIcon } from '../../components/icons';
import { blankSituation } from './blankSituation';

type Phase =
  | { kind: 'idle' }
  | { kind: 'reading' }
  | { kind: 'failed'; message: string };

export interface SituationEntryProps {
  /** Called with a prefilled situation. The next step is always the review. */
  onStart: (situation: StudentSituation, origin: 'stars' | 'sample' | 'manual') => void;
}

/**
 * The empty state: three ways in, all of them ending at the same review step.
 *
 * The uploaded file is handed straight to the parser and then dropped. It is
 * never stored, never read into state, and never named anywhere that persists.
 */
export function SituationEntry({ onStart }: SituationEntryProps) {
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' });
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const readFile = (file: File | undefined) => {
    if (!file) return;
    setPhase({ kind: 'reading' });
    parseStarsReport(file)
      .then((parsed) => {
        setPhase({ kind: 'idle' });
        onStart(parsed.situation, 'stars');
      })
      .catch(() => {
        // No detail from the file itself reaches this message or the console.
        setPhase({
          kind: 'failed',
          message:
            'We could not read that report. It may be a scan, or a format we do not handle yet.',
        });
      });
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    readFile(event.dataTransfer.files[0]);
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-5 py-12 sm:px-8 sm:py-20">
      <h1 className="wordmark text-display leading-tight text-ink sm:text-hero">
        Plan your next four years
      </h1>
      <p className="mt-2 max-w-xl text-base leading-relaxed text-ink-2">
        Lay out the terms ahead and see whether the plan reaches your degree — and what is still
        missing if it does not.
      </p>

      <section aria-labelledby="entry-upload" className="mt-10">
        <h2 id="entry-upload" className="text-base font-semibold text-ink">
          Start from your STARS report
        </h2>
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={`mt-4 rounded-panel border-2 border-dashed p-7 transition-colors duration-150 sm:p-9 ${
            dragging ? 'border-cardinal bg-gold-wash' : 'border-line-strong bg-surface'
          }`}
        >
          <div className="flex flex-col items-start gap-5 sm:flex-row sm:items-center">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-field bg-surface-sunk text-ink-3">
              <UploadIcon size={20} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-body font-medium text-ink">
                Drop your report here, or choose the file yourself.
              </p>
              <p className="mt-1 text-small text-ink-3">
                PDF, HTML or text. Your report is read on this device and never sent anywhere.
              </p>
            </div>
            <Button
              variant="primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={phase.kind === 'reading'}
            >
              <FileIcon />
              {phase.kind === 'reading' ? 'Reading your report…' : 'Choose a file'}
            </Button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            className="sr-only"
            accept=".pdf,.htm,.html,.txt,application/pdf,text/html,text/plain"
            aria-label="STARS report file"
            onChange={(event) => {
              readFile(event.target.files?.[0]);
              // Clear the input so choosing the same file twice still fires.
              event.target.value = '';
            }}
          />
        </div>

        {phase.kind === 'failed' ? (
          <div
            role="alert"
            className="anim-expand mt-3 rounded-card border border-warning-line bg-warning-wash px-4 py-3 text-body text-ink-2"
          >
            <p className="font-medium text-ink">{phase.message}</p>
            <p className="mt-1">
              You can fill your details in yourself, or look around with the sample student first.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button size="sm" onClick={() => onStart(blankSituation(), 'manual')}>
                Enter my details
              </Button>
              <Button size="sm" onClick={() => onStart(sampleSituation, 'sample')}>
                Use the sample student
              </Button>
            </div>
          </div>
        ) : null}
      </section>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => onStart(sampleSituation, 'sample')}
          className="group rounded-card border border-line bg-surface p-5 text-left transition-[border-color,box-shadow] duration-150 hover:border-ink-5 hover:shadow-raise"
        >
          <span className="flex items-center gap-2 text-body font-semibold text-ink">
            Try it with a sample student
          </span>
          <span className="mt-1 block text-small text-ink-3">
            A made-up computer science junior with a half-finished plan. Nothing is saved as yours.
          </span>
        </button>

        <button
          type="button"
          onClick={() => onStart(blankSituation(), 'manual')}
          className="group rounded-card border border-line bg-surface p-5 text-left transition-[border-color,box-shadow] duration-150 hover:border-ink-5 hover:shadow-raise"
        >
          <span className="flex items-center gap-2 text-body font-semibold text-ink">
            Enter it myself
          </span>
          <span className="mt-1 block text-small text-ink-3">
            Type your major, catalogue year and the courses you have already taken.
          </span>
        </button>
      </div>
    </div>
  );
}
