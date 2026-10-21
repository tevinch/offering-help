import { loadFromBlob, serializeAsJSON } from "@excalidraw/excalidraw";

export async function convertImage(file) {
  if (!/\.(png|svg)$/i.test(file.name || "")) {
    throw new Error("Choose a PNG or SVG exported with its Excalidraw scene embedded.");
  }
  let scene;
  try {
    scene = await loadFromBlob(file, null, null);
  } catch {
    throw new Error("No readable Excalidraw scene was found. An ordinary image cannot be converted into editable shapes. Export again with ‘Embed scene’ enabled.");
  }
  return {
    json: serializeAsJSON(scene.elements, scene.appState, scene.files || {}, "local"),
    filename: file.name.replace(/(?:\.excalidraw)?\.(png|svg)$/i, ".excalidraw"),
  };
}
