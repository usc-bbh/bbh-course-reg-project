// Rebuilding PDF text fragments into lines.
//
// Deliberately a module of its own, with no imports. textExtract.js pulls in
// pdfjs-dist, whose browser build touches DOMMatrix and so cannot be loaded
// by `node --test`. Keeping this function dependency-free means the test
// suite can import and exercise the real implementation instead of holding a
// second copy of it — which is the flaw docs/parser-brief.md §12 identifies
// in stars-parser/test/parser.test.js.

// A PDF does not store lines of text. It stores fragments, each positioned by
// its own transform matrix. This rebuilds the visual lines of a page: group
// fragments by their baseline (transform[5]), order each group left to right
// by its x offset (transform[4]), and join.
//
// Two details matter, and both were bugs before:
//
//   1. Line structure. The previous version joined every fragment on a page
//      with " ", collapsing the page into a single line. Everything in
//      fieldParser.js that works line by line then had nothing to match —
//      most visibly extractCourses(), whose row pattern is anchored with ^
//      and so matched nothing at all.
//
//   2. Spacing inside tokens. Fragments split mid-token, so joining them with
//      " " also inserted spaces inside words and numbers — "20243" arrived as
//      "2 0 2 4 3". That breaks the numeric patterns even where they never
//      needed line breaks, which is why the GPA and the catalog year came
//      back null. Fragments within a line are therefore joined with "", not
//      " "; real gaps between words arrive as their own fragments and are
//      preserved.
//
// Grouping on the exact baseline value follows docs/parser-brief.md §5, which
// reports it verified against every real report held so far.
export function rebuildLines(items) {
  const byBaseline = new Map();

  for (const item of items) {
    const y = item.transform[5];
    if (!byBaseline.has(y)) byBaseline.set(y, []);
    byBaseline.get(y).push(item);
  }

  return [...byBaseline.entries()]
    .sort((a, b) => b[0] - a[0]) // top of the page downwards
    .map(([, frags]) =>
      frags
        .sort((a, b) => a.transform[4] - b.transform[4]) // left to right
        .map((frag) => frag.str)
        .join("")
    )
    .join("\n");
}
