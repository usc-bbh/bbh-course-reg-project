import type { ReactNode } from 'react';
import type { RequirementStatus, WarningSeverity } from '../domain/types';
import {
  CheckCircleIcon,
  FilledSquareIcon,
  HalfCircleIcon,
  InfoIcon,
  OctagonIcon,
  TriangleIcon,
} from './icons';

/**
 * The status system, in one place.
 *
 * Brand and status are separate systems here. Cardinal is the brand and the
 * primary-action colour, so it cannot also mean "unsatisfied"; gold is brand
 * too, so it cannot mean "warning".
 *
 * That leaves no red for "unsatisfied", which is the interesting constraint.
 * Rather than invent a second red beside cardinal, unsatisfied carries its
 * weight through typography and shape: full-strength ink, a bold label, and the
 * heaviest icon in the set. It ends up the most prominent row in the panel
 * without competing with the brand — which is what we wanted anyway, since
 * unmet requirements are the thing a student came to see.
 *
 * Satisfied, in-progress and warning hues are the validator GUI's own values.
 */

export interface StatusPresentation {
  label: string;
  icon: ReactNode;
  /** Text colour class for the icon and label. */
  tone: string;
  /** Row background and rule, used sparingly. */
  surface: string;
  /** True for the one status that is set in bold. */
  emphatic: boolean;
}

export function requirementPresentation(status: RequirementStatus): StatusPresentation {
  switch (status) {
    case 'satisfied':
      return {
        label: 'Satisfied',
        icon: <CheckCircleIcon />,
        tone: 'text-satisfied',
        surface: 'bg-surface border-line',
        emphatic: false,
      };
    case 'in-progress':
      return {
        label: 'In progress',
        icon: <HalfCircleIcon />,
        tone: 'text-inprogress',
        surface: 'bg-surface border-line',
        emphatic: false,
      };
    case 'unsatisfied':
      return {
        label: 'Not met',
        icon: <FilledSquareIcon />,
        tone: 'text-unsatisfied',
        surface: 'bg-unsatisfied-wash border-ink-5',
        emphatic: true,
      };
  }
}

export function warningPresentation(severity: WarningSeverity): StatusPresentation {
  switch (severity) {
    case 'blocking':
      return {
        label: 'Blocking',
        icon: <OctagonIcon />,
        tone: 'text-blocking',
        surface: 'bg-blocking-wash border-l-[3px] border-l-blocking border-warning-line',
        emphatic: true,
      };
    case 'warning':
      return {
        label: 'Warning',
        icon: <TriangleIcon />,
        tone: 'text-warning',
        surface: 'bg-warning-wash border-warning-line',
        emphatic: false,
      };
    case 'info':
      return {
        label: 'Note',
        icon: <InfoIcon />,
        tone: 'text-inprogress',
        surface: 'bg-inprogress-wash border-inprogress-line',
        emphatic: false,
      };
  }
}
