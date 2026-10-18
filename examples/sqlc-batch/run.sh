#!/bin/sh
set -eu
cd "$(dirname "$0")"
for tool in go initdb pg_ctl; do
  command -v "$tool" >/dev/null 2>&1 || { printf '%s\n' "Missing $tool; install Go and PostgreSQL, then retry." >&2; exit 1; }
done

# This run owns a fresh cluster. Never select an existing server from PG* vars.
unset PGHOST PGHOSTADDR PGPORT PGDATABASE PGUSER PGPASSWORD PGPASSFILE
unset PGSERVICE PGSERVICEFILE PGOPTIONS PGSSLMODE PGREQUIRESSL
unset PGSSLCERT PGSSLKEY PGSSLROOTCERT PGSSLCRL PGSSLCRLDIR
unset PGTARGETSESSIONATTRS PGCHANNELBINDING PGCONNECT_TIMEOUT
umask 077
work=$(mktemp -d /tmp/sqlc-batch.XXXXXX)
cluster=$work/data
socket=$work/socket
mkdir "$socket"
attempted=no
cleanup() {
  if [ "$attempted" = yes ] && pg_ctl -D "$cluster" status >/dev/null 2>&1; then
    pg_ctl -D "$cluster" -m fast -w stop >/dev/null || {
      printf '%s\n' "Could not stop the example server. Preserved directory: $work" >&2
      return 1
    }
  elif [ -e "$cluster/postmaster.pid" ]; then
    printf '%s\n' "Server state is uncertain. Preserved directory: $work" >&2
    return 1
  fi
  rm -rf "$work"
}
finish() {
  status=$?
  trap - EXIT
  cleanup || status=1
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
initdb -D "$cluster" -U tevinch --auth=trust --no-locale --encoding=UTF8 >"$work/init.log" 2>&1 || { cat "$work/init.log" >&2; exit 1; }
# Short Unix socket path, private directory, and no TCP listener.
printf "\nlisten_addresses = ''\nunix_socket_directories = '%s'\nport = 5432\n" "$socket" >>"$cluster/postgresql.conf"
attempted=yes
pg_ctl -D "$cluster" -l "$work/server.log" -w start >/dev/null || { cat "$work/server.log" >&2; exit 1; }
go test -mod=readonly -count=1 -v ./... -args -socket "$socket"
go run -mod=readonly . -socket "$socket"
