import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { inspectMatches } from "./preview.mjs";

test("global matching joins every full match", () => {
  assert.deepEqual(inspectMatches("red blue green", /[a-z]+/g, " | "), {
    matches: ["red", "blue", "green"], joined: "red | blue | green",
  });
  assert.equal(inspectMatches("yellow violet", /[a-z]+/g, "-").joined, "yellow-violet");
  assert.equal(inspectMatches("café 茶", /[^\s]+/gu, " / ").joined, "café / 茶");
});

test("without global matching the full match and capture groups are joined", () => {
  assert.deepEqual(inspectMatches("red blue green gold", /[a-z]+/, " | "), {
    matches: ["red"], joined: "red",
  });
  assert.deepEqual(inspectMatches("red blue green gold", /([a-z]+) ([a-z]+)/, " | "), {
    matches: ["red blue", "red", "blue"], joined: "red blue | red | blue",
  });
  assert.deepEqual(inspectMatches("red blue green gold", /([a-z]+) ([a-z]+)/g, " | "), {
    matches: ["red blue", "green gold"], joined: "red blue | green gold",
  });
});

test("no matches give no joined text", () => {
  assert.deepEqual(inspectMatches("red blue", /[0-9]+/g, " | "), { matches: null, joined: "" });
});

test("the runnable examples print actual arrays and joined text", () => {
  const run = spawnSync(process.execPath, [fileURLToPath(new URL("./preview.mjs", import.meta.url))], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr);
  assert.equal(run.stderr, "");
  const records = run.stdout.trim().split("\n").map(line => JSON.parse(line));
  assert.deepEqual(records.map(record => record.joined), [
    "red | blue | green", "red", "red blue | red | blue", "red blue | green gold", "", "café / 茶",
  ]);
  assert.deepEqual(records[0], {
    message: "red blue green", titleFormat: "/[a-z]+/g", join: " | ",
    matches: ["red", "blue", "green"], joined: "red | blue | green",
  });
});
