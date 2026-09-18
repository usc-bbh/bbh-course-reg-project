import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Static front end only: `vite build` emits a plain `dist/` directory of HTML,
// JS, CSS and font files. There is no server half to this app, so the same
// output deploys unchanged to Vercel, Netlify, or any static host.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Relative asset URLs so the build also works from a sub-path or file://.
  base: './',
  build: {
    outDir: 'dist',
    // No inlined bootstrap script, so the page needs no script-src 'unsafe-inline'.
    modulePreload: { polyfill: false },
    assetsInlineLimit: 0,
  },
});
