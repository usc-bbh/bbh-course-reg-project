/**
 * The one piece of full-strength brand in the app: the validator GUI's cardinal
 * gradient with its gold rule underneath, so the two tools read as one product.
 *
 * The wordmark is a paragraph, not a heading — each screen owns its own h1.
 */
export function AppHeader() {
  return (
    <header
      data-print="hide"
      className="on-cardinal border-b-[3px] border-gold bg-linear-to-b from-cardinal to-cardinal-deep"
    >
      <div className="mx-auto flex w-full max-w-[1600px] items-center gap-3 px-4 py-3.5 sm:px-6">
        <span
          aria-hidden="true"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-field bg-gold text-[17px] font-bold text-cardinal"
        >
          4
        </span>
        <p className="text-[15px] font-semibold text-white">Four-Year Degree Planner</p>
        <p className="ml-auto hidden text-[12px] text-white/80 sm:block">
          Everything stays on this device
        </p>
      </div>
    </header>
  );
}
