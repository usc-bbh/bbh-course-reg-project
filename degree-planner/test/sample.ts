import { situationFromReport } from '../src/domain/situation';
import { sampleStarsReport } from '../src/data/sampleStudent';
import type { StudentSituation } from '../src/domain/types';

/** The sample student as the app holds them, for tests that need a situation. */
export function sampleSituation(overrides: Partial<StudentSituation> = {}): StudentSituation {
  return { ...situationFromReport(sampleStarsReport, 'Robin Samplewood'), ...overrides };
}
