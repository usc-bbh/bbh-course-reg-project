import type { AnalysisResult } from '../../domain/types';

/** How many requirements the result marked unsatisfied. A count, not a ruling. */
export function unmetCount(result: AnalysisResult): number {
  return result.requirements.filter((requirement) => requirement.status === 'unsatisfied').length;
}
