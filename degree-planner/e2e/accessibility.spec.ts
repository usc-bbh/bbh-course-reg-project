import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

/**
 * The accessibility rules a machine can check, on every screen the app has.
 *
 * Hand-written keyboard tests in planner.spec.ts cover the things axe cannot
 * see — focus order, focus restoration after a menu closes, whether the Move
 * to… menu is a real alternative to dragging. This covers the things a person
 * reading the code cannot reliably see: contrast ratios, names on controls,
 * ARIA that does not match its role, landmark structure.
 *
 * WCAG 2.1 A and AA, which is what USC's own accessibility policy asks for.
 */
const STANDARD = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

async function scan(page: Page) {
  return new AxeBuilder({ page }).withTags(STANDARD).analyze();
}

/** Reports the rule and the element, so a failure says what to fix. */
function describeViolations(results: Awaited<ReturnType<typeof scan>>): string {
  return results.violations
    .map((violation) => {
      const where = violation.nodes.map((node) => node.target.join(' ')).join(', ');
      return `${violation.id} (${violation.impact}): ${violation.help} — ${where}`;
    })
    .join('\n');
}

async function toWorkspace(page: Page) {
  await page.getByRole('button', { name: /try it with a sample student/i }).click();
  await page.getByRole('button', { name: /continue to my plan/i }).click();
  await page.getByRole('heading', { name: /four-year plan/i }).waitFor();
}

test.describe('accessibility', () => {
  test('the empty state has no violations', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('heading', { level: 1, name: /plan your next four years/i }).waitFor();
    const results = await scan(page);
    expect(describeViolations(results), describeViolations(results)).toBe('');
  });

  test('the review form has no violations', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /try it with a sample student/i }).click();
    await page.getByRole('heading', { level: 1, name: /check your details/i }).waitFor();
    const results = await scan(page);
    expect(describeViolations(results), describeViolations(results)).toBe('');
  });

  test('the plan workspace has no violations', async ({ page }) => {
    await page.goto('/');
    await toWorkspace(page);
    const results = await scan(page);
    expect(describeViolations(results), describeViolations(results)).toBe('');
  });

  test('the course picker has no violations while open', async ({ page }) => {
    await page.goto('/');
    await toWorkspace(page);
    await page.getByRole('button', { name: 'Add a course to Spring 2027' }).click();
    await page.getByRole('combobox', { name: /search for a course/i }).fill('csci');
    await page.getByRole('option').first().waitFor();
    const results = await scan(page);
    expect(describeViolations(results), describeViolations(results)).toBe('');
  });

  test('the clear-all dialog has no violations', async ({ page }) => {
    await page.goto('/');
    await toWorkspace(page);
    await page.getByRole('button', { name: /more plan actions/i }).click();
    await page.getByRole('menuitem', { name: /clear all data/i }).click();
    await page.getByRole('dialog', { name: /clear all data/i }).waitFor();
    const results = await scan(page);
    expect(describeViolations(results), describeViolations(results)).toBe('');
  });

  test('the audit sheet has no violations at phone width', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/');
    await toWorkspace(page);
    await page.getByRole('button', { name: /show details/i }).click();
    await page.getByRole('dialog', { name: /your plan, checked/i }).waitFor();
    const results = await scan(page);
    expect(describeViolations(results), describeViolations(results)).toBe('');
  });
});
