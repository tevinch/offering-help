# Reylo SQL files with Knex

This example imports a SQL file with Reylo and executes its original SQL through `knex.raw`. It uses SQLite and named value bindings, with query parameter and row types inferred from the database.

```sql
-- person.sql
select id, name, note from people where id = :id
```

```ts
import person, { type Params, type Row } from "./person.sql";

const params: Params = { id: 2 };
const rows = await db.raw<Row[]>(person.raw, params);
// [{ id: 2, name: "Ada Lovelace", note: "mathematics" }]
```

Here `db` is a Knex instance configured with `client: "better-sqlite3"`. The complete setup and calls are in [main.ts](main.ts).

## Run it

Use Node.js 24 or later. The pinned TypeScript **7.1.0-beta** compiler is required for Reylo's content mappers; this is a preview compiler dependency.

Download this directory, change into it, and run:

```sh
npm ci --ignore-scripts
npm run setup
npm run typecheck
npm start
npm test
```

The setup creates or resets this example's four-row `people` table in `.example-data/example.sqlite`. It does not use an external database. Leave `REYLO_CONFIG` unset for this example so Reylo reads the included `.reylo.yaml`.

The output contains:

| Query | SQLite raw result |
|---|---|
| Person with ID 2 | One-element array containing Ada Lovelace |
| Person with ID 99 | Empty array |
| Names matching `Ada%` | Two rows, ordered by ID, including a null note |
| Name matching `O'Brien :id?` | The matching row; the quote and punctuation are bound as data |

The test runs the actual command and queries, checks those results, then verifies that all four stored rows remain unchanged.

## How the pieces fit

- `.reylo.yaml` points analysis at the example's SQLite file. Create the database before type-checking or importing the SQL files.
- `tsconfig.json` registers Reylo's content mapper and explicitly includes Node types. `--runExternalCode` permits the compiler to run that mapper.
- `node --import reylo/register main.ts` loads the imported SQL files at runtime.
- `person.raw` is the SQL as written, including `:id`. Knex turns that named **value** binding into the driver's parameter placeholder and passes the value separately.
- `Params` checks the parameter object at compile time. `Row[]` describes this SQLite driver's returned rows. It is a TypeScript annotation, not runtime validation.

## Boundaries

Use `.raw` for this named-binding recipe. Reylo's `.sql` is already compiled for its own execution path; do not substitute it while keeping the same Knex binding object. This example does not pass the Knex instance to Reylo's `.run()`; Knex is not listed as a supported direct client.

Calling `knex.raw` skips Reylo's runtime input conversion, output decoding and cardinality shaping. A primary-key lookup still returns a raw array here, including `[]` when no row matches. The fixture deliberately uses `INTEGER`, `TEXT` and null values whose native SQLite results match the inferred types. This is not a general adapter for booleans, large integers, dates, JSON, structured parameters or Reylo's additional SQL annotations.

Raw result shapes depend on the Knex driver. This example tests `better-sqlite3` only. PostgreSQL typically returns an object with `rows`; MySQL commonly returns a rows/fields pair. Do not copy the `Row[]` annotation to another driver without checking its result shape and value conversions. The SQL must also be valid for that database and Knex's binding syntax.

## Verified versions

Scripted local checks used Node.js 24.19.0, Reylo and `@reylosql/sqlite` 0.3.0, Knex 3.3.0, better-sqlite3 13.0.3 and TypeScript 7.1.0-beta. The lockfile pins the install. The actual content mapper rejected a string used for the numeric ID, an unknown result property, and an unknown SQL column in separate negative checks; the restored example passed. No application supplied by the original requester or other database driver was tested.

References: [Reylo usage at v0.3.0](https://github.com/colinhacks/reylo/blob/v0.3.0/site/content/sections/02-usage.mdx), [Reylo setup](https://reylo.dev/#setup), [Knex raw bindings and results](https://knexjs.org/guide/raw.html).

## Optional coffee

If this saved you some time, you can buy me a coffee. It is entirely optional; the example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
