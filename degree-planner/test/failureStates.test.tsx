import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../src/App';
import { PlannerProvider } from '../src/state/PlannerProvider';
import { STORAGE_KEY } from '../src/state/persistence';

/**
 * The failure paths.
 *
 * Every rejection is reached by mocking the module, never by a failure switch
 * wired into production code.
 */
const analyze = vi.hoisted(() => vi.fn());
const parse = vi.hoisted(() => vi.fn());

vi.mock('../src/data/analyzePlan', () => ({ analyzePlan: analyze }));
vi.mock('../src/data/parseStarsReport', () => ({ parseStarsReport: parse }));

function renderApp() {
  return render(
    <PlannerProvider>
      <App />
    </PlannerProvider>,
  );
}

describe('failure states', () => {
  beforeEach(() => {
    analyze.mockReset();
    parse.mockReset();
  });

  it('shows the check’s error and keeps the plan usable when analyzePlan rejects', async () => {
    analyze.mockRejectedValue(new Error('The course requirements could not be loaded.'));
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByRole('button', { name: /try it with a sample student/i }));
    await user.click(await screen.findByRole('button', { name: /continue to my plan/i }));

    // The page is not blank: the plan is still there and still editable.
    expect(await screen.findByRole('heading', { name: /four-year plan/i })).toBeInTheDocument();
    expect(document.querySelector('[data-term-id="spring-2027"]')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Move or remove CSCI 485' })).toBeInTheDocument();

    const audit = screen.getByRole('complementary', { name: /your plan, checked/i });
    expect(within(audit).getByText(/we could not check this plan/i)).toBeInTheDocument();
    expect(within(audit).getByText(/course requirements could not be loaded/i)).toBeInTheDocument();
    expect(within(audit).getByRole('button', { name: /check again/i })).toBeInTheDocument();
  });

  it('offers a way out when the report cannot be read', async () => {
    parse.mockRejectedValue(new Error('unreadable'));
    const user = userEvent.setup();
    renderApp();

    const picker = await screen.findByLabelText(/stars report file/i);
    await user.upload(picker, new File(['not really a report'], 'report.pdf', { type: 'application/pdf' }));

    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText(/we could not read that report/i)).toBeInTheDocument();
    expect(within(alert).getByRole('button', { name: /enter my details/i })).toBeInTheDocument();
    expect(within(alert).getByRole('button', { name: /use the sample student/i })).toBeInTheDocument();

    // The way out works.
    await user.click(within(alert).getByRole('button', { name: /enter my details/i }));
    expect(
      await screen.findByRole('heading', { level: 1, name: /check your details/i }),
    ).toBeInTheDocument();
  });

  it('starts fresh with a notice when the saved copy is from an older version', async () => {
    analyze.mockResolvedValue({
      verdict: 'unknown',
      headline: 'Nothing to check yet.',
      units: { counted: 0, required: 128, unit: 'UNITS' },
      reusedFromReportDated: null,
      requirements: [],
      warnings: [],
      isSample: true,
    });
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ schemaVersion: 0, situation: null, plan: { schemaVersion: 1, terms: [] } }),
    );

    renderApp();

    expect(await screen.findByText(/could not reopen your last plan/i)).toBeInTheDocument();
    expect(
      await screen.findByRole('heading', { level: 1, name: /plan your next four years/i }),
    ).toBeInTheDocument();
  });

  it('names the problem when an imported file is not a plan', async () => {
    analyze.mockResolvedValue({
      verdict: 'unknown',
      headline: 'Nothing to check yet.',
      units: { counted: 0, required: 128, unit: 'UNITS' },
      reusedFromReportDated: null,
      requirements: [],
      warnings: [],
      isSample: true,
    });
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByRole('button', { name: /try it with a sample student/i }));
    await user.click(await screen.findByRole('button', { name: /continue to my plan/i }));
    await screen.findByRole('heading', { name: /four-year plan/i });

    const input = screen.getByLabelText(/plan file to import/i);
    await user.upload(input, new File(['{"schemaVersion":1,"kind":'], 'half.json', {
      type: 'application/json',
    }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/cut short/i);
  });
});
