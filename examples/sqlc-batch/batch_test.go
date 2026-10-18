package main

import (
	"bytes"
	"context"
	"errors"
	"flag"
	"fmt"
	"reflect"
	"strings"
	"testing"
	"time"

	"example.com/sqlc-batch/internal/batchdb"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
)

var testSocket = flag.String("socket", "", "private PostgreSQL Unix socket directory (use ./run.sh)")

func testConnection(t *testing.T) (context.Context, *pgx.Conn) {
	t.Helper()
	if *testSocket == "" {
		t.Fatal("real PostgreSQL required: ./run.sh, or go test -args -socket /absolute/private/socket")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	t.Cleanup(cancel)
	conn, err := connect(ctx, *testSocket)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = conn.Close(context.Background()) })
	return ctx, conn
}

func testDB(t *testing.T) (context.Context, *pgx.Conn) {
	t.Helper()
	ctx, conn := testConnection(t)
	_, err := conn.Exec(ctx, `CREATE TEMP TABLE sqlc_batch_items (id integer PRIMARY KEY, note text NOT NULL); INSERT INTO sqlc_batch_items VALUES (0, 'keep existing content')`)
	if err != nil {
		t.Fatal(err)
	}
	return ctx, conn
}

func assertRows(t *testing.T, ctx context.Context, conn *pgx.Conn, want map[int32]string) {
	t.Helper()
	if status := conn.PgConn().TxStatus(); status != 'I' {
		t.Fatalf("transaction status = %c, want idle I", status)
	}
	rows, err := conn.Query(ctx, "SELECT id, note FROM sqlc_batch_items ORDER BY id")
	if err != nil {
		t.Fatal(err)
	}
	got := map[int32]string{}
	for rows.Next() {
		var id int32
		var note string
		if err := rows.Scan(&id, &note); err != nil {
			t.Fatal(err)
		}
		got[id] = note
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	rows.Close()
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("actual SQL rows = %#v, want %#v", got, want)
	}
	var answer int
	if err := conn.QueryRow(ctx, "SELECT 42").Scan(&answer); err != nil || answer != 42 {
		t.Fatalf("connection reuse: value=%d error=%v", answer, err)
	}
}

func threeItems() []batchdb.InsertItemParams {
	return []batchdb.InsertItemParams{{ID: 1, Note: "one"}, {ID: 2, Note: "two"}, {ID: 3, Note: "three"}}
}

func TestCloseBeforeReadDrainsBatchAndLeavesAllValidRows(t *testing.T) {
	ctx, conn := testDB(t)
	results := batchdb.New(conn).InsertItem(ctx, threeItems())
	if err := results.Close(); err != nil {
		t.Fatal(err)
	}
	assertRows(t, ctx, conn, allRows())
	if err := results.Close(); err != nil {
		t.Fatalf("repeated Close: %v", err)
	}
}

type observedResult struct {
	index int
	err   error
}

func assertIndexes(t *testing.T, got []observedResult, count int) {
	t.Helper()
	if len(got) != count {
		t.Fatalf("callbacks = %d, want %d: %#v", len(got), count, got)
	}
	for i, result := range got {
		if result.index != i {
			t.Fatalf("callback position %d reports index %d", i, result.index)
		}
	}
}

func allRows() map[int32]string {
	return map[int32]string{0: "keep existing content", 1: "one", 2: "two", 3: "three"}
}

func TestNormalIndexesAndConnectionReuse(t *testing.T) {
	ctx, conn := testDB(t)
	results := batchdb.New(conn).InsertItem(ctx, threeItems())
	var got []observedResult
	results.Exec(func(i int, err error) { got = append(got, observedResult{i, err}) })
	closeErr := results.Close()
	assertIndexes(t, got, 3)
	for _, result := range got {
		if result.err != nil {
			t.Fatalf("input %d: %v", result.index, result.err)
		}
	}
	if closeErr != nil {
		t.Fatal(closeErr)
	}
	assertRows(t, ctx, conn, allRows())
	if err := results.Close(); err != nil {
		t.Fatalf("repeated Close: %v", err)
	}
}

func TestCloseInsideCallbackSkipsResultsButDoesNotCancelSQL(t *testing.T) {
	ctx, conn := testDB(t)
	results := batchdb.New(conn).InsertItem(ctx, threeItems())
	var got []observedResult
	var earlyCloseErr error
	results.Exec(func(i int, err error) {
		got = append(got, observedResult{i, err})
		if i == 0 {
			earlyCloseErr = results.Close()
		}
	})
	closeErr := results.Close()
	assertIndexes(t, got, 3)
	if got[0].err != nil || earlyCloseErr != nil || closeErr != nil {
		t.Fatalf("first=%v early Close=%v final Close=%v", got[0].err, earlyCloseErr, closeErr)
	}
	for _, result := range got[1:] {
		if !errors.Is(result.err, batchdb.ErrBatchAlreadyClosed) {
			t.Fatalf("input %d: %v, want ErrBatchAlreadyClosed", result.index, result.err)
		}
	}
	assertRows(t, ctx, conn, allRows())
}

