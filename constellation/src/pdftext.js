/* Constellation PDF text extraction. Shared by the page and test/run.mjs so both run the same code.
   Takes a pdf.js library object and the PDF bytes; returns the report text with lines rebuilt
   from the vertical position of each text fragment. No network: the caller supplies the bytes. */
(function (root) {
  // Options passed to pdf.js in both places. isEvalSupported:false keeps pdf.js from calling
  // new Function(), which the page's Content-Security-Policy blocks.
  const PDF_OPTIONS = { isEvalSupported: false, disableFontFace: true, useSystemFonts: true };

  function rebuildLines(pages) {
    const out = [];
    for (const items of pages) {
      const rows = [];
      for (const it of items) {
        if (!it.str || !it.str.trim()) continue;
        const x = it.transform[4], y = it.transform[5], h = Math.abs(it.transform[3]) || it.height || 8;
        let r = rows.find(r => Math.abs(r.y - y) < Math.max(2, h * .4));
        if (!r) { r = { y, items: [] }; rows.push(r); }
        r.items.push({ str: it.str, x, w: it.width });
      }
      rows.sort((a, b) => b.y - a.y);
      for (const r of rows) {
        r.items.sort((a, b) => a.x - b.x);
        let s = '', end = null;
        for (const it of r.items) {
          if (end !== null) { const gap = it.x - end; if (gap > 1.5) s += ' '.repeat(Math.max(1, Math.round(gap / 4))); }
          s += it.str; end = it.x + it.w;
        }
        out.push(s);
      }
    }
    return out.join('\n');
  }

  async function extractText(lib, data) {
    const doc = await lib.getDocument({ data, ...PDF_OPTIONS }).promise;
    try {
      const pages = [];
      for (let p = 1; p <= doc.numPages; p++) pages.push((await (await doc.getPage(p)).getTextContent()).items);
      const text = rebuildLines(pages);
      if (text.replace(/\s+/g, '').length < 100) throw new Error('This PDF is a scanned image with no text to read. Download the report from STARS and save it as a PDF instead of scanning a printout.');
      return text;
    } finally { doc.destroy(); }
  }

  const api = { PDF_OPTIONS, rebuildLines, extractText };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.PdfText = api;
})(typeof window !== 'undefined' ? window : globalThis);
