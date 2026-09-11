import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

// Fonts are vendored into the bundle by @fontsource. Nothing is fetched from a
// font CDN at runtime — see the Content-Security-Policy in index.html.
import '@fontsource/dm-sans/400.css';
import '@fontsource/dm-sans/500.css';
import '@fontsource/dm-sans/600.css';
import '@fontsource/dm-sans/700.css';
import '@fontsource/dm-mono/400.css';
import '@fontsource/dm-mono/500.css';

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
