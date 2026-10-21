// Pass this function as the first argument to Tabulator's table.download().
// Input is the native export list, after row-range and column options are applied.
export function markdownDownloader(list, options, setFileContents) {
  if (!list.length || list[0].type !== "header" || !list[0].columns.length) {
    throw new Error("Markdown export needs a column header and at least one downloadable column.");
  }
  const width = list[0].columns.length;
  const lines = list.map((row, index) => {
    if (row.type !== (index === 0 ? "header" : "row") || row.indent !== 0) {
      throw new Error("Markdown export supports flat headers and data rows only.");
    }
    if (row.columns.length !== width || row.columns.some(col =>
      !col || col.width !== 1 || col.height !== 1 ||
      (index === 0 ? col.depth !== 1 : col.depth !== undefined && col.depth !== 1))) {
      throw new Error("Markdown export needs flat, unmerged columns.");
    }
    return "| " + row.columns.map(col => textCell(col.value)).join(" | ") + " |";
  });
  lines.splice(1, 0, "| " + Array(width).fill("---").join(" | ") + " |");
  setFileContents(lines.join("\n") + "\n", "text/markdown;charset=utf-8");
}

function textCell(value) {
  let text;
  if (value == null) text = "";
  else if (typeof value === "object") text = JSON.stringify(value);
  else if (["string", "number", "boolean", "bigint"].includes(typeof value)) text = String(value);
  if (typeof text !== "string") throw new TypeError("Cell value cannot be represented as text.");

  // Entities preserve literal Markdown/HTML, including pipes and backslashes.
  // Encode in one pass so an existing entity such as '&amp;' stays literal.
  return text.replace(/[&<>\\`*_\[\]~!:@|]/g, ch => `&#${ch.codePointAt(0)};`)
    .replace(/\r\n|\r|\n/g, "<br>");
}
