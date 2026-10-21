import assert from "node:assert/strict";
import test from "node:test";
import { marked } from "marked";
import { markdownDownloader } from "./markdown-downloader.mjs";

const cell = value => ({ value, width: 1, height: 1, depth: 1 });
const row = (type, values) => ({ type, indent: 0,
  columns: values.map(value => ({ ...cell(value), depth: type === "row" ? undefined : 1 })) });
function download(list) {
  let result;
  markdownDownloader(list, {}, (text, mime) => { result = { text, mime }; });
  assert.ok(result, "formatter must supply file contents");
  return result;
}

// Removing escaping would split pipes/newlines into extra cells or interpret text.
test("plain-text cells stay inside one GFM table cell", () => {
  const list = [row("header", ["Name | label", "Notes"]), row("row", [
    "*literal* _text_ `code` [link](path) ~strike~ \\ | <b> &amp;",
    "first\r\nsecond\rthird\nfourth",
  ])];
  const original = structuredClone(list);
  const result = download(list);
  assert.equal(result.mime, "text/markdown;charset=utf-8");
  const tokens = marked.lexer(result.text, { gfm: true });
  assert.equal(tokens.length, 1);
  assert.equal(tokens[0].type, "table");
  assert.equal(tokens[0].header.length, 2);
  assert.equal(tokens[0].rows.length, 1);
  assert.equal(tokens[0].rows[0].length, 2);
  const rendered = marked.parse(result.text, { gfm: true });
  assert.equal((rendered.match(/<br>/g) || []).length, 3);
  assert.doesNotMatch(rendered, /<(?:strong|em|del|a|code|b)(?:>|\s)/);
  assert.match(rendered, /(?:&lt;|&#60;)b(?:&gt;|&#62;)/);
  assert.match(rendered, /(?:&amp;|&#38;)amp;/);
  assert.deepEqual(list, original, "export values must not be mutated");
});

// Reordering or filtering in this formatter would break the native export contract.
test("native export-list order and scalar values are retained", () => {
  const result = download([row("header", ["Second", "First"]),
    row("row", [false, 0]), row("row", [null, undefined]), row("row", ["中文", { x: "a|b" }])]);
  const table = marked.lexer(result.text)[0];
  assert.deepEqual(table.header.map(c => c.text), ["Second", "First"]);
  assert.equal(table.rows.length, 3);
  assert.deepEqual(table.rows[0].map(c => c.text), ["false", "0"]);
  assert.deepEqual(table.rows[1].map(c => c.text), ["", ""]);
  assert.equal(table.rows[2][0].text, "中文");
  assert.equal(table.rows[2].length, 2);
  assert.match(marked.parse(result.text), /a(?:&#124;|\|)b/);
});

// Dropping a missing/empty header silently would create an invalid Markdown table.
test("empty selection still exports the column header", () => {
  const table = marked.lexer(download([row("header", ["Name", "Notes"])]).text)[0];
  assert.equal(table.type, "table");
  assert.equal(table.rows.length, 0);
  for (const input of [[], [row("row", ["value"])], [row("header", [])]]) {
    assert.throws(() => download(input), /header|column/i);
  }
});

// Removing these checks would silently flatten/drop unsupported table structures.
test("unsupported export structures fail before any file is emitted", () => {
  const header = row("header", ["Name"]);
  const cases = [
    [header, row("group", ["Group"])],
    [header, row("calc", [1])],
    [header, { ...row("row", ["child"]), indent: 1 }],
    [{ ...header, columns: [{ ...cell("Group"), width: 2, depth: 2 }] }],
    [header, row("header", ["Again"])],
    [header, row("row", [1, 2])],
    [{ ...header, columns: [null] }],
  ];
  for (const list of cases) {
    let emitted = false;
    assert.throws(() => markdownDownloader(list, {}, () => { emitted = true; }), /flat|header|column|row/i);
    assert.equal(emitted, false);
  }
});

// Circular/non-data values must not be replaced by misleading blank text.
test("unserializable values fail before a download is emitted", () => {
  const circular = {}; circular.self = circular;
  for (const value of [circular, () => {}, Symbol("value")]) {
    let emitted = false;
    assert.throws(() => markdownDownloader([row("header", ["Value"]), row("row", [value])], {},
      () => { emitted = true; }));
    assert.equal(emitted, false);
  }
});
