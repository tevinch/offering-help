# Export a Tabulator table as Markdown

Download filtered, selected or all rows as a GitHub-flavored Markdown table using Tabulator's existing custom file-formatter API. This example uses Tabulator **6.7.0**; it does not add a built-in `"md"` download type.

## Try the example

With Node.js 20 or newer and Python 3 available, run these commands in this directory:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm test
python3 -m http.server 8000 --bind 127.0.0.1
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Any other static HTTP server works too.

1. Select a couple of rows with the checkboxes.
2. Choose **Active items**, then **Move Notes before Item**. You can also drag column headers or click a header to sort.
3. Download filtered or selected rows. Selected rows remain selected when the filter hides them.
4. Open the downloaded `.md` file in a Markdown viewer that supports GFM tables and `<br>` line breaks, such as GitHub's Markdown preview.
5. Clear the filter, double-click an Item or Notes cell to edit it, and download again. The file reflects the new values and selection.

The page also shows the exact last downloaded Markdown. Its hidden Reference column is deliberately included, Scratch is excluded, and Count is transformed by a download accessor. No server upload is involved.

## Use it with your table

Copy [markdown-downloader.mjs](./markdown-downloader.mjs) into your application and pass the function as the first argument to `download`:

```js
import { markdownDownloader } from "./markdown-downloader.mjs";

// The fourth argument uses Tabulator's normal row-range selection.
table.download(markdownDownloader, "selected.md", {}, "selected");
table.download(markdownDownloader, "filtered.md", {}, "active");
table.download(markdownDownloader, "all.md", {}, "all");

// Omit the fourth argument to use your downloadRowRange setting.
table.download(markdownDownloader, "report.md");
```

Tabulator prepares the export list before calling the function. The function preserves that list's column and row order. This retains `download`, `titleDownload`, `accessorDownload` and native row-range behavior, rather than rebuilding the export from `getData()`.

For example, these existing column options continue to apply:

```js
columns: [
  { title: "Name", field: "name", titleDownload: "Item name" },
  { title: "Count", field: "count", accessorDownload: value => `${value} items` },
  { title: "Reference", field: "reference", visible: false, download: true },
  { title: "Local note", field: "localNote", download: false },
]
```

`"active"` means rows passing the filter; `"visible"` means rows in the viewport. Selected exports include selected rows outside the active filter. Row order is the order Tabulator supplies for that range: in the tested release, `"selected"` follows selection order and `"all"` follows the full data order, while `"active"` reflects sorting. The formatter does not impose a different order.

## Text and supported scope

- Flat columns and ordinary data rows, with column headers enabled and at least one downloadable column. Empty selections produce a header-only table.
- Pipes, backslashes, Markdown punctuation, HTML-looking text and existing entities are encoded as literal text. LF, CRLF and CR line endings become `<br>` within the cell. Existing Markdown formatting is displayed literally, rather than interpreted. Normal HTML whitespace collapsing still applies.
- `null` and `undefined` become empty cells. Strings, numbers, booleans and bigint values become text; object values use `JSON.stringify`. Circular or otherwise unserializable values stop the export before a file is emitted. Convert dates or other values with `accessorDownload` when you want a particular display format.
- Rich HTML column-title strings are exported literally. Use a plain `titleDownload` for the label you want in the file.

Grouped headers, row groups, calculation rows, merged cells and indented tree rows are rejected. The function does not change your table settings or silently drop these structures. A viewer that disables inline HTML may display `<br>` literally instead of a line break. This is a text table export, not a copy of cell formatting or interactive controls.

## Validation

The included five tests exercise the formatter and real Marked GFM parsing. Additional software-operated Chromium **153.0.8010.12** checks on macOS, with Node.js **24.19.0**, Tabulator **6.7.0** and Marked **18.1.1**, saved actual browser downloads and inspected their rendered table cells. They covered filtered and selected rows, a selected row hidden by the filter, column movement, sorting, export column settings/accessors, literal punctuation and multiline values, all rows, an actual cell edit followed by another download, and empty selection. Wrong-range and unescaped-download controls failed the same output checks.

The example was also installed and exercised from a clean copy. These are scripted and software-operated browser checks; the requester's application and adoption have not been verified. `marked` is a development dependency for tests, and the example page does not load it.

See the [custom formatter and export-list documentation](https://www.tabulator.info/docs/6.x/download/#custom), [native row-range documentation](https://www.tabulator.info/docs/6.x/download/#row-range), and [original export request](https://github.com/tabulator-tables/tabulator/issues/4992).

## Optional coffee

This example is free. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
