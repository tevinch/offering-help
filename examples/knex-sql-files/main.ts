import { fileURLToPath } from "node:url";
import knex from "knex";
import person, { type Params as PersonParams, type Row as PersonRow } from "./person.sql";
import findPeople, { type Params as SearchParams, type Row as SearchRow } from "./find-people.sql";

const db = knex({
  client: "better-sqlite3",
  connection: {
    filename: fileURLToPath(new URL(".example-data/example.sqlite", import.meta.url)),
  },
  useNullAsDefault: true,
});

try {
  // .raw keeps :id and :pattern for Knex's named value bindings.
  // These Row[] types describe this SQLite driver's raw result, not .run()'s result.
  const oneParams: PersonParams = { id: 2 };
  const one = await db.raw<PersonRow[]>(person.raw, oneParams);
  const missing = await db.raw<PersonRow[]>(person.raw, { id: 99 } satisfies PersonParams);
  const many = await db.raw<SearchRow[]>(findPeople.raw, { pattern: "Ada%" } satisfies SearchParams);
  const quoted = await db.raw<SearchRow[]>(findPeople.raw, { pattern: "O'Brien :id?" } satisfies SearchParams);

  console.log(JSON.stringify({ one, missing, many, quoted }, null, 2));
} finally {
  await db.destroy();
}
