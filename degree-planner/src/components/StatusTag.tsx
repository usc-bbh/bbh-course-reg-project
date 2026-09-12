import type { StatusPresentation } from './status';

/** Icon plus its text label. Never the icon alone, never the colour alone. */
export function StatusTag({
  presentation,
  className = '',
}: {
  presentation: StatusPresentation;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 text-micro ${presentation.tone} ${
        presentation.emphatic ? 'font-semibold' : 'font-medium'
      } ${className}`}
    >
      <span className="shrink-0">{presentation.icon}</span>
      {presentation.label}
    </span>
  );
}
