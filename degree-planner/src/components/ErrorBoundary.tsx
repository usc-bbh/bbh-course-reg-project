import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button } from './Button';

interface Props {
  /** Named in the fallback: "The plan couldn't be shown." */
  area: string;
  children: ReactNode;
}

interface State {
  failed: boolean;
}

/**
 * One boundary per major panel, so a failure in the audit never blanks the plan
 * and vice versa.
 *
 * Nothing about the error is logged. A student's situation can travel inside an
 * error message, and browser consoles get screen-shared and pasted into
 * tickets.
 */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  override componentDidCatch(_error: Error, _info: ErrorInfo): void {
    void _error;
    void _info;
  }

  private retry = () => this.setState({ failed: false });

  override render(): ReactNode {
    if (!this.state.failed) return this.props.children;
    return (
      <div
        role="alert"
        className="rounded-card border border-line bg-surface p-5 text-[13.5px] text-ink-2"
      >
        <p className="mb-1 font-semibold text-ink">{this.props.area} could not be shown.</p>
        <p className="mb-3">
          The rest of the page is unaffected. Try again, and if it keeps happening, export your plan
          so you do not lose it.
        </p>
        <Button onClick={this.retry}>Try again</Button>
      </div>
    );
  }
}
