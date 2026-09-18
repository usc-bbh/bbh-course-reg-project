import { useCallback, useEffect, useState } from 'react';
import type { Catalogue } from '../domain/types';
import { loadCatalogue } from './catalogue';

export type CatalogueState =
  | { status: 'pending' }
  | { status: 'ready'; catalogue: Catalogue }
  | { status: 'failed'; message: string };

/**
 * Loads the public course list once per page. Kept as a real async load so the
 * pending and failed states are exercised, not imagined — see catalogue.ts.
 */
export function useCatalogue(): { state: CatalogueState; retry: () => void } {
  const [state, setState] = useState<CatalogueState>({ status: 'pending' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    loadCatalogue()
      .then((catalogue) => {
        if (!cancelled) setState({ status: 'ready', catalogue });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState({
          status: 'failed',
          message:
            error instanceof Error && error.message
              ? error.message
              : 'The course list could not be loaded.',
        });
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  // Resetting to pending happens here, in the click handler, rather than at the
  // top of the effect: an effect body that calls setState synchronously causes
  // a cascading render.
  const retry = useCallback(() => {
    setState({ status: 'pending' });
    setAttempt((value) => value + 1);
  }, []);
  return { state, retry };
}
