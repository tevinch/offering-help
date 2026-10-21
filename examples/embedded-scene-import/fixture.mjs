import {
  convertToExcalidrawElements,
  exportToBlob,
  exportToSvg,
} from "@excalidraw/excalidraw";

export async function createFixture(embed = true) {
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 24;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#e02060";
  ctx.fillRect(0, 0, 16, 24);
  ctx.fillStyle = "#30b0e0";
  ctx.fillRect(16, 0, 16, 24);
  const dataURL = canvas.toDataURL("image/png");
  const files = {
    "fixture-image": {
      id: "fixture-image",
      mimeType: "image/png",
      dataURL,
      created: 1700000000000,
      lastRetrieved: 1700000000000,
    },
  };
  const elements = convertToExcalidrawElements([
    { id: "box", type: "rectangle", x: 20, y: 20, width: 180, height: 110 },
    { id: "label", type: "text", x: 35, y: 35, text: "Editable scene 中文", fontFamily: 2 },
  ], { regenerateIds: false });
  const image = {
    ...elements[0],
    id: "picture",
    type: "image",
    x: 240,
    y: 25,
    width: 96,
    height: 72,
    fileId: "fixture-image",
    status: "saved",
    scale: [1, 1],
    crop: null,
  };
  elements.push(image);
  const appState = { exportEmbedScene: embed, exportBackground: true, viewBackgroundColor: "#fff7e8" };
  const png = await exportToBlob({ elements, appState, files });
  const svg = await exportToSvg({ elements, appState, files });
  return { elements, appState, files, png, svg: new Blob([svg.outerHTML], { type: "image/svg+xml" }) };
}
