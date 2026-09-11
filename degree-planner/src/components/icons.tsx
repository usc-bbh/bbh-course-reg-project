import type { SVGProps } from 'react';

/**
 * Status is never carried by colour alone. Every status in this app pairs an
 * icon with a text label, and the icon shapes differ from each other so they
 * still read in greyscale or at small sizes.
 *
 * Icons are decoration: each one is aria-hidden, and the control or row around
 * it carries the accessible name.
 */

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Svg({ size = 16, children, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

/** Satisfied: a filled disc with a check cut through it. */
export function CheckCircleIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="6.6" fill="currentColor" stroke="none" />
      <path d="M5 8.2 7.1 10.3 11 6.1" stroke="#fff" strokeWidth={1.8} />
    </Svg>
  );
}

/** In progress: a half-filled disc. Reads as "part way" without a label. */
export function HalfCircleIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="6.6" />
      <path d="M8 1.4a6.6 6.6 0 0 1 0 13.2z" fill="currentColor" stroke="none" />
    </Svg>
  );
}

/** Unsatisfied: a filled square. Deliberately the heaviest shape here. */
export function FilledSquareIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="2" y="2" width="12" height="12" rx="2.5" fill="currentColor" stroke="none" />
      <path d="M8 4.8v4.4" stroke="#fff" strokeWidth={1.9} />
      <circle cx="8" cy="11.4" r="0.95" fill="#fff" stroke="none" />
    </Svg>
  );
}

/** Warning: a triangle. */
export function TriangleIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 2.2 14.6 13.4H1.4z" />
      <path d="M8 6.5v3.1" />
      <circle cx="8" cy="11.5" r="0.85" fill="currentColor" stroke="none" />
    </Svg>
  );
}

/** Blocking: a filled octagon. The only status shape that is filled and edged. */
export function OctagonIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path
        d="M5.4 1.6h5.2l3.8 3.8v5.2l-3.8 3.8H5.4l-3.8-3.8V5.4z"
        fill="currentColor"
        stroke="none"
      />
      <path d="M8 4.6v4.2" stroke="#fff" strokeWidth={1.9} />
      <circle cx="8" cy="11.2" r="0.95" fill="#fff" stroke="none" />
    </Svg>
  );
}

/** Info: an outlined circle with an i. */
export function InfoIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="6.6" />
      <path d="M8 7.2v4" />
      <circle cx="8" cy="4.8" r="0.85" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function LockIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3.2" y="7" width="9.6" height="7" rx="1.8" />
      <path d="M5.6 7V5.2a2.4 2.4 0 0 1 4.8 0V7" />
    </Svg>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 3.2v9.6M3.2 8h9.6" />
    </Svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 4l8 8M12 4l-8 8" />
    </Svg>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3.8 6 8 10.2 12.2 6" />
    </Svg>
  );
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 3.8 10.2 8 6 12.2" />
    </Svg>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="7.2" cy="7.2" r="4.6" />
      <path d="M10.6 10.6 13.6 13.6" />
    </Svg>
  );
}

export function DragHandleIcon(props: IconProps) {
  return (
    <Svg {...props} strokeWidth={1.3}>
      <circle cx="6" cy="4" r="1.05" fill="currentColor" stroke="none" />
      <circle cx="10" cy="4" r="1.05" fill="currentColor" stroke="none" />
      <circle cx="6" cy="8" r="1.05" fill="currentColor" stroke="none" />
      <circle cx="10" cy="8" r="1.05" fill="currentColor" stroke="none" />
      <circle cx="6" cy="12" r="1.05" fill="currentColor" stroke="none" />
      <circle cx="10" cy="12" r="1.05" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function MoreIcon(props: IconProps) {
  return (
    <Svg {...props} strokeWidth={1.3}>
      <circle cx="3.4" cy="8" r="1.15" fill="currentColor" stroke="none" />
      <circle cx="8" cy="8" r="1.15" fill="currentColor" stroke="none" />
      <circle cx="12.6" cy="8" r="1.15" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function PrinterIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4.4 6.2V2.4h7.2v3.8" />
      <rect x="2" y="6.2" width="12" height="5" rx="1.4" />
      <path d="M4.4 9.6h7.2v4H4.4z" />
    </Svg>
  );
}

export function DownloadIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 2.4v7.4M4.8 7.2 8 10.4l3.2-3.2" />
      <path d="M2.6 12.2v1.2h10.8v-1.2" />
    </Svg>
  );
}

export function UploadIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 10.8V3.4M4.8 6.6 8 3.4l3.2 3.2" />
      <path d="M2.6 12.2v1.2h10.8v-1.2" />
    </Svg>
  );
}

export function UndoIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 7.4h6.6a3.4 3.4 0 1 1 0 6.8H6.2" />
      <path d="M5.6 4.6 2.8 7.4l2.8 2.8" />
    </Svg>
  );
}

export function TrashIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2.8 4.4h10.4M6.2 4.4V2.9h3.6v1.5" />
      <path d="M4.2 4.4l.7 8.4h6.2l.7-8.4" />
    </Svg>
  );
}

export function PencilIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M11.1 2.6 13.4 4.9 5.6 12.7 2.6 13.4l.7-3z" />
    </Svg>
  );
}

export function FileIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M9 1.8H4.6a1.6 1.6 0 0 0-1.6 1.6v9.2a1.6 1.6 0 0 0 1.6 1.6h6.8a1.6 1.6 0 0 0 1.6-1.6V5.6z" />
      <path d="M9 1.8v3.8h4" />
    </Svg>
  );
}
