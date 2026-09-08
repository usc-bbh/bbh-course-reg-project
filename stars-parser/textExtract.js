import * as pdfjsLib from "pdfjs-dist";
import { rebuildLines } from "./lineRebuilder";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

// Re-exported so callers can keep importing it from here.
export { rebuildLines };

// Loads a PDF and tries to extract text directly.
// Returns null if the PDF has no text layer (i.e. it's a scanned image).
//
// Each page is rebuilt into real lines before being concatenated — see
// lineRebuilder.js for why joining raw fragments broke the parsing.
export async function extractTextFromPDF(arrayBuffer) {
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const pages = [];

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    pages.push(rebuildLines(content.items));
  }

  const fullText = pages.join("\n");

  const meaningful = fullText.replace(/\s+/g, "").length > 100;
  return meaningful ? fullText : null;
}
