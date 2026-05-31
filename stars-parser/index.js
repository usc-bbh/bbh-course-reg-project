import { extractTextFromPDF } from "./textExtract";
import { extractTextViaOCR } from "./ocrExtract";
import { parseStarsFields } from "./fieldParser";

// Main entry point for the STARS parser.
//
// Tries text extraction first (works for PDFs downloaded directly from my.usc.edu).
// Falls back to OCR if no text layer is found (handles scanned copies).
// Returns null if both fail, so the UI can prompt the student to enter info manually.
//
// Everything runs in the browser — no data is sent to a server.
export async function parseStarsReport(file, options = {}) {
  const { onProgress, onStatus } = options;
  const status = (msg) => onStatus && onStatus(msg);

  const arrayBuffer = await file.arrayBuffer();

  status("Reading PDF...");
  let rawText = await extractTextFromPDF(arrayBuffer);

  if (!rawText) {
    status("No text layer found, running OCR...");
    try {
      rawText = await extractTextViaOCR(arrayBuffer, onProgress);
    } catch (err) {
      console.error("OCR failed:", err);
      status("Could not read this PDF.");
      return null;
    }
  }

  if (!rawText || rawText.replace(/\s+/g, "").length < 100) {
    status("Could not extract text from this PDF.");
    return null;
  }

  status("Parsing...");
  const result = parseStarsFields(rawText);
  status("Done.");
  return result;
}

export { parseStarsFields } from "./fieldParser";
