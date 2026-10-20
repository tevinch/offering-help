# Read JSON configurations with full-line comments

When an otherwise valid JSON configuration contains complete lines beginning with `//`, read it as text first, blank those lines, then parse the result. A normal jq filter runs only after its input has already been parsed, so removing comments inside that filter is too late without raw input mode.

From this directory, with jq installed:

```sh
jq -Rs -f read-config.jq config.json
```

To read a field in a single command:

```sh
jq -Rrs '
  split("\n")
  | map(if test("^[ \t\r]*//") then "" else . end)
  | join("\n")
  | fromjson
  | .service.endpoint
' config.json
```

The sample prints `https://example.com/a//b`. Replace `.service.endpoint` with your usual query. `-R` reads text; `-s` collects one complete configuration before processing it. The command reads the original file without changing it. It keeps the number of lines by replacing comment lines with empty strings.

This recipe accepts one JSON value with full-line `//` comments, optionally indented with spaces or tabs. Use UTF-8 without a BOM and LF or CRLF line endings. It keeps `//` inside quoted strings, including URLs. The rest must remain valid JSON: removing a property line must not leave a trailing comma. Inline comments, block comments and JSON5 syntax require a parser for that format. Invalid input still produces a nonzero exit status; it is not silently skipped. Supply one configuration file per invocation. The complete input is held in memory.

`-f read-config.jq` emits the complete parsed value, including `false` or `null`. Add your own query in the inline form above. If you pipe the file form into another command, enable your shell's pipeline failure propagation (for Bash, `set -o pipefail`) so a later successful command does not hide a parsing failure.

## Check the example

```sh
python3 -m unittest -v test_read_config.py
```

The scripted check runs real jq processes and compares the full parsed object, a subsequent field query, CRLF input, indentation, arrays, nested comments, quoted slashes, escaped quotes, Unicode and top-level JSON types. Invalid and unsupported syntax must fail. Each invocation checks that the input file's hash is unchanged.

Verified with official jq 1.8.2 on macOS arm64 and Python 3.12.4. The reporting user's configuration was not supplied, so its syntax has not been verified. See the [official jq manual](https://jqlang.org/manual/#invoking-jq) for raw input and slurp, and [JSON conversion](https://jqlang.org/manual/#convert-to-from-json).

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free to use.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
