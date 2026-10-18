package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"time"

	"example.com/sqlc-batch/internal/batchdb"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
)

func main() {
	if err := command(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func command() error {
	socket := flag.String("socket", "", "private PostgreSQL Unix socket directory (use ./run.sh)")
	flag.Parse()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	conn, err := connect(ctx, *socket)
	if err != nil {
		return err
	}
	defer func() {
		closeCtx, closeCancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer closeCancel()
		_ = conn.Close(closeCtx)
	}()
	return run(ctx, conn, os.Stdout)
}

func run(ctx context.Context, conn *pgx.Conn, out io.Writer) error {
	// Setup is outside SendBatch: pgx may prepare all statements before any run.
	if _, err := conn.Exec(ctx, `CREATE TEMP TABLE sqlc_batch_items (id integer PRIMARY KEY, note text NOT NULL); INSERT INTO sqlc_batch_items VALUES (0, 'keep existing content')`); err != nil {
		return err
	}
	var version string
	if err := conn.QueryRow(ctx, "SHOW server_version").Scan(&version); err != nil {
		return err
	}
	fmt.Fprintf(out, "PostgreSQL %s; pgx 5.11.0; sqlc 1.31.1 generated :batchexec\n", version)
	queries := batchdb.New(conn)
	want := map[int32]string{0: "keep existing content"}

	// Ordinary result processing: every input index is recorded outside callback.
	results := queries.InsertItem(ctx, items(1))
	var indexes []int
	var resultErrors []error
	results.Exec(func(i int, err error) { indexes = append(indexes, i); resultErrors = append(resultErrors, err) })
	closeErr := results.Close()
	if err := errors.Join(append(resultErrors, closeErr)...); err != nil {
		return err
	}
	if err := checkIndexes(indexes, 3); err != nil {
		return err
	}
	addExpected(want, items(1))
	if err := checkState(ctx, conn, want); err != nil {
		return err
	}
	fmt.Fprintf(out, "normal: indexes=%v, new rows=3\n", indexes)

	// No Exec callback runs here. Close drains all three already-sent inserts.
	results = queries.InsertItem(ctx, items(4))
	if err := results.Close(); err != nil {
		return err
	}
	if err := results.Close(); err != nil {
		return err
	}
	addExpected(want, items(4))
	if err := checkState(ctx, conn, want); err != nil {
		return err
	}
	fmt.Fprintln(out, "Close before Exec: new rows=3")

	// Closing the wrapper changes later callbacks, not the submitted SQL.
	results = queries.InsertItem(ctx, items(7))
	indexes, resultErrors = nil, nil
	var earlyCloseErr error
	results.Exec(func(i int, err error) {
		indexes = append(indexes, i)
		resultErrors = append(resultErrors, err)
		if i == 0 {
			earlyCloseErr = results.Close()
		}
	})
	closeErr = results.Close()
	if err := checkIndexes(indexes, 3); err != nil {
		return err
	}
	if err := errors.Join(resultErrors[0], earlyCloseErr, closeErr); err != nil {
		return err
	}
	for _, err := range resultErrors[1:] {
		if !errors.Is(err, batchdb.ErrBatchAlreadyClosed) {
			return fmt.Errorf("expected closed-result error, got %v", err)
		}
	}
	addExpected(want, items(7))
	if err := checkState(ctx, conn, want); err != nil {
		return err
	}
	fmt.Fprintf(out, "Close inside callback 0: indexes=%v, closed-result errors=2, new rows=3\n", indexes)

	// The later duplicate rolls back this entire implicit batch, not earlier work.
	args := []batchdb.InsertItemParams{{ID: 10, Note: "ten"}, {ID: 11, Note: "eleven"}, {ID: 10, Note: "duplicate"}, {ID: 12, Note: "after error"}}
	results = queries.InsertItem(ctx, args)
	indexes, resultErrors = nil, nil
	results.Exec(func(i int, err error) { indexes = append(indexes, i); resultErrors = append(resultErrors, err) })
	closeErr = results.Close()
	if err := checkIndexes(indexes, 4); err != nil {
		return err
	}
	if err := errors.Join(resultErrors[:2]...); err != nil {
		return err
	}
	for _, err := range append(resultErrors[2:], closeErr) {
		var pgErr *pgconn.PgError
		if !errors.As(err, &pgErr) || pgErr.Code != "23505" {
			return fmt.Errorf("expected duplicate-key error, got %v", err)
		}
	}
	if again := results.Close(); again != closeErr {
		return fmt.Errorf("repeated Close did not retain the batch error")
	}
	if err := checkState(ctx, conn, want); err != nil {
		return err
	}
	fmt.Fprintf(out, "duplicate key: indexes=%v, Close SQLSTATE=23505, new rows=0\n", indexes)

	results = queries.InsertItem(ctx, nil)
	indexes = nil
	results.Exec(func(i int, err error) { indexes = append(indexes, i) })
	closeErr = results.Close()
	if err := errors.Join(closeErr, results.Close()); err != nil {
		return err
	}
	if err := checkIndexes(indexes, 0); err != nil {
		return err
	}
	if err := checkState(ctx, conn, want); err != nil {
		return err
	}
	fmt.Fprintln(out, "empty batch: callbacks=0; repeated Close succeeded")
	fmt.Fprintln(out, "sentinel unchanged; connection idle and reusable after every case")
	return nil
}

func items(start int32) []batchdb.InsertItemParams {
	var args []batchdb.InsertItemParams
	for id := start; id < start+3; id++ {
		args = append(args, batchdb.InsertItemParams{ID: id, Note: fmt.Sprintf("item %d", id)})
	}
	return args
}

func addExpected(want map[int32]string, args []batchdb.InsertItemParams) {
	for _, arg := range args {
		want[arg.ID] = arg.Note
	}
}

func checkIndexes(indexes []int, count int) error {
	if len(indexes) != count {
		return fmt.Errorf("callback indexes=%v, want %d results", indexes, count)
	}
	for i, index := range indexes {
		if i != index {
			return fmt.Errorf("callback position %d reports index %d", i, index)
		}
	}
	return nil
}

func checkState(ctx context.Context, conn *pgx.Conn, want map[int32]string) error {
	if status := conn.PgConn().TxStatus(); status != 'I' {
		return fmt.Errorf("transaction status=%c, want idle I", status)
	}
	rows, err := conn.Query(ctx, "SELECT id, note FROM sqlc_batch_items ORDER BY id")
	if err != nil {
		return err
	}
	got, err := pgx.CollectRows(rows, pgx.RowToStructByPos[batchdb.SqlcBatchItem])
	if err != nil {
		return err
	}
	if len(got) != len(want) {
		return fmt.Errorf("actual SQL row count=%d, want %d", len(got), len(want))
	}
	for _, row := range got {
		if note, ok := want[row.ID]; !ok || note != row.Note {
			return fmt.Errorf("unexpected actual SQL row: %+v", row)
		}
	}
	var answer int
	if err := conn.QueryRow(ctx, "SELECT 42").Scan(&answer); err != nil {
		return err
	}
	if answer != 42 {
		return fmt.Errorf("connection reuse returned %d", answer)
	}
	return nil
}
