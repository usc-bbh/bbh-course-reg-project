import { existsSync } from 'node:fs';
import { defineConfig, devices } from '@playwright/test';

const CANDIDATES = [
  process.env.PLAYWRIGHT_CHROMIUM_PATH,
  '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
].filter((path): path is string => Boolean(path));

const CHROMIUM = CANDIDATES.find((path) => existsSync(path));

/**
 * End-to-end checks run against the production build, not the dev server, so
 * the console assertions cover what a student would actually load.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    ...devices['Desktop Chrome'],
    // Use the Chromium already on the machine rather than downloading one.
    // Set PLAYWRIGHT_CHROMIUM_PATH if yours lives somewhere else; leave it
    // unset and Playwright falls back to its own managed browser.
    launchOptions: CHROMIUM ? { executablePath: CHROMIUM } : {},
  },
  webServer: {
    command: 'npm run preview -- --port 4173 --strictPort',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
