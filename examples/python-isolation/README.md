# PyArrow in a clean Python environment

A shared Python installation can contain packages your project does not need. A fresh virtual environment keeps those packages out of your test environment without changing the shared installation or adding them to your deployment requirements.

This example installs PyArrow 26.0.0 without NumPy, imports it, and writes and reads both Arrow IPC and Parquet files twice. It checks the schema and the Unicode, null, numeric and boolean values after every read.

## Run

Use Python 3.11 or newer on Linux or macOS:

```sh
bash examples/python-isolation/run.sh
```

To select an interpreter explicitly:

```sh
PYTHON=python3.11 bash examples/python-isolation/run.sh
```

The script creates a new temporary venv, uses that venv's Python for installation and execution, and removes the temporary directory when it exits. It does not uninstall or upgrade packages in the shared Python installation. `-I` ignores `PYTHONPATH`, `PYTHONHOME` and the user site directory. `PIP_CONFIG_FILE=/dev/null` disables pip configuration files; `--isolated` ignores pip environment options and user configuration. The example downloads public packages; adapt those settings if your project uses a private package index.

`requirements.txt` contains only PyArrow. NumPy is an [optional PyArrow dependency](https://arrow.apache.org/docs/python/install.html#dependencies); an incompatible installed NumPy is different from an absent NumPy. This check uses Python values and Arrow tables. Operations such as `to_numpy()` and `to_pandas()` still need compatible versions of their respective packages.

## Use the same approach in a test job

Copy `workflow.yml` to `.github/workflows/pyarrow-isolation.yml` in a repository containing this example. It selects Python 3.11 on a self-hosted Linux runner and runs the complete example.

For an application, create the venv after `setup-python`, then install your existing requirements and run your entry point through that venv's Python. For example, in a single Bash step:

```sh
venv_dir="$(mktemp -d "$RUNNER_TEMP/python-test.XXXXXX")"
trap 'rm -rf -- "$venv_dir"' EXIT
python -I -m venv "$venv_dir"
PIP_CONFIG_FILE=/dev/null "$venv_dir/bin/python" -I -m pip --isolated install -r requirements.txt
unset PYTHONHOME PYTHONPATH
"$venv_dir/bin/python" myscript.py
```

Use your real entry point or test command in place of `myscript.py`. Keep all these commands in the same step, or explicitly preserve the venv path between steps. Do not add `--system-site-packages`: it would expose the shared packages again. If your application needs NumPy, keep that dependency and select a compatible version rather than removing it to pass this check.

## Verification scope

The local check uses CPython 3.12.4 on macOS arm64 and official PyArrow 26.0.0 wheels. The Python 3.11 workflow is supplied for adoption; it has not been run on the reporting user's self-hosted runner. The check does not establish where an existing NumPy installation came from, reproduce an unspecified traceback, or validate an Azure Function deployment.

See the [Python venv documentation](https://docs.python.org/3/library/venv.html) and [setup-python's interpreter and cache behavior](https://github.com/actions/setup-python/blob/v7.0.0/README.md).

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free to use.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
