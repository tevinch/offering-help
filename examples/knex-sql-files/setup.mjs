import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import Database from "better-sqlite3";

mkdirSync(new URL(".example-data/", import.meta.url), { recursive: true });
const db = new Database(fileURLToPath(new URL(".example-data/example.sqlite", import.meta.url)));
try {
  db.exec(`
    create table if not exists people (
      id integer primary key,
      name text not null,
      note text
    ) strict;
  `);
  const insert = db.prepare("insert into people (id, name, note) values (?, ?, ?)");
  db.transaction(() => {
    db.prepare("delete from people").run();
    insert.run(1, "Ada", null);
    insert.run(2, "Ada Lovelace", "mathematics");
    insert.run(3, "O'Brien :id?", "literal text");
    insert.run(4, "Grace", "compilers");
  })();
} finally {
  db.close();
}
console.log("Created the four-row example database in .example-data/example.sqlite");
