import { UscLockup } from './UscLockup';

/**
 * The one piece of full-strength brand in the app, built to sit beside USC's
 * own registration pages: the wordmark in Caslon on the left, the university
 * lockup on the right, a gold rule underneath, cardinal behind all of it.
 *
 * The wordmark is a paragraph, not a heading — each screen owns its own h1.
 */
export function AppHeader() {
  return (
    <header
      data-print="hide"
      className="on-cardinal border-b-[3px] border-gold bg-linear-to-b from-cardinal to-cardinal-deep"
    >
      <div className="mx-auto w-full max-w-[1600px] px-5 py-5 sm:px-8 sm:py-6">
        <div className="flex flex-wrap items-center justify-between gap-x-8 gap-y-5">
          <p className="wordmark text-[1.75rem] leading-none text-white sm:text-[2.15rem]">
            Four-Year Degree Planner
          </p>
          <UscLockup />
        </div>
        <p className="mt-4 text-micro text-white/85 sm:mt-3 sm:text-right">
          Everything you enter stays on this device.
        </p>
      </div>
    </header>
  );
}
