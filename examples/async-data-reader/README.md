# Async data reader with CSLA

A complete, local console example of awaiting ADO.NET reads through CSLA. The caller awaits `IDataPortal<PersonList>.FetchAsync`, an attributed async `[Fetch]` method awaits an injected DAL, and the DAL awaits Npgsql's connection, command and row-reading operations. The returned CSLA list contains the completed query results.

The project targets .NET 10 and pins CSLA 10.2.0 and Npgsql 10.0.3. Scripted validation used .NET SDK 10.0.402 and PostgreSQL 18.6. Dependency versions are recorded in both `packages.lock.json` files. MIT licensed; see [LICENSE](LICENSE).

## Run the checks

On macOS or Linux, install the .NET 10 SDK, Python 3 and PostgreSQL server tools (`initdb`, `pg_ctl`, `psql`). Run as an ordinary user; PostgreSQL does not allow `initdb` as root.

```sh
python3 validate.py
```

If PostgreSQL tools are outside `PATH`, set `PG_BIN` to their directory. If the SDK is outside `PATH`, set `DOTNET` to its executable:

```sh
PG_BIN=/path/to/postgresql/bin DOTNET=/path/to/dotnet python3 validate.py
```

The script restores locked dependencies, builds both projects, and creates a fresh private temporary PostgreSQL cluster with TCP disabled. It loads only its own fixture, runs the checks and verifies the console program's JSON. The temporary server stops in `finally`, including on a failing check. It does not connect to an existing database. NuGet access is needed for the initial restore.

The checks use real PostgreSQL queries. A test-only view introduces `pg_sleep`; a separate connection observes the expected active query and `PgSleep` in `pg_stat_activity`. Both a direct DAL call and a CSLA fetch must return a pending task promptly, allow other caller work, and eventually return the exact result. Testing the DAL directly matters because CSLA's local console portal schedules work internally: portal responsiveness alone does not prove a provider uses asynchronous IO.

Other checks cover zero/one/multiple rows, Unicode, SQL `NULL` versus an empty string, parameterized input, a real provider error followed by a successful retry, unchanged existing data and DAL cancellation. These are scripted integration checks, not UI tests or evidence for another provider.

## Use the console caller

For an ordinary database, the example expects a `person_directory` table or view with `id integer`, `name text` and nullable `nickname text`. This small schema can be created in a separate demonstration database:

```sql
CREATE TABLE person_directory (
    id integer PRIMARY KEY,
    name text NOT NULL,
    nickname text
);
INSERT INTO person_directory VALUES
    (1, 'Ada Lovelace', NULL),
    (2, 'Grace Hopper', 'Amazing Grace'),
    (3, 'José García', '');
```

Use your PostgreSQL ADO.NET connection string in the environment, then pass a case-sensitive name prefix:

```sh
export READER_CONNECTION_STRING='Host=/path/to/socket;Username=your_user;Database=your_demo_db'
dotnet restore --locked-mode
dotnet run -- Ada
```

Expected JSON:

```json
[{"Id":1,"Name":"Ada Lovelace","Nickname":null}]
```

No argument fetches all rows in ID order. A prefix with no match returns `[]`. Errors exit nonzero without writing a partial JSON result. `Program.cs` is the complete caller; `PersonList.cs` contains the CSLA objects and `[Fetch]`; `PersonDal.cs` contains the database work; `ExampleServices.cs` registers the local portal and injected DAL.

## What changes in an async conversion

In [PersonDal.cs](PersonDal.cs), use `await dataSource.OpenConnectionAsync(token)`, `await command.ExecuteReaderAsync(token)` and `while (await reader.ReadAsync(token))`. Keep the connection, command and reader alive until all rows have been consumed, then dispose them with `await using`. The scalar getters read the current buffered row; `IsDBNull` preserves a nullable nickname instead of treating SQL `NULL` as an empty string. The prefix is a parameter, not concatenated SQL.

In [PersonList.cs](PersonList.cs), make the data portal operation `async Task`, await the DAL result, then populate the list before returning. In the caller, await `FetchAsync` before using the result. There are no blocking task waits or fire-and-forget database calls in this example.

One thread-safe `NpgsqlDataSource` supplies a separate connection for each DAL call. Do not share a connection, command, reader or mutable CSLA object across concurrent operations. This read-only example has no asynchronous business rules; applications with those rules must still decide their concurrency and completion policy.

The optional `CancellationToken` parameter belongs to the DAL. The cancellation check waits until PostgreSQL is actually executing, cancels the provider operation, observes `OperationCanceledException`, and then performs a successful later fetch through the same data source. The CSLA `[Fetch]` uses the default token here. This does not propagate a token through a remote data portal or decide which business operations should continue after a caller disconnects.

This uses native `NpgsqlDataReader`, including explicit null handling. It does not add asynchronous methods to CSLA's `SafeDataReader`. Async behavior depends on the provider; changing a method name alone is not proof of nonblocking database IO.

References: [Npgsql basic usage](https://www.npgsql.org/doc/basic-usage.html), [Npgsql 10.0.3](https://www.nuget.org/packages/Npgsql/10.0.3), [CSLA 10.2.0](https://www.nuget.org/packages/Csla/10.2.0), [stable CSLA portal API](https://github.com/MarimerLLC/csla/blob/v10.2.0/Source/Csla/IDataPortalT.cs), and [stable CSLA local portal implementation](https://github.com/MarimerLLC/csla/blob/v10.2.0/Source/Csla/DataPortalClient/LocalProxy.cs).

## Optional coffee

The example is free. If it helps and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
