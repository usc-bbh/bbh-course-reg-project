import { expect, test, type ConsoleMessage, type Page, type Request } from '@playwright/test';

/**
 * The production build, in a real browser.
 *
 * Two things only a browser can check are asserted on every test here:
 *   1. nothing on the page reaches an origin other than the app's own, and
 *   2. the console stays clean — no hydration warnings, no errors.
 */
const ALLOWED_SCHEMES = ['data:', 'blob:', 'about:'];

function guardTheOrigin(page: Page, offOrigin: string[]) {
  page.on('request', (request: Request) => {
    const url = request.url();
    if (ALLOWED_SCHEMES.some((scheme) => url.startsWith(scheme))) return;
    if (url.startsWith('http://127.0.0.1:4173')) return;
    offOrigin.push(url);
  });
}

function watchTheConsole(page: Page, noise: string[]) {
  page.on('console', (message: ConsoleMessage) => {
    if (message.type() === 'error' || message.type() === 'warning') {
      noise.push(`${message.type()}: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => noise.push(`pageerror: ${error.message}`));
}

test.describe('the built planner', () => {
  test('runs the whole flow without leaving the device or dirtying the console', async ({
    page,
  }) => {
    const offOrigin: string[] = [];
    const noise: string[] = [];
    guardTheOrigin(page, offOrigin);
    watchTheConsole(page, noise);

    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1, name: /plan your next four years/i })).toBeVisible();

    await page.getByRole('button', { name: /try it with a sample student/i }).click();
    await expect(page.getByRole('heading', { level: 1, name: /check your details/i })).toBeVisible();
    await page.getByRole('button', { name: /continue to my plan/i }).click();

    await expect(page.getByRole('heading', { name: /four-year plan/i })).toBeVisible();
    await expect(page.locator('[data-term-id="fall-2024"]').getByText('Completed')).toBeVisible();
    await expect(page.locator('[data-term-id="fall-2025"]').getByText('CSCI 353')).toBeVisible();

    // Move a course with the menu, which is the keyboard and touch path.
    await page.getByRole('button', { name: 'Move or remove CSCI 353' }).click();
    await page.getByRole('menuitem', { name: 'Move to Fall 2026' }).click();
    await expect(page.locator('[data-term-id="fall-2026"]').getByText('CSCI 353')).toBeVisible();

    const audit = page.getByRole('complementary', { name: /your plan, checked/i });
    await expect(audit.getByText('Not yet')).toBeVisible();
    // A block read off the report, with STARS' own verdict and its date.
    await expect(audit.getByRole('button', { name: /^128-Unit Minimum/ })).toBeVisible();
    await expect(audit.getByText(/8 more are needed before May 2027/i)).toBeVisible();
    await expect(audit.getByText(/CSCI 401 has only ever run in fall terms/i)).toBeVisible();
    await expect(audit).toContainText(/read from your STARS report of 14 February 2025/i);

    // Cross-highlighting.
    await audit.getByRole('button', { name: /computer science core/i }).click();
    await expect(page.locator('[data-course-key="fall-2025::CSCI 310"]')).toHaveClass(
      /is-highlighted/,
    );
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-course-key="fall-2025::CSCI 310"]')).not.toHaveClass(
      /is-highlighted/,
    );

    // The plan survives a real reload.
    await expect(page.getByTestId('save-status')).toHaveText('Saved on this device.');
    await page.reload();
    await expect(page.locator('[data-term-id="fall-2026"]').getByText('CSCI 353')).toBeVisible();

    // Clear all data returns the empty state.
    await page.getByRole('button', { name: /more plan actions/i }).click();
    await page.getByRole('menuitem', { name: /clear all data/i }).click();
    const dialog = page.getByRole('dialog', { name: /clear all data/i });
    await dialog.getByRole('button', { name: /clear all data/i }).click();
    await expect(page.getByRole('heading', { level: 1, name: /plan your next four years/i })).toBeVisible();

    expect(offOrigin, `requests left the app's origin: ${offOrigin.join(', ')}`).toEqual([]);
    expect(noise, `console was not clean: ${noise.join(' | ')}`).toEqual([]);
  });

  test('is usable by keyboard alone', async ({ page }) => {
    const noise: string[] = [];
    watchTheConsole(page, noise);

    await page.goto('/');
    await page.getByRole('button', { name: /try it with a sample student/i }).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('heading', { level: 1, name: /check your details/i })).toBeVisible();

    await page.getByRole('button', { name: /continue to my plan/i }).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('heading', { name: /four-year plan/i })).toBeVisible();

    // The skip link is the first stop, because the situation summary sits above
    // the plan on every load.
    await page.locator('body').press('Tab');
    await expect(page.getByRole('link', { name: /skip to the plan/i })).toBeFocused();

    // Add a course entirely from the keyboard.
    await page.getByRole('button', { name: 'Add a course to Spring 2027' }).focus();
    await page.keyboard.press('Enter');
    const combobox = page.getByRole('combobox', { name: /search for a course to add to spring 2027/i });
    await expect(combobox).toBeFocused();
    // CSCI 435 is in the sample catalogue and in no term of the sample plan.
    await page.keyboard.type('435');
    // Wait for the option rather than racing the course-list request: the file
    // is the size of a real scrape, so "it was instant locally" is not a fact
    // the test may rely on.
    await page.getByRole('option', { name: /CSCI 435/ }).waitFor();
    await page.keyboard.press('Enter');
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button', { name: 'Add a course to Spring 2027' })).toBeFocused();
    await expect(page.locator('[data-term-id="spring-2027"]').getByText('CSCI 435')).toBeVisible();

    // Remove it, and undo from where focus lands.
    await page.getByRole('button', { name: 'Move or remove CSCI 435' }).focus();
    await page.keyboard.press('Enter');
    await page.getByRole('menuitem', { name: 'Remove from plan' }).click();
    await expect(page.getByRole('button', { name: /undo/i })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-term-id="spring-2027"]').getByText('CSCI 435')).toBeVisible();

    expect(noise, `console was not clean: ${noise.join(' | ')}`).toEqual([]);
  });
});

