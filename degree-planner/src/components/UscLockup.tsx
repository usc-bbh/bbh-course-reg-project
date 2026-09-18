/**
 * The university lockup in the header: the shield-and-torch emblem beside the
 * name, set the way USC's own registration pages set it — "USC" in gold, then
 * "University of / Southern California" in white, all in the Caslon.
 *
 * The emblem is drawn here as inline SVG rather than loaded as an image file,
 * for two reasons: the app is not allowed to request anything from another
 * origin, and an inline mark stays crisp at any size and takes its colour from
 * the header it sits on. If the team later adds the official artwork from USC's
 * brand portal, swap the <UscShield> body for it and nothing else changes.
 *
 * Sizes here are in rem rather than on the interface type scale on purpose: a
 * lockup has fixed internal proportions and is not body copy.
 */

// GAP(other): the shield is drawn here from the lockup on USC's own
// registration pages, because the official artwork is not in this repo and the
// app may not fetch it from another origin. Someone with access to the brand
// portal should drop the real file in and replace <UscShield>.

const RAY_COUNT = 13;
const RAY_SPREAD = 84; // degrees either side of straight up

function UscShield({ className = '' }: { className?: string }) {
  const rays = Array.from({ length: RAY_COUNT }, (_, index) => {
    const step = (RAY_SPREAD * 2) / (RAY_COUNT - 1);
    const degrees = -RAY_SPREAD + index * step;
    const radians = ((degrees - 90) * Math.PI) / 180;
    const cx = 32;
    const cy = 33;
    return {
      x1: cx + Math.cos(radians) * 10,
      y1: cy + Math.sin(radians) * 10,
      x2: cx + Math.cos(radians) * 32,
      y2: cy + Math.sin(radians) * 32,
    };
  });

  return (
    <svg
      viewBox="0 0 64 80"
      className={className}
      role="img"
      aria-label="University of Southern California"
      focusable="false"
    >
      <defs>
        <clipPath id="usc-shield-clip">
          <path d="M5 3 H59 V43 C59 61 47 73 32 78 C17 73 5 61 5 43 Z" />
        </clipPath>
      </defs>

      <g clipPath="url(#usc-shield-clip)">
        <g stroke="var(--color-gold)" strokeWidth="1.5" strokeLinecap="round" opacity="0.9">
          {rays.map((ray, index) => (
            <line key={index} x1={ray.x1} y1={ray.y1} x2={ray.x2} y2={ray.y2} />
          ))}
        </g>

        {/* Torch: flame, bowl, stem, foot. */}
        <g fill="#ffffff">
          <path d="M32 10 C37 17.5 36 23 32 28 C28 23 27 17.5 32 10 Z" fill="var(--color-gold)" />
          <path d="M25.5 28.5 H38.5 L36.3 35.5 H27.7 Z" />
          <path d="M30.4 36 H33.6 L33.1 59 H30.9 Z" />
          <path d="M27 59 H37 V63.5 H27 Z" />
        </g>
      </g>

      <path
        d="M5 3 H59 V43 C59 61 47 73 32 78 C17 73 5 61 5 43 Z"
        fill="none"
        stroke="#ffffff"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function UscLockup({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <UscShield className="h-[3.1rem] w-auto shrink-0" />
      <p className="wordmark leading-[1.14] text-white">
        <span className="flex items-baseline gap-[0.3em]">
          <span className="text-[1.7rem] font-bold tracking-[-0.01em] text-gold">USC</span>
          <span className="text-[1.2rem]">University of</span>
        </span>
        <span className="block text-[1.2rem]">Southern California</span>
      </p>
    </div>
  );
}
