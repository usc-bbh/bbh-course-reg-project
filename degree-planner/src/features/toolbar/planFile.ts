import type { Plan, PlanExportFile, StudentSituation } from '../../domain/types';
import { checkExportFile, type Checked } from '../../domain/validate';

/** `2026-09-11`, from a Date the caller supplies. Never used to judge a term. */
export function isoDate(now: Date): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * The exported file. No student name in the filename — files get shared, and a
 * name in a filename travels further than the file's contents do.
 */
export function exportFileName(now: Date): string {
  return `degree-plan-${isoDate(now)}.json`;
}

export function buildExport(
  situation: StudentSituation,
  plan: Plan,
  now: Date,
): PlanExportFile {
  return {
    schemaVersion: 1,
    kind: 'plansc.degree-planner.export',
    exportedOn: isoDate(now),
    situation,
    plan,
  };
}

/**
 * Hands the file to the browser's download machinery and immediately revokes
 * the object URL, so nothing derived from the student's data outlives the
 * click.
 */
export function downloadExport(situation: StudentSituation, plan: Plan, now: Date): void {
  const payload = JSON.stringify(buildExport(situation, plan, now), null, 2);
  const blob = new Blob([payload], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = exportFileName(now);
    anchor.rel = 'noopener';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

/** Reads and validates a file the student picked. Names the actual problem. */
export async function readImport(file: File): Promise<Checked<PlanExportFile>> {
  let text: string;
  try {
    text = await file.text();
  } catch {
    return { ok: false, problem: 'that file could not be opened' };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { ok: false, problem: 'that file is not complete JSON — it may have been cut short' };
  }
  return checkExportFile(parsed);
}
