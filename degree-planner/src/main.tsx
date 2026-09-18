import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

// USC's registration pages set their wordmark and the university lockup in a
// Caslon; Libre Caslon Text is the open face that matches it. Source Sans 3 is
// the interface face, Source Code Pro carries course codes and unit counts.
//
// All three are vendored into the bundle by @fontsource. Nothing is fetched
// from a font CDN at runtime — see the Content-Security-Policy in index.html.
// Latin and Latin Extended only. The full @fontsource entry points also ship
// Cyrillic, Greek and Vietnamese, which tripled the number of font files in the
// build for coverage a USC course planner never reaches.
import '@fontsource/libre-caslon-text/latin-400.css';
import '@fontsource/libre-caslon-text/latin-ext-400.css';
import '@fontsource/libre-caslon-text/latin-700.css';
import '@fontsource/libre-caslon-text/latin-ext-700.css';
import '@fontsource/source-sans-3/latin-400.css';
import '@fontsource/source-sans-3/latin-ext-400.css';
import '@fontsource/source-sans-3/latin-500.css';
import '@fontsource/source-sans-3/latin-ext-500.css';
import '@fontsource/source-sans-3/latin-600.css';
import '@fontsource/source-sans-3/latin-ext-600.css';
import '@fontsource/source-sans-3/latin-700.css';
import '@fontsource/source-sans-3/latin-ext-700.css';
import '@fontsource/source-code-pro/latin-400.css';
import '@fontsource/source-code-pro/latin-ext-400.css';
import '@fontsource/source-code-pro/latin-500.css';
import '@fontsource/source-code-pro/latin-ext-500.css';

import './styles/index.css';
import { App } from './App';
import { PlannerProvider } from './state/PlannerProvider';

const container = document.getElementById('root');
if (!container) throw new Error('The page is missing its root element.');

createRoot(container).render(
  <StrictMode>
    <PlannerProvider>
      <App />
    </PlannerProvider>
  </StrictMode>,
);
