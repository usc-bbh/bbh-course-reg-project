# Changes in 1.2.0 (2026-07-19) — live-run reliability and speed

Diagnosed from a real 263-minor run that stalled and stopped:

1. **False-positive challenge detection (the main failure).** The bare word
   "challenge" was a title marker, so "Engineering Innovation for Global
   Challenges Minor" was deterministically misread as a bot-verification
   wall — the run waited 6 minutes for a verification that never existed.
   Removed the fuzzy marker; the definitive `x-amzn-waf-action` response
   header is now checked in both fetch layers. Regression test added.
2. **WAF token rotation stranded the fast path.** Browser→HTTP cookie sync
   happened only once per run; when the token rotated (~hourly) direct
   fetching never recovered and every page paid minutes of browser cost.
   Cookies now re-sync after every successful browser fetch.
3. **Headless challenge auto-resolve.** The WAF's JS challenge solves itself
   in a real browser; headless runs used to bail out immediately instead of
   giving it up to 30 seconds.
4. **Driver ladder.** The known-good discovery config now runs first; the
   retry grep no longer matches the success line "Boundary proven"; pacing
   lowered to 2–4.5 s; on a verification stop the driver cools down 90 s and
   auto-resumes (visible browser) up to twice.

Validated by finishing the interrupted run: 162 remaining minors collected
with zero failures (~9 s/page including pacing), full-collection audit passed.
