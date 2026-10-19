#!/usr/bin/env bash
set -euo pipefail

example_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_command="${PYTHON:-python3}"
venv_dir="$(mktemp -d "${TMPDIR:-/tmp}/pyarrow-check.XXXXXX")"
trap 'rm -rf -- "$venv_dir"' EXIT

"$python_command" -I -m venv "$venv_dir"
PIP_CONFIG_FILE=/dev/null "$venv_dir/bin/python" -I -m pip --isolated install \
    --no-cache-dir --only-binary=:all: --disable-pip-version-check \
    -r "$example_dir/requirements.txt"
"$venv_dir/bin/python" -I "$example_dir/verify.py"
