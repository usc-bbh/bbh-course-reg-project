import * as pdfjsLib from "pdfjs-dist";
import { createWorker } from "tesseract.js";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

// Renders each PDF page to a canvas and runs Tesseract OCR on it.
// Used as fallback when the PDF has no text layer.
// Runs entirely in the browser — nothing is sent to a server.
export async function extractTextViaOCR(arrayBuffer, onProgress) {
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const worker = await createWorker("eng");
  let fullText = "";

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const viewport = page.getViewport({ scale: 2.0 });

    const canvas = document.createElement("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    const ctx = canvas.getContext("2d");
    await page.render({ canvasContext: ctx, viewport }).promise;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const correctedCanvas = correctRotation(canvas, imageData);

    const { data } = await worker.recognize(correctedCanvas);
    fullText += data.text + "\n";

    if (onProgress) onProgress(i, pdf.numPages);
  }

  await worker.terminate();
  return fullText;
}

// Some STARS scans come in upside-down (seen in the registrar's anonymized copies).
// This detects that by comparing ink density in the top vs bottom quarter and rotates if needed.
function correctRotation(canvas, imageData) {
  const { width, height, data } = imageData;
  const quarterHeight = Math.floor(height / 4);
  let topDark = 0;
  let bottomDark = 0;

  for (let y = 0; y < quarterHeight; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;
      if ((data[idx] + data[idx + 1] + data[idx + 2]) / 3 < 128) topDark++;
    }
  }

  for (let y = height - quarterHeight; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;
      if ((data[idx] + data[idx + 1] + data[idx + 2]) / 3 < 128) bottomDark++;
    }
  }

  if (bottomDark > topDark * 1.5) {
    const rotated = document.createElement("canvas");
    rotated.width = canvas.width;
    rotated.height = canvas.height;
    const rCtx = rotated.getContext("2d");
    rCtx.translate(canvas.width / 2, canvas.height / 2);
    rCtx.rotate(Math.PI);
    rCtx.drawImage(canvas, -canvas.width / 2, -canvas.height / 2);
    return rotated;
  }

  return canvas;
}
