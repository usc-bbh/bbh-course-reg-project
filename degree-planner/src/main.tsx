import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

// USC's registration pages set their wordmark and the university lockup in a
// Caslon; Libre Caslon Text is the open face that matches it. Source Sans 3 is
// the interface face, Source Code Pro carries course codes and unit counts.
//
// All three are vendored into the bundle by @fontsource. Nothing is fetched
// from a font CDN at runtime — see the Content-Security-Policy in index.html.
import '@fontsource/libre-caslon-text/400.css';
import '@fontsource/libre-caslon-text/700.css';
import '@fontsource/source-sans-3/400.css';
import '@fontsource/source-sans-3/500.css';
import '@fontsource/source-sans-3/600.css';
import '@fontsource/source-sans-3/700.css';
import '@fontsource/source-code-pro/400.css';
import '@fontsource/source-code-pro/500.css';

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
