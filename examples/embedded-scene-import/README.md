# Import an embedded Excalidraw scene into ExcaliDash

If a PNG or SVG was exported with **Embed scene** enabled, it contains the editable Excalidraw data as well as the rendered image. This example reads that data locally and downloads a `.excalidraw` file that ExcaliDash can import.

This is a consumer workaround for [ExcaliDash #281](https://github.com/ZimengXiong/ExcaliDash/issues/281), using the existing importer. It does not add native PNG/SVG support to the dashboard.

## Run locally

Use Node.js 20.19+ or 22.12+; the example was checked with Node.js 24.19.0.

```sh
npm ci --ignore-scripts
npm run dev
```

Open the local URL printed by Vite. Choose the `.png` or `.svg`, then select **Convert and download**. The original image stays unchanged; its contents are processed in this browser without uploading them.

In your existing ExcaliDash workspace:

1. Go to the dashboard and choose **Import drawings**.
2. Select the downloaded `.excalidraw` file. Use this drawing import, rather than the separate `.excalidash` backup importer.
3. Open the new drawing. Check its text, shapes, background and embedded images.
4. Edit an object, let autosave complete, then reload the drawing to check the saved result. Other drawings stay in the workspace.

Renaming a PNG or SVG to `.excalidraw` does not work: the importer expects scene JSON, not image bytes. An ordinary image with no embedded scene cannot be restored to editable shapes; export it again from the source drawing with **Embed scene** enabled if that source is available.

## The relevant API calls

```js
import { loadFromBlob, serializeAsJSON } from "@excalidraw/excalidraw";

const scene = await loadFromBlob(file, null, null);
const json = serializeAsJSON(
  scene.elements,
  scene.appState,
  scene.files || {},
  "local",
);
```

Keep `scene.files`: it carries the image data referenced by image elements. The four-argument serialization call above matches the published **0.18.1** package. Local serialization keeps the exportable scene state and removes deleted elements and temporary editor state; it is not a byte-for-byte copy of every editor setting.

Sources: [official loading utility](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils#loadfromblob), [official export options](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export#additional-attributes-of-appstate-for-export-apis), [versioned serialization source](https://github.com/excalidraw/excalidraw/blob/v0.18.1/packages/excalidraw/data/json.ts#L43).

## Checks

```sh
npx playwright install chromium
npm test
npm run build
```

The browser test creates PNG and SVG exports with embedded text, shapes and a small raster image. It checks the restored object IDs, text and image bytes, unchanged input bytes, actual UI downloads, and rejection of ordinary images. Set `CHROMIUM_EXECUTABLE_PATH` if you already have a compatible Chromium executable.

Local software-operated Chromium 153 checks also exercised the actual ExcaliDash **v0.6.5** dashboard: import each downloaded file, open it, move the imported objects, observe successful autosave requests, and reload. A second edit changed the imported text and survived another autosave and reload. Object IDs and image bytes survived; an existing drawing was unchanged. The host ran with a fresh local SQLite database in its supported single-user mode. These checks do not establish compatibility with every Excalidraw export, deployment setting or the original reporter’s installation.

The example pins Excalidraw **0.18.1**, React **18.3.1**, Vite **7.3.6**, and Playwright **1.62.1**. The dependency lockfile is included.

## Optional coffee

This example is free. If it saves you time, a small coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
