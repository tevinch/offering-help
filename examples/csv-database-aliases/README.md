# CSV aliases from a database

Accept a new CSV column name by adding a database row, then run the same compiled program again. This complete example loads the original three-column alias table, builds CsvHelper name mappings for six typed properties, and returns the imported records as JSON.

CsvHelper already accepts an array of alternative names in `.Name(...)`. The aliases can come from a database; they do not need to be literals in the mapping constructor. This example uses native CsvHelper APIs and a fixed C# model.

The project targets .NET 10 and pins CsvHelper 33.1.0 and Microsoft.Data.Sqlite 10.0.13. Scripted validation used .NET SDK 10.0.402. The dependencies are recorded in `packages.lock.json`. MIT licensed; see [LICENSE](LICENSE).

## Run the complete checks

Install the .NET 10 SDK and Python 3, then run from this directory:

```sh
python3 validate.py
```

If the SDK is outside `PATH`, set `DOTNET` to its executable:

```sh
DOTNET=/path/to/dotnet python3 validate.py
```

The script restores locked dependencies and builds once. It creates a temporary SQLite database with all 18 original alias rows, imports two CSV records, and checks all six properties. A file using the new `EventNumber` header must fail first. The script adds that alias to the database and invokes the same DLL again; the import must then return the expected records. It checks the DLL's SHA-256 before and after the sequence. No database service or existing database is used. The first restore requires NuGet access.

The 31 scripted checks also cover all original aliases, reordered columns, quoted commas, quotes, newlines, Unicode, empty strings, header-only files, unmapped extra columns, missing headers and fields, malformed quoting, invalid and overflowing decimals, invalid metadata, ambiguous aliases, and successful use after failures. A late invalid row must produce no partial JSON. These are local software checks, not confirmation that the original requester has adopted the example.

## Try a database-only change

Build once:

```sh
dotnet restore --locked-mode
dotnet build -c Release --no-restore
```

Create a fresh demonstration database from [fixtures/aliases.sql](fixtures/aliases.sql):

```sh
python3 - <<'PY'
from pathlib import Path
import sqlite3

path = Path("aliases.db")
if path.exists():
    raise SystemExit("aliases.db already exists; choose a fresh directory for this demo.")
with sqlite3.connect(path) as connection:
    connection.executescript(Path("fixtures/aliases.sql").read_text())
PY
dotnet bin/Release/net10.0/CsvRuntimeMap.dll aliases.db fixtures/original.csv
```

The output contains the complete records:

```json
[{"EventId":"EV-001","Period":"2026","MeanLossAmount":12.50,"DayInPeriod":"4","PerilZone":"North, coast","CatalogueTypeCode":"TYPE-A"},{"EventId":"EV-002","Period":"2027","MeanLossAmount":0,"DayInPeriod":"","PerilZone":"南","CatalogueTypeCode":"TYPE-B"}]
```

The program's JSON encoder may escape non-ASCII characters; the decoded values are the same. Next, the new-header fixture fails with a `HeaderValidationException` because `EventNumber` is not yet configured:

```sh
dotnet bin/Release/net10.0/CsvRuntimeMap.dll aliases.db fixtures/new-alias.csv
```

Add one alias, then invoke the same executable again:

```sh
python3 - <<'PY'
import sqlite3

with sqlite3.connect("aliases.db") as connection:
    connection.execute(
        "INSERT INTO CsvColumnMappings (CsvColumnName, PropertyName, DataType) VALUES (?, ?, ?)",
        ("EventNumber", "EventId", "String"),
    )
PY
dotnet bin/Release/net10.0/CsvRuntimeMap.dll aliases.db fixtures/new-alias.csv
```

It now returns the same records without a rebuild. The importer opens the database read-only and loads a fresh alias snapshot each time it starts. A change made after an import has started applies to the next import.

## Use it in an application

[AliasCatalog.cs](AliasCatalog.cs) reads `CsvColumnName`, `PropertyName` and `DataType` from `CsvColumnMappings`. The table name is an example choice. The fixture preserves the original question's column names and all 18 rows. SQLite provides a portable, local demonstration; this example does not test a SQL Server or other production database. For another provider, replace the connection and fixed SELECT while keeping the same metadata validation and mapping inputs.

[CsvImport.cs](CsvImport.cs) registers an already-created map instance. Each typed member receives the names loaded for that property:

```csharp
Map(record => record.EventId)
    .Name(catalog.NamesFor(nameof(ImportRecord.EventId)));
```

The five string properties are `EventId`, `Period`, `DayInPeriod`, `PerilZone` and `CatalogueTypeCode`. `MeanLossAmount` is a `decimal`. The database's `DataType` values are checked against these exact types: `String` for those five members and `Decimal` for `MeanLossAmount`. They describe the existing model; they do not create CLR types or change properties at runtime. Adding an alias needs only a metadata row. Adding a new model property or changing its type requires a deliberate model and mapping change.

Names use exact, case-sensitive matching. The original table spells the first alias `EventID`; add a separate `EventId` alias if that spelling occurs in your files. Values are not trimmed or rewritten. CSV empty strings remain empty strings. Empty, invalid or overflowing decimals fail conversion; this example uses `InvariantCulture`, including a period as the decimal separator. It does not configure special textual null tokens or domain validation for the string fields.

The loader rejects SQL NULL metadata, blank aliases, unknown properties, mismatched types, missing property mappings and an alias assigned to two different properties. Repeated identical metadata rows are harmless. Each CSV must supply exactly one matching column for every required property; two aliases for the same property in one header are rejected so there is no silent precedence choice. Unmapped extra columns remain ignored under the explicit map.

CsvHelper's normal header, missing-field and bad-data handlers remain enabled. The example only disables raw-record text in exception messages. It reads and serializes the complete result before writing JSON; failures exit nonzero and write an error to stderr. This buffers the result in memory. Adapt the output step for very large imports with an explicit policy for committing or rolling back partial work.

References: [original question](https://github.com/JoshClose/CsvHelper/discussions/2328), [CsvHelper alternate-name mapping](https://joshclose.github.io/CsvHelper/examples/configuration/class-maps/mapping-by-alternate-names/), [CsvHelper reading and culture guidance](https://joshclose.github.io/CsvHelper/getting-started/), and [Microsoft.Data.Sqlite usage](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/).

## Optional coffee

The example is free. If it helps and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
