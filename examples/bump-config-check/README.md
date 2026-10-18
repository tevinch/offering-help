# Check bump.yml version targets

Check every `files` declaration in a bump-release-action configuration before a release: the file must exist, the configured line must exist, and the first numeric version after `start` must equal the version you expect. The check reads local files and exits with a nonzero status if any target fails. It needs no Git branch, GitHub token or network access at runtime.

## Try it

Use Python 3.9 or newer. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python check_bump.py --root example --config bump.yml --expected-version 1.2.3
```

Expected result:

```text
OK files[0]: package.json:3 (start 0) = 1.2.3
OK files[1]: versions.txt:2 (start 13) = 1.2.3
Checked 2 targets; files unchanged.
```

Change an example line number or version and run it again. Each failing declaration is reported as `files[index]`; the exit status is `1`. Argument errors exit with status `2`.

For your project, copy `check_bump.py` and `requirements.txt` to `tools/bump-config-check/`, install the requirement in your usual Python environment, then run from your repository root:

```sh
python tools/bump-config-check/check_bump.py --config .github/bump.yml --expected-version 1.2.3
```

`--root` defaults to the current directory. Target paths and a relative `--config` are resolved from that root. Supply the expected version from the source your project treats as authoritative; the checker does not fetch the latest release or infer a version from the target being checked.

## Pull request check

For a project whose authoritative numeric version is `package.json`'s `version`, save this as `.github/workflows/check-bump-targets.yml` after copying the two files as above:

```yaml
name: Check version targets
on: pull_request
permissions:
  contents: read
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7.0.1
      - uses: actions/setup-python@v7.0.0
        with:
          python-version: '3.12'
      - run: python -m pip install -r tools/bump-config-check/requirements.txt
      - name: Check every configured target
        run: |
          BUMP_EXPECTED_VERSION="$(python -c 'import json; from pathlib import Path; print(json.loads(Path("package.json").read_text())["version"])')"
          python tools/bump-config-check/check_bump.py --config .github/bump.yml --expected-version "$BUMP_EXPECTED_VERSION"
```

Use your own authoritative version source if it differs. This workflow runs the local checker; it does not invoke the release action.

## Matching and limits

Target selection follows bump-release-action **v3.0.13**: `line` is one based; `start` is a zero based UTF-16 offset, omitted or null means zero; line endings may be LF, CRLF or CR; the first ASCII `X.Y.Z` after that offset is selected. Prerelease and build suffixes are outside the action's numeric matcher. Pass a valid numeric core such as `1.2.3` as the expected version.

The checker is deliberately stricter about configuration. Every target needs a string `file-path` and positive integer `line`; `start` must be a nonnegative integer or null. Empty target lists, unknown target fields, duplicate YAML keys (including conflicting merged keys), and target paths outside the selected root are rejected. Quoted numbers and fractional/exponent offsets are rejected. YAML aliases are supported. Other release settings are not validated.

This checks the declarations against the current, unmodified files. It does not simulate sequential future replacements, calculate the next version, or establish that a complete release will succeed. In particular, the official `dry_run` already reads and checks replacement targets after its branch guard passes; it searches for a numeric version but does not compare it with the calculated current version. Changing `branch.base-branch` alone does not add that comparison.

Run the CLI tests with:

```sh
.venv/bin/python -m unittest discover -v
```

Tests cover valid and invalid declarations, all-target error reporting, unchanged input files, mixed line endings, UTF-16 offsets, YAML aliases and duplicate keys. These are scripted local checks; the original project's configuration and hosted CI have not been tested.

References: [original question](https://github.com/MeilCli/bump-release-action/issues/1884), [configuration documentation](https://github.com/MeilCli/bump-release-action/tree/v3.0.13#configuration), [branch guard](https://github.com/MeilCli/bump-release-action/blob/v3.0.13/src/main.ts#L19-L22), [replacement matcher](https://github.com/MeilCli/bump-release-action/blob/v3.0.13/src/file.ts#L64-L111).

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
