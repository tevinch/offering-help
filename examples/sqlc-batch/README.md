# Read sqlc batch results without confusing Close with cancellation

`InsertItem(ctx, args)` sends the whole batch before returning its result object. Generated `Exec` consumes results and invokes the `:batchexec` callback: `i` is the **zero-based position in `args`** and `err` is the error reported for that result. The callback has no return value.

`Close` drains unread results and must finish before connection reuse. It does **not** cancel the SQL already sent. Calling the generated wrapper's `Close` during `Exec` makes later callback indexes report `batchdb.ErrBatchAlreadyClosed`; valid inserts can still have executed. An early nil callback error also does not prove a write committed: without explicit transaction-control statements, pgx runs the batch in an implicit transaction, so a later SQL error rolls it back.

This example uses a session-local temporary table with synthetic rows. It checks actual SQL rows after closing each batch, preserves an existing sentinel row, checks idle transaction status and reuses the same connection. It does not infer SQL effects from callback counts.

## Run

Install Go and PostgreSQL so `go`, `initdb` and `pg_ctl` are in `PATH`. The runner requires a POSIX shell and Unix sockets. Run as an ordinary user; PostgreSQL refuses to initialize as root. Go modules need network access on the first run.

```sh
cd examples/sqlc-batch
./run.sh
```

The script creates its own temporary cluster and private Unix socket under `/tmp`, uses role `tevinch`, disables TCP listening, runs the tests and example, then stops and removes that cluster. It never selects a database from your environment or reads a password file. The temporary trust authentication is confined to that private local directory. No existing cluster or table is changed.

The executable requires an explicit private socket directory; running `go run .` without `-socket` fails. `./run.sh` supplies the socket for both the tests and program and clears `PGSERVICE`. Direct execution rejects a nonempty `PGSERVICE` before reading a service file. If startup or stopping fails, read the error before removing any preserved temporary directory.

## Consuming a result

```go
results := batchdb.New(conn).InsertItem(ctx, args)
var resultErrors []error
results.Exec(func(i int, err error) {
    // args[i] identifies the input. Collect the error outside the callback.
    if err != nil {
        resultErrors = append(resultErrors, fmt.Errorf("input %d: %w", i, err))
    }
})
closeErr := results.Close()
if err := errors.Join(append(resultErrors, closeErr)...); err != nil {
    return err
}
```

Check **both** the collected errors and `closeErr` before reporting success. Generated `Exec` defers the driver's `Close`, but does not return its error; explicitly calling the generated `Close` exposes that error. Repeated Close is safe. Later errors can repeat an earlier batch error, so an error at an index does not establish that its SQL statement independently ran. Do not use callback `return`, Close or panic as a cancellation mechanism.

The runnable cases cover normal results, Close before reading, Close inside callback 0, a duplicate key rolling back an implicit batch, an empty batch and repeated Close. `batch_test.go` checks every expected index, independent exact table contents, the sentinel, transaction status and a separate query on the same connection.

## Regenerate

Generated files are included. To reproduce them, install the official [sqlc 1.31.1 binary](https://github.com/sqlc-dev/sqlc/releases/tag/v1.31.1), then run:

```sh
sqlc version  # v1.31.1
sqlc generate
git diff -- internal/batchdb
./run.sh
```

`schema.sql` is generator input; the program creates a TEMP table before sending a batch. This matters because pgx may prepare all queued statements before executing them. The dependency is pinned to pgx **5.11.0** in `go.mod` and `go.sum`. The executable scope is **`:batchexec`**, PostgreSQL and Go/pgx v5.

## Checked scope

Checked with sqlc **1.31.1**, pgx **5.11.0**, Go **1.27.2** and PostgreSQL **18.6** on macOS arm64, with pgx's default execution mode and no explicit transaction control inside a batch. These are scripted local integration tests of synthetic temporary rows. Temporary rows last for that session; their existence after a batch is not a claim of cross-session storage. The original application's schema and versions are unknown. Remote connection loss, cancellation, pools/proxies, explicit transactions, pgx v4, other engines, `:batchone` and `:batchmany` are outside the tested scope. On connection faults, pgx may close a connection it cannot resynchronize; reuse is demonstrated here for the checked local cases.

References: [sqlc query annotations](https://docs.sqlc.dev/en/latest/reference/query-annotations.html), [sqlc 1.31.1 generated batch code](https://github.com/sqlc-dev/sqlc/blob/v1.31.1/examples/batch/postgresql/batch.go), [pgx 5.11.0 SendBatch](https://github.com/jackc/pgx/blob/v5.11.0/conn.go), [pgx 5.11.0 BatchResults.Close](https://github.com/jackc/pgx/blob/v5.11.0/batch.go), [original question](https://github.com/sqlc-dev/sqlc/issues/4631).

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
