import { extractTextFromPDF } from "./textExtract";
import { parseStarsFields, StarsParseError } from "./fieldParser";

export { StarsParseError };

// Main entry point for the STARS parser.
//
// Scope (docs/parser-brief.md §3): the single-column PDF produced by
// print-to-PDF from experience.usc.edu. That export always has a real text
// layer, so this is a single extraction path — no OCR fallback. A scanned
// report or a two-column export (Registrar-only; students never see it)
// isn't handled, and returns null so the UI can prompt the student to enter
// their info manually rather than guess.
//
// Everything runs in the browser — no data is sent to a server.
export async function parseStarsReport(file, options = {}) {
  const { onStatus } = options;
  const status = (msg) => onStatus && onStatus(msg);

  const arrayBuffer = await file.arrayBuffer();

  status("Reading PDF...");
  const rawText = await extractTextFromPDF(arrayBuffer);

  if (!rawText) {
    status("Could not extract text from this PDF — it may be scanned or in an unsupported format.");
    return null;
  }

  status("Parsing...");
  try {
    const result = parseStarsFields(rawText);
    status("Done.");
    return result;
  } catch (err) {
    if (err instanceof StarsParseError) {
      console.error("STARS parse failed:", err.message);
      status("Could not read this report — it may be in a format this parser doesn't support yet.");
      return null;
    }
    throw err;
  }
}

export { parseStarsFields } from "./fieldParser";
