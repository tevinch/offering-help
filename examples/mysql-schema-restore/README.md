# Move a MySQL schema to another server

A dump can create its own schema when it contains `CREATE DATABASE` and `USE`. Import that dump without selecting a default database first. Selecting a missing database fails before the client can execute the dump, even if the file could create it.

This is a native-client workaround for [Database Client #1805](https://github.com/cweijan/vscode-database-client/issues/1805). It restores the transfer workflow; it does not change the extension's Import SQL command. Do not create a database named `undefined` to work around that error.

## Keep the same schema name

Run the export against the source server, replacing the example host, user and schema names. These commands skip local option and login files so a configured default database cannot interfere; supply any required connection options explicitly.

```sh
mysqldump --no-defaults --no-login-paths --host=source.example --user=backup_user -p \
  --default-character-set=utf8mb4 --single-transaction \
  --no-tablespaces --set-gtid-purged=OFF \
  --routines --events --triggers \
  --databases catalog_demo > catalog_demo.sql
```

Check that the export finished successfully before importing. An output file can exist after a failed export. `--databases` includes schema creation and selection; routines and events need the explicit options above, while triggers are included by default.

Import into the destination server **without a database argument**:

```sh
mysql --no-defaults --no-login-paths --host=destination.example --user=restore_user -p \
  --default-character-set=utf8mb4 < catalog_demo.sql
```

Use an empty destination schema. A normal `mysqldump` file drops and recreates its tables, so importing it again can replace destination changes. The destination account needs permission to create the schema and its objects. Stored-object definers and cross-version compatibility may need separate handling. `--single-transaction` gives a consistent snapshot for transactional tables; avoid concurrent schema changes during the export.

Afterward, refresh the destination connection in Database Client and open the restored schema. The [extension's connection guide](https://doc.database-client.com/#/connection?id=cache) explains that its schema metadata is cached. The extension UI itself was not tested here.

## An existing plain dump

A single-schema dump made **without** `--databases` generally omits `CREATE DATABASE` and `USE`. Create and select the destination schema before loading that form:

```sh
mysql --no-defaults --no-login-paths --host=destination.example --user=restore_user -p \
  --execute='CREATE DATABASE catalog_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;'

mysql --no-defaults --no-login-paths --host=destination.example --user=restore_user -p \
  --default-character-set=utf8mb4 catalog_demo < plain_dump.sql
```

For a new plain dump, use the first export command with `catalog_demo` in place of `--databases catalog_demo`. Keep the original schema name. A dump containing `USE catalog_demo` overrides a different command-line target; renaming a schema also requires checking database-qualified references in views or stored programs. Inspect the existing dump's schema-selection statements before choosing which import form to use.

## Try the complete example

Use two disposable MySQL servers. The source and destination must initially have no `catalog_demo` schema. [sample.sql](sample.sql) creates three tables with Unicode, null, decimal and multiline data, plus a view, procedure, trigger and disabled event.

```sh
mysql --no-defaults --no-login-paths --host=source.example --user=restore_user -p \
  --default-character-set=utf8mb4 < sample.sql
```

Export and import with the commands above. Then compare the source and destination using the same query file:

```sh
mysql --no-defaults --no-login-paths --host=source.example --user=backup_user -p \
  --default-character-set=utf8mb4 --batch --skip-column-names \
  catalog_demo < verify.sql > source.tsv

mysql --no-defaults --no-login-paths --host=destination.example --user=restore_user -p \
  --default-character-set=utf8mb4 --batch --skip-column-names \
  catalog_demo < verify.sql > restored.tsv

diff -u source.tsv restored.tsv
```

No differences means the checked rows, view output, procedure result and object metadata match. [expected.tsv](expected.tsv) is the result from the supplied fixture on MySQL 8.4.0.

Validated with MySQL Community Server **8.4.0**, macOS 14 arm64, using two separate local servers with networking disabled. The destination schema was absent before the actual dump/import. The restored foreign key rejected an invalid row; the restored trigger and procedure ran; the disabled event was preserved; source data and an unrelated destination schema stayed unchanged. A plain dump also restored after explicitly creating and selecting a fresh schema with the same name. A repeated import replaced destination-only rows, as expected. These were scripted checks, not the original user's dump or current extension UI.

The [MySQL 8.4 reload guide](https://dev.mysql.com/doc/refman/8.4/en/reloading-sql-format-dumps.html) documents both dump forms. Its [database-copy guide](https://dev.mysql.com/doc/refman/8.4/en/mysqldump-copying-database.html) explains the schema-name distinction.

## Optional coffee

This example is free. If it saved you time, an optional coffee is appreciated.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
