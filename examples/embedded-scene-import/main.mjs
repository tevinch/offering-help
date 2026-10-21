import { convertImage } from "./scene.mjs";

const input = document.querySelector("#image");
const button = document.querySelector("#convert");
const status = document.querySelector("#status");

input.addEventListener("change", () => {
  button.disabled = !input.files.length;
  status.textContent = "";
});

button.addEventListener("click", async () => {
  const file = input.files[0];
  if (!file) return;
  button.disabled = true;
  status.textContent = "Reading the embedded scene…";
  try {
    const result = await convertImage(file);
    const url = URL.createObjectURL(new Blob([result.json], { type: "application/vnd.excalidraw+json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = result.filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    const scene = JSON.parse(result.json);
    status.textContent = `Downloaded ${result.filename}: ${scene.elements.length} editable elements, ${Object.keys(scene.files).length} image files. Import this file with ExcaliDash’s “Import drawings” button.`;
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = !input.files.length;
  }
});
