import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import catalogue from '../src/data/catalogue/courses.json';
import { resetCatalogueCache } from '../src/data/catalogue';

/**
 * jsdom stops short of a few browser APIs the app uses. These are environment
 * shims for the test runner only — no failure switches, and nothing here is
 * reachable from production code.
 */
if (!('ResizeObserver' in globalThis)) {
  class TestResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(globalThis, 'ResizeObserver', { value: TestResizeObserver, writable: true });
}

if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
      onchange: null,
    }),
  });
}

Element.prototype.scrollIntoView = Element.prototype.scrollIntoView ?? (() => {});
window.print = window.print ?? (() => {});

// jsdom ships FileReader but not Blob#text. The app uses the standard method.
if (typeof Blob.prototype.text !== 'function') {
  Object.defineProperty(Blob.prototype, 'text', {
    writable: true,
    value(this: Blob) {
      return new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(reader.error ?? new Error('read failed'));
        reader.readAsText(this);
      });
    },
  });
}

beforeEach(() => {
  window.localStorage.clear();
  resetCatalogueCache();
  // The catalogue is the one thing this app fetches, and it is public course
  // data shipped with the build. Serving it here keeps the real code path.
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(catalogue),
      } as Response),
    ),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
