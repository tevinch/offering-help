package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	"github.com/jackc/pgx/v5"
)

// Only an explicitly supplied private Unix socket is accepted. No ambient DSN,
// password file, service configuration or TCP fallback selects the database.
func connect(ctx context.Context, socket string) (*pgx.Conn, error) {
	if !filepath.IsAbs(socket) {
		return nil, fmt.Errorf("supply an absolute private socket directory; ./run.sh creates one")
	}
	info, err := os.Lstat(socket)
	if err != nil {
		return nil, err
	}
	if !info.IsDir() || info.Mode().Perm()&0077 != 0 {
		return nil, fmt.Errorf("socket directory must be a private directory (mode 0700)")
	}
	if os.Getenv("PGSERVICE") != "" {
		return nil, fmt.Errorf("unset PGSERVICE or use ./run.sh; this example does not read service files")
	}
	config, err := pgx.ParseConfig("postgres://tevinch@localhost:5432/postgres?sslmode=disable&passfile=/dev/null&options=&target_session_attrs=any&connect_timeout=5")
	if err != nil {
		return nil, err
	}
	config.Host, config.Port, config.Password = socket, 5432, ""
	config.Fallbacks = nil
	config.RuntimeParams = map[string]string{"application_name": "sqlc-batch", "search_path": "pg_temp,pg_catalog"}
	return pgx.ConnectConfig(ctx, config)
}