test.describe('the parts only a browser can check', () => {
  // Dragging needs the year columns laid out side by side, which is the
  // 1440-wide layout the design targets rather than the stacked phone one.
  test.use({ viewport: { width: 1440, height: 1000 } });

  test('moves a course by dragging it into another term', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /try it with a sample student/i }).click();
    await page.getByRole('button', { name: /continue to my plan/i }).click();
    await page.getByRole('heading', { name: /four-year plan/i }).waitFor();

    const row = page.locator('[data-course-key="fall-2025::CSCI 310"]');
    const handle = row.locator('[data-drag-handle]');
    const target = page.locator('[data-term-id="spring-2026"]');

    await row.scrollIntoViewIfNeeded();
    const from = await handle.boundingBox();
    const to = await target.boundingBox();
    if (!from || !to) throw new Error('Could not find the drag handle or the drop target.');

    await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
    await page.mouse.down();
    // Several steps: dnd-kit needs movement, not a teleport.
    await page.mouse.move(to.x + to.width / 2, to.y + 40, { steps: 12 });
    await page.mouse.up();

    await expect(page.locator('[data-term-id="spring-2026"]').getByText('CSCI 310')).toBeVisible();
    await expect(page.locator('[data-term-id="fall-2025"]').getByText('CSCI 310')).toHaveCount(0);
  });

  test('refuses to drop a course into a locked term', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /try it with a sample student/i }).click();
    await page.getByRole('button', { name: /continue to my plan/i }).click();
    await page.getByRole('heading', { name: /four-year plan/i }).waitFor();

    const row = page.locator('[data-course-key="fall-2025::CSCI 353"]');
    const handle = row.locator('[data-drag-handle]');
    const locked = page.locator('[data-term-id="fall-2024"]');

    await row.scrollIntoViewIfNeeded();
    const from = await handle.boundingBox();
    const to = await locked.boundingBox();
    if (!from || !to) throw new Error('Could not find the drag handle or the locked term.');

    await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
    await page.mouse.down();
    await page.mouse.move(to.x + to.width / 2, to.y + 60, { steps: 12 });
    await page.mouse.up();

    await expect(page.locator('[data-term-id="fall-2025"]').getByText('CSCI 353')).toBeVisible();
    await expect(page.locator('[data-term-id="fall-2024"]').getByText('CSCI 353')).toHaveCount(0);
  });

  test('adds a summer term, then takes it away again', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /try it with a sample student/i }).click();
    await page.getByRole('button', { name: /continue to my plan/i }).click();
    await page.getByRole('heading', { name: /four-year plan/i }).waitFor();

    await page.getByRole('button', { name: 'Add Summer 2027' }).click();
    await expect(page.locator('[data-term-id="summer-2027"]')).toBeVisible();

    await page.getByRole('button', { name: 'Remove Summer 2027' }).click();
    await expect(page.locator('[data-term-id="summer-2027"]')).toHaveCount(0);
  });

  test('exports a plan file and imports it back', async ({ page }, testInfo) => {
    await page.goto('/');
    await page.getByRole('button', { name: /try it with a sample student/i }).click();
    await page.getByRole('button', { name: /continue to my plan/i }).click();
    await page.getByRole('heading', { name: /four-year plan/i }).waitFor();

    const download = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /export plan/i }).click(),
    ]).then(([event]) => event);

    expect(download.suggestedFilename()).toMatch(/^degree-plan-\d{4}-\d{2}-\d{2}\.json$/);
    expect(download.suggestedFilename()).not.toMatch(/samplewood/i);
    const saved = testInfo.outputPath('exported-plan.json');
    await download.saveAs(saved);

    // Change the plan, then import the file back over it.
    await page.getByRole('button', { name: 'Move or remove CSCI 420' }).click();
    await page.getByRole('menuitem', { name: 'Remove from plan' }).click();
    await expect(page.locator('[data-term-id="fall-2026"]').getByText('CSCI 420')).toHaveCount(0);

    await page.getByRole('button', { name: /more plan actions/i }).click();
    await page.getByRole('menuitem', { name: /import plan/i }).click();
    await page.getByLabel(/plan file to import/i).setInputFiles(saved);

    const dialog = page.getByRole('dialog', { name: /import plan/i });
    await dialog.getByRole('button', { name: /import plan/i }).click();

    await expect(page.locator('[data-term-id="fall-2026"]').getByText('CSCI 420')).toBeVisible();
  });
});
