import { writeMetadata } from '@uswriting/exiftool';
import wasmUrl from '@6over3/zeroperl-ts/zeroperl.wasm?url';

// Vite emits the published Wasm asset; the supported fetch hook loads that URL.
const loadWasm = () => fetch(wasmUrl);
function isJpeg(bytes) {
  return bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
}
export async function prepareCopy(file, form) {
  // File extensions and MIME types do not establish the actual image format.
  if (!isJpeg(new Uint8Array(await file.slice(0, 3).arrayBuffer()))) {
    throw new Error('Choose a JPEG file; other formats are not converted.');
  }
  const options = { fetch: loadWasm };
  const result = form === 'args'
    ? await writeMetadata(file, {}, { ...options, args: ['-trailer:all='] })
    : await writeMetadata(file, { 'Trailer:All': '' }, options);
  if (!result.success || !(result.data instanceof ArrayBuffer) || !result.data.byteLength) {
    throw new Error(result.error || 'ExifTool did not return an output image.');
  }
  if (!isJpeg(new Uint8Array(result.data))) {
    throw new Error('ExifTool returned a non-JPEG output.');
  }
  return result.data;
}