func TestDuplicateKeyRollsBackImplicitBatchAndPreservesEarlierRows(t *testing.T) {
	ctx, conn := testDB(t)
	if _, err := conn.Exec(ctx, "INSERT INTO sqlc_batch_items VALUES (50, 'earlier committed row')"); err != nil {
		t.Fatal(err)
	}
	args := []batchdb.InsertItemParams{{ID: 1, Note: "one"}, {ID: 2, Note: "two"}, {ID: 1, Note: "duplicate"}, {ID: 3, Note: "after error"}}
	results := batchdb.New(conn).InsertItem(ctx, args)
	var got []observedResult
	results.Exec(func(i int, err error) { got = append(got, observedResult{i, err}) })
	closeErr := results.Close()
	assertIndexes(t, got, 4)
	if got[0].err != nil || got[1].err != nil {
		t.Fatalf("early result errors: %v %v", got[0].err, got[1].err)
	}
	for _, result := range got[2:] {
		var pgErr *pgconn.PgError
		if !errors.As(result.err, &pgErr) || pgErr.Code != "23505" {
			t.Fatalf("input %d: %v, want duplicate-key error", result.index, result.err)
		}
	}
	var pgErr *pgconn.PgError
	if !errors.As(closeErr, &pgErr) || pgErr.Code != "23505" {
		t.Fatalf("final Close: %v, want duplicate-key error", closeErr)
	}
	if again := results.Close(); again != closeErr {
		t.Fatalf("repeated Close = %v, want same error %v", again, closeErr)
	}
	assertRows(t, ctx, conn, map[int32]string{0: "keep existing content", 50: "earlier committed row"})
}

func TestEmptyBatchAndRepeatedCloseLeaveConnectionReusable(t *testing.T) {
	ctx, conn := testDB(t)
	results := batchdb.New(conn).InsertItem(ctx, nil)
	var got []observedResult
	results.Exec(func(i int, err error) { got = append(got, observedResult{i, err}) })
	closeErr, again := results.Close(), results.Close()
	assertIndexes(t, got, 0)
	if closeErr != nil || again != nil {
		t.Fatalf("empty Close errors: %v %v", closeErr, again)
	}
	assertRows(t, ctx, conn, map[int32]string{0: "keep existing content"})
	// Reuse the same connection for another generated batch, not just a ping.
	next := batchdb.New(conn).InsertItem(ctx, threeItems())
	var nextResults []observedResult
	next.Exec(func(i int, err error) { nextResults = append(nextResults, observedResult{i, err}) })
	finalErr := next.Close()
	assertIndexes(t, nextResults, 3)
	for _, result := range nextResults {
		if result.err != nil {
			t.Fatal(result.err)
		}
	}
	if finalErr != nil {
		t.Fatal(finalErr)
	}
	assertRows(t, ctx, conn, allRows())
}

func TestExplicitSocketIgnoresAmbientDatabaseSelection(t *testing.T) {
	for key, value := range map[string]string{
		"PGHOST": "invalid.example", "PGPORT": "1", "PGUSER": "unused",
		"PGDATABASE": "unused", "PGPASSWORD": "unused", "PGSERVICE": "",
		"PGSERVICEFILE": "/nonexistent/service", "PGPASSFILE": "/nonexistent/password",
		"PGOPTIONS": "-c search_path=unused", "PGSSLMODE": "verify-full",
	} {
		t.Setenv(key, value)
	}
	ctx, conn := testDB(t)
	assertRows(t, ctx, conn, map[int32]string{0: "keep existing content"})
}

func TestMissingSocketFailsBeforeDatabaseSelection(t *testing.T) {
	conn, err := connect(context.Background(), "")
	if err == nil || conn != nil {
		t.Fatalf("missing explicit socket: conn=%v error=%v", conn, err)
	}
}

func TestServiceSelectionIsRejectedBeforeReadingServiceFiles(t *testing.T) {
	t.Setenv("PGSERVICE", "unused")
	t.Setenv("PGSERVICEFILE", "/nonexistent/service")
	conn, err := connect(context.Background(), *testSocket)
	if err == nil || conn != nil {
		t.Fatalf("service selection: conn=%v error=%v", conn, err)
	}
}

func TestRunnableExampleCompletesAllCasesAndLeavesExpectedRows(t *testing.T) {
	ctx, conn := testConnection(t)
	var out bytes.Buffer
	if err := run(ctx, conn, &out); err != nil {
		t.Fatal(err)
	}
	for _, line := range []string{
		"normal: indexes=[0 1 2], new rows=3",
		"Close before Exec: new rows=3",
		"Close inside callback 0: indexes=[0 1 2], closed-result errors=2, new rows=3",
		"duplicate key: indexes=[0 1 2 3], Close SQLSTATE=23505, new rows=0",
		"empty batch: callbacks=0; repeated Close succeeded",
		"sentinel unchanged; connection idle and reusable after every case",
	} {
		if !strings.Contains(out.String(), line) {
			t.Fatalf("missing observed output %q in:\n%s", line, out.String())
		}
	}
	want := map[int32]string{0: "keep existing content"}
	for id := int32(1); id <= 9; id++ {
		want[id] = fmt.Sprintf("item %d", id)
	}
	assertRows(t, ctx, conn, want)
}
