# JPEG trailer copy

Pass an empty string to delete a tag group through `@uswriting/exiftool`:

```js
import { writeMetadata } from '@uswriting/exiftool';

const result = await writeMetadata(file, { 'Trailer:All': '' });
if (!result.success || !(result.data instanceof ArrayBuffer)) {
  throw new Error(result.error || 'No output image returned');
}
const copy = new Blob([result.data], { type: 'image/jpeg' });
// Download or save copy as a separate file.
```

The equivalent public options form is:

```js
const result = await writeMetadata(file, {}, { args: ['-trailer:all='] });
```

Use `writeMetadata` for the edited bytes. `parseMetadata` reads metadata. An empty string produces the native `-Trailer:All=` deletion argument; do not substitute `null` or `undefined`.

## Run the browser example

```sh
npm ci --ignore-scripts
npm run dev
```

Open the displayed local URL, choose a JPEG, click **Prepare copy**, then **Save copy**. The download has a new `-without-trailer.jpg` name. Actual JPEG bytes are checked before editing and before offering the copy. Non-JPEG files are rejected even if renamed `.jpg` or given a JPEG MIME type; there is no format conversion. Each operation finishes before another starts. For a static build, use `npm run build` and `npm run preview`, or serve `dist/` with a static server.

[src/operation.js](src/operation.js) imports the published Wasm asset through Vite and uses the wrapper's public `fetch` option to load its emitted URL. This avoids relying on a relative `./zeroperl.wasm` at the page URL. No library or Wasm modifications are required. The runtime asset is about 25 MB; the first operation loads it. The short calls above assume your application has already configured Wasm loading. This repository provides that configuration.

## Verify saved files

Tested with `@uswriting/exiftool` 1.0.9, its pinned runtime 1.0.10, Chromium 149, native ExifTool 13.59 and Pillow 11.3.0 on macOS. Checks are scripted browser checks, not human manual validation.

Install Python 3, native [ExifTool](https://exiftool.org/), and the test dependencies:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
npx playwright install chromium
PYTHON=.venv/bin/python npm test
npm run build
PYTHON=.venv/bin/python npm run test:production
```

If native ExifTool is outside PATH, set `EXIFTOOL=/absolute/path/to/exiftool` on the test command. Tests invoke that native executable separately from the browser package. Generated images, downloads and screenshots stay in ignored `.work/`.

Tests generate two owned JPEGs with distinct dimensions, decoded RGB pixels, Artist and ImageDescription metadata, then append a harmless 322-byte trailer. A browser selects real Files and downloads actual saved outputs. Native ExifTool verifies the input trailer is present and each output trailer is absent; Pillow compares full decoded RGB hashes and dimensions; metadata and both disk/File input hashes are checked separately. Both API forms, a sequential second file, a JPEG with no trailer, corrupt JPEG input without a download, valid PNG rejection (including a renamed file with a spoofed JPEG MIME type), stale download cleanup, and valid recovery are covered.

The negative control still performs a successful wrapper write and browser download, but omits trailer deletion. Run:

```sh
PYTHON=.venv/bin/python npm run test:negative
```

Its **nonzero exit is expected**: native verification reports that the saved output still contains 322 trailer bytes. This demonstrates that an enabled download or successful wrapper call alone cannot pass the acceptance.

## Scope

This example removes bytes after a JPEG end-of-image marker. Camera previews may live there and will also be removed. It preserves the tested ordinary EXIF fields and decoded pixels; this is not anonymization. JPEG is the tested format. Specific camera payloads, Adobe files, MPF/MotionPhoto behavior, large-file limits and other browsers/formats are unverified. The wrapper bundles ExifTool 13.42; the separate native verifier uses 13.59. Calls in this example are sequential; no parallel-safety claim is made.

- [Wrapper API and setup](https://github.com/6over3/exiftool)
- [Native trailer deletion example](https://exiftool.org/exiftool_pod2.html)

MIT licensed; see [LICENSE](LICENSE).

## Optional coffee

The example is free. If it helps and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
