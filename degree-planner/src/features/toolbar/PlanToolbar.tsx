import { useRef, useState } from 'react';
import type { Plan, StudentSituation } from '../../domain/types';
import { Button } from '../../components/Button';
import { Dialog } from '../../components/Dialog';
import { MenuButton, type MenuItem } from '../../components/MenuButton';
import { ChevronDownIcon, DownloadIcon, PrinterIcon } from '../../components/icons';
import { downloadExport, readImport } from './planFile';

type Confirm = 'none' | 'reset' | 'clear' | 'overwrite';

export interface PlanToolbarProps {
  situation: StudentSituation;
  plan: Plan;
  saveState: 'idle' | 'saving' | 'saved' | 'error';
  onImport: (situation: StudentSituation, plan: Plan) => void;
  onResetPlan: () => void;
  onClearAll: () => void;
}

const MORE_TRIGGER =
  'inline-flex h-10 items-center gap-1.5 rounded-control border border-line-strong bg-surface ' +
  'px-4 text-body font-medium text-ink transition-colors duration-150 hover:border-ink-5 hover:bg-surface-2';

/**
 * Save, export, import, print, reset.
 *
 * The two a student reaches for while planning sit out in the open; the rest —
 * including both destructive ones — live one step behind a menu, so a row of
 * buttons never competes with the plan itself. Every action keeps its name from
 * the button to the dialog, and each confirm says exactly what will be lost.
 */
export function PlanToolbar({
  situation,
  plan,
  saveState,
  onImport,
  onResetPlan,
  onClearAll,
}: PlanToolbarProps) {
  const [confirm, setConfirm] = useState<Confirm>('none');
  const [importProblem, setImportProblem] = useState<string | null>(null);
  const [pendingImport, setPendingImport] = useState<{
    situation: StudentSituation;
    plan: Plan;
  } | null>(null);
  const importInputRef = useRef<HTMLInputElement | null>(null);

  const planHasCourses = plan.terms.some((term) => term.courses.length > 0);

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    setImportProblem(null);
    void readImport(file).then((checked) => {
      if (!checked.ok) {
        setImportProblem(
          `We could not import that file because ${checked.problem}. Export a new one and try again.`,
        );
        return;
      }
      if (planHasCourses) {
        setPendingImport({ situation: checked.value.situation, plan: checked.value.plan });
        setConfirm('overwrite');
      } else {
        onImport(checked.value.situation, checked.value.plan);
      }
    });
  };

  const moreActions: MenuItem[] = [
    { key: 'import', label: 'Import plan', run: () => importInputRef.current?.click() },
    { key: 'reset', label: 'Reset plan', run: () => setConfirm('reset') },
    { key: 'clear', label: 'Clear all data', run: () => setConfirm('clear'), danger: true },
  ];

  return (
    <div className="flex flex-wrap items-center gap-2" data-print="hide">
      <p
        className="mr-1 text-micro text-ink-4"
        role="status"
        aria-live="polite"
        data-testid="save-status"
      >
        {saveState === 'error'
          ? 'Not saved on this device — storage is unavailable.'
          : saveState === 'saved'
            ? 'Saved on this device.'
            : saveState === 'saving'
              ? 'Saving…'
              : ''}
      </p>

      <Button size="md" onClick={() => downloadExport(situation, plan, new Date())}>
        <DownloadIcon size={14} />
        Export plan
      </Button>

      <Button size="md" onClick={() => window.print()}>
        <PrinterIcon size={14} />
        Print plan
      </Button>

      <MenuButton label="More plan actions" items={moreActions} triggerClassName={MORE_TRIGGER}>
        More
        <ChevronDownIcon size={14} />
      </MenuButton>

      <input
        ref={importInputRef}
        type="file"
        className="sr-only"
        accept="application/json,.json"
        aria-label="Plan file to import"
        onChange={(event) => {
          handleFile(event.target.files?.[0]);
          event.target.value = '';
        }}
      />

      {importProblem ? (
        <p role="alert" className="w-full text-small text-blocking">
          {importProblem}
        </p>
      ) : null}

      <Dialog
        open={confirm === 'reset'}
        title="Reset plan"
        description="Every course you have placed in a planned term will be removed. Your details and your completed coursework stay as they are. This cannot be undone."
        onClose={() => setConfirm('none')}
        footer={
          <>
            <Button onClick={() => setConfirm('none')}>Keep my plan</Button>
            <Button
              variant="primary"
              onClick={() => {
                setConfirm('none');
                onResetPlan();
              }}
            >
              Reset plan
            </Button>
          </>
        }
      />

      <Dialog
        open={confirm === 'clear'}
        title="Clear all data"
        description="Your details, your completed coursework and your whole plan will be removed from this device, and you will go back to the start. Nothing is kept anywhere else, so this cannot be undone. Export your plan first if you want a copy."
        onClose={() => setConfirm('none')}
        footer={
          <>
            <Button onClick={() => setConfirm('none')}>Keep my data</Button>
            <Button
              variant="danger"
              onClick={() => {
                setConfirm('none');
                onClearAll();
              }}
            >
              Clear all data
            </Button>
          </>
        }
      />

      <Dialog
        open={confirm === 'overwrite'}
        title="Import plan"
        description="The plan you have now will be replaced by the one in this file, along with the details saved in it. This cannot be undone."
        onClose={() => {
          setConfirm('none');
          setPendingImport(null);
        }}
        footer={
          <>
            <Button
              onClick={() => {
                setConfirm('none');
                setPendingImport(null);
              }}
            >
              Keep my plan
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                if (pendingImport) onImport(pendingImport.situation, pendingImport.plan);
                setConfirm('none');
                setPendingImport(null);
              }}
            >
              Import plan
            </Button>
          </>
        }
      />
    </div>
  );
}
