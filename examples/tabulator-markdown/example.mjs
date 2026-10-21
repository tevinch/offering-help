import { TabulatorFull as Tabulator } from "./node_modules/tabulator-tables/dist/js/tabulator_esm.mjs";
import { markdownDownloader } from "./markdown-downloader.mjs";

const status = document.querySelector("#status");
export const table = new Tabulator("#table", {
  data: [
    { id: 1, name: "Cedar | desk", notes: "First line\nSecond line", active: true, units: 0, reference: "R-1", scratch: "Local note", omitted: "Not exported" },
    { id: 2, name: "中文 *literal*", notes: "Use `code` and [text](path) \\ here", active: false, units: 2, reference: "R-2", scratch: "Local note", omitted: "Not exported" },
    { id: 3, name: "Maple &amp; oak", notes: "<b>literal tag</b>\r\nA | B", active: true, units: 3, reference: "R-3", scratch: "Local note", omitted: "Not exported" },
    { id: 4, name: "Birch", notes: null, active: false, units: 4, reference: "R-4", scratch: "Local note", omitted: "Not exported" },
  ],
  index: "id",
  layout: "fitData",
  movableColumns: true,
  selectableRows: true,
  selectableRowsPersistence: true,
  rowHeader: { formatter: "rowSelection", titleFormatter: "rowSelection", headerSort: false, resizable: false, width: 40, download: false },
  downloadEncoder(contents, mimeType) {
    document.querySelector("#preview").textContent = contents;
    return new Blob([contents], { type: mimeType });
  },
  columns: [
    { title: "ID", field: "id", width: 65, sorter: "number" },
    { title: "Item", titleDownload: "Item | name", field: "name", formatter: "plaintext", editor: "input", width: 190 },
    { title: "Notes", field: "notes", formatter: "textarea", editor: "textarea", width: 260 },
    { title: "Active", field: "active", formatter: "tickCross", width: 80 },
    { title: "Count", titleDownload: "Count | items", field: "units", accessorDownload: value => `${value} items`, width: 85 },
    { title: "Reference", field: "reference", visible: false, download: true },
    { title: "Scratch", field: "scratch", formatter: "plaintext", download: false, width: 120 },
    { title: "Omitted", field: "omitted", visible: false },
  ],
});

table.on("tableBuilt", () => { status.textContent = "Ready. Choose rows and download."; });
document.querySelector("#filter").addEventListener("change", event => {
  if (event.target.value === "active") table.setFilter("active", "=", true);
  else table.clearFilter();
});
document.querySelector("#move").addEventListener("click", () => table.moveColumn("notes", "name", false));
document.querySelector("#clear").addEventListener("click", () => table.deselectRow());
for (const button of document.querySelectorAll("[data-range]")) {
  button.addEventListener("click", () => {
    try {
      const range = button.dataset.range;
      table.download(markdownDownloader, `${range}.md`, {}, range);
      status.textContent = `Downloaded ${range}.md. Open it in a Markdown viewer.`;
    } catch (error) {
      status.textContent = error.message;
    }
  });
}
