import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";
import Database from "better-sqlite3";

const directory = fileURLToPath(new URL(".", import.meta.url));

function run(...args) {
  const child = spawnSync(process.execPath, args, {
    cwd: directory,
    encoding: "utf8",
    timeout: 30_000,
  });
  assert.equal(child.status, 0, child.stderr || String(child.error));
  return child.stdout;
}

test("the SQL-file example returns raw SQLite rows with bound values", () => {
  run("setup.mjs");
  const actual = JSON.parse(run("--import", "reylo/register", "main.ts"));
  assert.deepEqual(actual, {
    one: [{ id: 2, name: "Ada Lovelace", note: "mathematics" }],
    missing: [],
    many: [
      { id: 1, name: "Ada", note: null },
      { id: 2, name: "Ada Lovelace", note: "mathematics" },
    ],
    quoted: [{ id: 3, name: "O'Brien :id?", note: "literal text" }],
  });
  const db = new Database(fileURLToPath(new URL(".example-data/example.sqlite", import.meta.url)), { readonly: true });
  try {
    assert.deepEqual(db.prepare("select id, name, note from people order by id").all(), [
      { id: 1, name: "Ada", note: null },
      { id: 2, name: "Ada Lovelace", note: "mathematics" },
      { id: 3, name: "O'Brien :id?", note: "literal text" },
      { id: 4, name: "Grace", note: "compilers" },
    ]);
  } finally {
    db.close();
  }
});
