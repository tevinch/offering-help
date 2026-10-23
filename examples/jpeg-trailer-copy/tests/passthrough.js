import { writeMetadata } from '@uswriting/exiftool';
import wasmUrl from '@6over3/zeroperl-ts/zeroperl.wasm?url';

// Vite emits the published Wasm asset; the supported fetch hook loads that URL.
const loadWasm = () => fetch(wasmUrl);
export async function prepareCopy(file, form) {
  const options = { fetch: loadWasm };
  // Baseline: successful metadata write without trailer deletion.
  const result = await writeMetadata(file, { Artist: 'Fixture artist 1' }, options);
  if (!result.success || !(result.data instanceof ArrayBuffer) || !result.data.byteLength) {
    throw new Error(result.error || 'ExifTool did not return an output image.');
  }
  return result.data;
}
