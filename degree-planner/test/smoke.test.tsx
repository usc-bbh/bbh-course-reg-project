import { describe, expect, it } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../src/App';
import { PlannerProvider } from '../src/state/PlannerProvider';

function renderApp() {
  return render(
    <PlannerProvider>
      <App />
    </PlannerProvider>,
  );
}

function term(id: string): HTMLElement {
  const element = document.querySelector<HTMLElement>(`[data-term-id="${id}"]`);
  if (!element) throw new Error(`No term card for ${id}`);
  return element;
}

/**
 * The end-to-end flow, by keyboard-reachable controls only: sample student,
 * plan renders with the past locked, move a course with the Move to… menu, the
 * audit shows the verdict with its reasons, the plan survives a reload, and
 * Clear all data returns the empty state.
 */
describe('the whole flow', () => {
  it('goes from the sample student to a checked, saved, clearable plan', async () => {
    const user = userEvent.setup();
    const view = renderApp();

    // ── Empty state ──────────────────────────────────────────────────────
    expect(
      await screen.findByRole('heading', { level: 1, name: /plan your next four years/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /try it with a sample student/i }));

    // ── Review step ──────────────────────────────────────────────────────
    expect(
      await screen.findByRole('heading', { level: 1, name: /check your details/i }),
    ).toBeInTheDocument();
    expect(await screen.findByDisplayValue('Robin Samplewood')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /continue to my plan/i }));

    // ── Plan, with the past locked ───────────────────────────────────────
    expect(await screen.findByRole('heading', { name: /four-year plan/i })).toBeInTheDocument();

    const completedTerm = term('fall-2024');
    expect(within(completedTerm).getByText('Completed')).toBeInTheDocument();
    expect(within(completedTerm).getByText('CSCI 103L')).toBeInTheDocument();
    // Locked coursework offers no move, no remove and no drag handle.
    expect(within(completedTerm).queryByRole('button', { name: /move or remove/i })).toBeNull();

    const inProgressTerm = term('fall-2026');
    expect(within(inProgressTerm).getByText('In progress')).toBeInTheDocument();

    expect(within(term('spring-2027')).getByText('CSCI 353')).toBeInTheDocument();

    // ── Move a course with the Move to… menu ─────────────────────────────
    await user.click(screen.getByRole('button', { name: 'Move or remove CSCI 353' }));
    await user.click(await screen.findByRole('menuitem', { name: 'Move to Fall 2027' }));

    await waitFor(() => {
      expect(within(term('fall-2027')).getByText('CSCI 353')).toBeInTheDocument();
    });
    expect(within(term('spring-2027')).queryByText('CSCI 353')).toBeNull();

    // ── The audit ────────────────────────────────────────────────────────
    const audit = screen.getByRole('complementary', { name: /your plan, checked/i });
    expect(within(audit).getByText('Not yet')).toBeInTheDocument();
    expect(within(audit).getByText(/does not reach the degree yet/i)).toBeInTheDocument();
    expect(within(audit).getByText('Core electives')).toBeInTheDocument();
    expect(
      within(audit).getByText(/Four 300- or 400-level CSCI courses are required/i),
    ).toBeInTheDocument();
    expect(within(audit).getByText(/CSCI 401 is offered in the fall only/i)).toBeInTheDocument();
    expect(within(audit).getByText(/Sample results\./i)).toBeInTheDocument();

    // ── Reload: the plan is still there ──────────────────────────────────
    // Wait for the move itself to reach storage, not just for any earlier save.
    await waitFor(
      () => {
        const raw = window.localStorage.getItem('plansc.degreePlanner.v1');
        expect(raw).toBeTruthy();
        const saved = JSON.parse(raw ?? '{}') as {
          plan: { terms: Array<{ id: string; courses: Array<{ code: string }> }> };
        };
        const moved = saved.plan.terms.find((entry) => entry.id === 'fall-2027');
        expect(moved?.courses.some((course) => course.code === 'CSCI 353')).toBe(true);
      },
      { timeout: 3000 },
    );
    expect(screen.getByTestId('save-status')).toHaveTextContent('Saved on this device.');

    view.unmount();
    renderApp();

    await waitFor(() => {
      expect(within(term('fall-2027')).getByText('CSCI 353')).toBeInTheDocument();
    });

    // ── Clear all data ───────────────────────────────────────────────────
    await user.click(screen.getByRole('button', { name: /more plan actions/i }));
    await user.click(await screen.findByRole('menuitem', { name: /clear all data/i }));
    const dialog = await screen.findByRole('dialog', { name: /clear all data/i });
    await user.click(within(dialog).getByRole('button', { name: /clear all data/i }));

    expect(
      await screen.findByRole('heading', { level: 1, name: /plan your next four years/i }),
    ).toBeInTheDocument();
    expect(document.querySelector('[data-term-id="fall-2027"]')).toBeNull();
  });

  it('removes a course with an undo that the keyboard can reach', async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByRole('button', { name: /try it with a sample student/i }));
    await user.click(await screen.findByRole('button', { name: /continue to my plan/i }));
    await screen.findByRole('heading', { name: /four-year plan/i });

    await user.click(screen.getByRole('button', { name: 'Move or remove CSCI 420' }));
    await user.click(await screen.findByRole('menuitem', { name: 'Remove from plan' }));

    expect(within(term('spring-2028')).queryByText('CSCI 420')).toBeNull();

    const undo = await screen.findByRole('button', { name: /undo/i });
    // Focus lands on Undo, so it is reachable without a mouse.
    expect(undo).toHaveFocus();

    await user.keyboard('{Enter}');
    await waitFor(() => {
      expect(within(term('spring-2028')).getByText('CSCI 420')).toBeInTheDocument();
    });
  });

  it('adds a course through the keyboard-driven picker', async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByRole('button', { name: /try it with a sample student/i }));
    await user.click(await screen.findByRole('button', { name: /continue to my plan/i }));
    await screen.findByRole('heading', { name: /four-year plan/i });

    await user.click(screen.getByRole('button', { name: 'Add a course to Spring 2027' }));

    const combobox = await screen.findByRole('combobox', {
      name: /search for a course to add to spring 2027/i,
    });
    expect(combobox).toHaveFocus();

    await user.type(combobox, 'CSCI 485');
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /CSCI 485/i })).toBeInTheDocument();
    });
    await user.keyboard('{Enter}');

    // Escape closes the picker and hands focus back to the trigger.
    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Add a course to Spring 2027' })).toHaveFocus();
    });

    expect(within(term('spring-2027')).getByText('CSCI 485')).toBeInTheDocument();
  });

  it('clears the cross-highlight with Escape', async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByRole('button', { name: /try it with a sample student/i }));
    await user.click(await screen.findByRole('button', { name: /continue to my plan/i }));
    await screen.findByRole('heading', { name: /four-year plan/i });

    const audit = screen.getByRole('complementary', { name: /your plan, checked/i });
    const requirement = within(audit).getByRole('button', { name: /core electives/i });
    await user.click(requirement);
    expect(requirement).toHaveAttribute('aria-pressed', 'true');

    await waitFor(() => {
      expect(document.querySelector('[data-course-key="fall-2027::CSCI 402"]')).toHaveClass(
        'is-highlighted',
      );
    });

    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(
        within(screen.getByRole('complementary', { name: /your plan, checked/i })).getByRole(
          'button',
          { name: /core electives/i },
        ),
      ).toHaveAttribute('aria-pressed', 'false');
    });
  });
});
