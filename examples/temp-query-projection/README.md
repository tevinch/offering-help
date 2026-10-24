# Use one projection for list and chunked queries

After `WithTempQuery`, select the member paths that the temporary query actually projects. Two expressions can refer to the same conceptual ID while following different mapped paths.

In [this example's motivating question](https://github.com/dotnetcore/FreeSql/issues/2288), the two final projections differ:

```csharp
// Chunk snippet:
CaseId = s.ProcInfo!.CaseId

// List snippet:
CaseId = s.ProcInfo!.CaseInfo.Id
```

The intermediate projection creates `ProcInfo.CaseInfo.Id`, but does not assign `ProcInfo.CaseId`. Start by using the working list expression in both operations. This avoids introducing an unprojected member when changing how results are consumed.

`Program.cs` defines one complete, 16-field `Expression<Func<CaseProcSchedule, ProductivityInfo>>`. Both calls use it:

```csharp
var listRows = await Query(db).ToListAsync(projection);

await foreach (var batch in Query(db).ToChunkAsyncEnumerable(projection, 10))
{
    // Consume this batch before requesting the next one.
}
```

`Query(db)` creates a fresh query with the same filters and order each time. The example keeps the nested temporary projection rather than replacing it with a different database design.

## Run

Requires the .NET 10 SDK and Python 3. Dependencies are fixed in `packages.lock.json`: FreeSql's SQLiteCore and SQL Server providers 3.5.311, and SQLitePCLRaw's SQLite bundle 3.0.5.

```sh
python3 verify.py
```

If the SDK is not on `PATH`, set `DOTNET` to its executable. The script restores in locked mode, builds, and checks the actual executable.

To inspect one result directly:

```sh
dotnet restore --locked-mode
dotnet run -c Release --no-restore -- --count 23
```

It prints JSON containing the complete list result, batches of 10/10/3, the executed SQLite SQL, before/after source records and separately generated SQL Server SQL. It uses a private in-memory SQLite database; it does not open or update an existing database.

## What is checked

- Five related tables, the nested temporary projection and all 16 final output fields.
- Date, case-type and user filters, with three nonmatching source records that must remain stored.
- Zero, one and 23 matching rows; complete values, deterministic order and batch boundaries.
- Unicode, null/default values and unchanged source records after both reads.
- Independent observation of both executed SELECT statements, so omitting either operation fails validation.
- The unprojected-member baseline exits with an error and no partial JSON output. On this SQLite setup it fails during expression processing; it is not a reproduction of the original SQL Server exception.

SQL Server 3.5.311 is used only to generate the equivalent SQL, including the original inner-source `WithLock()` placement. The connection factory deliberately throws if anything attempts a SQL Server connection. The generated outer SELECT uses `a.[Id]` and introduces no extra outer navigation JOIN. This is SQL-generation evidence, **not execution on SQL Server**, validation of locking behavior or a claim that the original application's error is fixed.

The example was checked with .NET SDK 10.0.402 on macOS arm64. These are scripted checks. The original application's complete model, provider version and production data still need testing. `WithCancellation(CancellationToken.None)` preserves the enumeration form; cancellation behavior is not evaluated here.

If two genuinely identical expressions still behave differently in your application, preserve that smaller reproduction for the maintainers. This example changes consumer usage, not FreeSql source.

References: [FreeSql query documentation](https://github.com/dotnetcore/FreeSql/wiki/Query-Data), [public `ISelect` API](https://github.com/dotnetcore/FreeSql/blob/master/FreeSql/Interface/Curd/ISelect/ISelect1.cs).

## Optional coffee

If this example saves you some time, you're welcome to buy me a coffee. It is entirely optional; the example stays free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
