#!/usr/bin/env python3
"""Validate with a fresh local PostgreSQL cluster; no existing database is used."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
DOTNET = os.environ.get("DOTNET", "dotnet")
PG_BIN = os.environ.get("PG_BIN", "")


def pg(name):
    candidate = str(Path(PG_BIN) / name) if PG_BIN else shutil.which(name)
    if not candidate or not Path(candidate).is_file():
        raise RuntimeError(f"Install PostgreSQL tools or set PG_BIN (missing {name}).")
    return candidate


def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, **kwargs)


def main():
    # Check prerequisites before creating a cluster. Unix sockets need a short path.
    commands = {name: pg(name) for name in ("initdb", "pg_ctl", "psql")}
    run([DOTNET, "restore", "--locked-mode"])
    run([DOTNET, "restore", "checks/IntegrationChecks.csproj", "--locked-mode"])
    run([DOTNET, "build", "checks/IntegrationChecks.csproj", "--no-restore"])
    with tempfile.TemporaryDirectory(prefix="reader-", dir="/tmp") as directory:
        work = Path(directory)
        socket = work / "socket"
        socket.mkdir(mode=0o700)
        cluster = work / "db"
        started = False
        try:
            run([commands["initdb"], "-D", str(cluster), "--username=reader_demo",
                 "--auth-local=trust", "--auth-host=reject", "--encoding=UTF8", "--no-locale"],
                stdout=subprocess.DEVNULL)
            # No TCP listener; trust applies only inside this private temporary directory.
            run([commands["pg_ctl"], "-D", str(cluster), "-l", str(work / "postgres.log"),
                 "-o", f"-k {socket} -c listen_addresses='' -c unix_socket_permissions=0700", "-w", "start"],
                stdout=subprocess.DEVNULL)
            started = True
            run([commands["psql"], "-X", "-h", str(socket), "-U", "reader_demo", "-d", "postgres",
                 "-f", "checks/fixture.sql"], stdout=subprocess.DEVNULL)
            env = dict(os.environ, READER_CONNECTION_STRING=
                       f"Host={socket};Username=reader_demo;Database=postgres;Timeout=5;Command Timeout=15")
            run([DOTNET, "run", "--project", "checks/IntegrationChecks.csproj", "--no-build"], env=env)
            # Verify the ordinary executable's final stdout independently from its checks.
            expected = [{"Id": 1, "Name": "Ada Lovelace", "Nickname": None},
                        {"Id": 2, "Name": "Grace Hopper", "Nickname": "Amazing Grace"},
                        {"Id": 3, "Name": "José García", "Nickname": ""}]
            for prefix, rows in (("", expected), ("Ada", expected[:1]), ("Missing", [])):
                output = run([DOTNET, "run", "--no-build", "--", prefix], env=env, capture_output=True)
                if json.loads(output.stdout) != rows:
                    raise AssertionError(f"CLI final output mismatch for prefix {prefix!r}.")
            print("PASS CLI complete JSON output for multiple, one and zero rows", flush=True)
        finally:
            if started or (cluster / "postmaster.pid").exists():
                run([commands["pg_ctl"], "-D", str(cluster), "-m", "fast", "-w", "stop"],
                    stdout=subprocess.DEVNULL)
                status = subprocess.run([commands["pg_ctl"], "-D", str(cluster), "status"],
                                        text=True, capture_output=True)
                if status.returncode != 3:
                    raise RuntimeError("Temporary PostgreSQL cluster did not stop.")
                print("PASS temporary PostgreSQL stopped; private files removed on exit", flush=True)


if __name__ == "__main__":
    main()
