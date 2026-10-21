import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { createServer } from "vite";
import { chromium } from "playwright";
const server = await createServer({ server: { host: "127.0.0.1", port: 0 }, logLevel: "error" });
await server.listen();
const address = server.httpServer.address();
const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.CHROMIUM_EXECUTABLE_PATH } : {}) });
try {
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${address.port}/`, { waitUntil: "domcontentloaded" });
  const result = await page.evaluate(async () => {
    const { createFixture } = await import("./fixture.mjs");
    const { convertImage } = await import("./scene.mjs");
    const fixture = await createFixture();
    const outputs = [];
    for (const [ext, type] of [["png", "image/png"], ["svg", "image/svg+xml"]]) {
      const blob = fixture[ext];
      const file = new File([blob], `plan.excalidraw.${ext}`, { type });
      const original = Array.from(new Uint8Array(await file.arrayBuffer()));
      const converted = await convertImage(file);
      outputs.push({ ext, ...converted, original, after: Array.from(new Uint8Array(await file.arrayBuffer())) });
    }
    const plain = await createFixture(false);
    const failures = [];
    for (const [ext, type] of [["png", "image/png"], ["svg", "image/svg+xml"]]) {
      try {
        await convertImage(new File([plain[ext]], `plain.${ext}`, { type }));
        failures.push(null);
      } catch (error) {
        failures.push(error.message);
      }
    }
    return { outputs, failures, expectedFiles: fixture.files };
  });
  for (const output of result.outputs) {
    assert.equal(typeof output.json, "string", "conversion must return an editable scene JSON download");
    const scene = JSON.parse(output.json);
    assert.equal(scene.type, "excalidraw");
    assert.equal(scene.elements.length, 3);
    assert.equal(scene.elements.find(x => x.id === "label").text, "Editable scene 中文");
    assert.equal(scene.elements.find(x => x.id === "picture").fileId, "fixture-image");
    assert.deepEqual(scene.files, result.expectedFiles);
    assert.equal(output.filename, "plan.excalidraw");
    assert.deepEqual(output.original, output.after, "conversion must leave original image bytes unchanged");
  }
  for (const message of result.failures) assert.match(message, /No readable Excalidraw scene/);
  let downloadCount = 0;
  page.on("download", () => downloadCount++);
  for (const output of result.outputs) {
    await page.locator("#image").setInputFiles({ name: `ui.excalidraw.${output.ext}`, mimeType: output.ext === "png" ? "image/png" : "image/svg+xml", buffer: Buffer.from(output.original) });
    const pending = page.waitForEvent("download");
    await page.getByRole("button", { name: "Convert and download" }).click();
    const download = await pending;
    assert.equal(await download.failure(), null);
    assert.equal(download.suggestedFilename(), "ui.excalidraw");
    const downloaded = JSON.parse(await fs.readFile(await download.path(), "utf8"));
    assert.equal(downloaded.elements.find(x => x.id === "label").text, "Editable scene 中文");
    assert.deepEqual(downloaded.files, result.expectedFiles);
  }
  assert.equal(downloadCount, 2);
  await page.locator("#image").setInputFiles({ name: "plain.svg", mimeType: "image/svg+xml", buffer: Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>') });
  await page.getByRole("button", { name: "Convert and download" }).click();
  await page.getByRole("status").filter({ hasText: "No readable Excalidraw scene" }).waitFor();
  assert.equal(downloadCount, 2, "ordinary image must not download an empty drawing");
  console.log(JSON.stringify({ passed: ["PNG editable scene", "SVG editable scene", "image bytes preserved", "source images unchanged", "ordinary PNG/SVG rejected", "two real UI downloads", "failed UI conversion creates no download"], node: process.version, browser: browser.version() }, null, 2));
} finally {
  await browser.close();
  await server.close();
}
