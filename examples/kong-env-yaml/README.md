# Environment overrides YAML in Kong

A runnable example for `flags > environment > YAML > defaults`, using Kong **v1.16.1** and kong-yaml **v0.2.0**. It addresses the ordering requested in [Kong discussion #566](https://github.com/alecthomas/kong/discussions/566).

Kong's regular YAML configuration can replace a value read from the environment. The small loader in [envyaml.go](envyaml.go) leaves that value alone whenever a flag's configured environment variable is present. Kong still performs the decoding and validation.

## Run

Requires Go 1.20 or newer. Dependencies are pinned in `go.mod` and `go.sum`. These commands use a POSIX shell; start with the example variables unset:

```sh
unset DEBUG APP_WORKERS APP_NAME APP_TIMEOUT APP_TAGS APP_LABELS
go test ./...
go build -o config-example .
./config-example
```

```json
{"debug":false,"workers":2,"name":"local","timeout":"5s","tags":["base"],"labels":{"region":"local"}}
```

Load the included YAML file:

```sh
./config-example --config fixtures/settings.yaml
```

```json
{"debug":true,"workers":8,"name":"from-yaml","timeout":"30s","tags":["yaml","shared"],"labels":{"region":"yaml"}}
```

Environment values override the file, including `false`, `0`, and the empty string:

```sh
DEBUG=false APP_WORKERS=0 APP_NAME='' APP_TIMEOUT=2s \
  APP_TAGS=env,shared APP_LABELS='region=env;team=demo' \
  ./config-example --config fixtures/settings.yaml
```

```json
{"debug":false,"workers":0,"name":"","timeout":"2s","tags":["env","shared"],"labels":{"region":"env","team":"demo"}}
```

An explicit flag wins over a valid environment value:

```sh
DEBUG=false ./config-example --config fixtures/settings.yaml --debug
```

The result has `"debug":true`; the other settings still come from YAML. `--debug=false` explicitly sets false. Maps use Kong's native semicolon separator; slices use commas.

## Use in an existing CLI

Copy `envyaml.go` into your package, change its package declaration if needed, and use `kong.ConfigFlag` for the file selector:

```go
var cli struct {
    Config kong.ConfigFlag `help:"Path to the YAML configuration file."`
    Debug  bool            `default:"false" env:"DEBUG"`
}
kong.Parse(&cli, kong.Configuration(envFirstYAML))
```

Parse once. `ConfigFlag` loads the selected file through the configured loader before values are resolved. There is no separate initial parse to discover `--config`.

For optional default files, pass paths in increasing precedence:

```go
kong.Parse(&cli, kong.Configuration(envFirstYAML, "defaults.yaml", "local.yaml"))
```

Later default files win. An explicit `--config` file overrides them, while environment values still override all those YAML layers. Missing optional default files are skipped by Kong; a missing explicitly selected file is an error. Use this loader for every YAML layer whose precedence you want to change.

## Semantics and limits

- **Present includes empty.** `APP_NAME=''` sets an empty name. Empty boolean, integer, and duration values are invalid; they do not fall back to YAML. For multiple names in an `env` tag, Kong uses the first present name.
- **Invalid environment values remain errors.** On Kong v1.16.1, `DEBUG=invalid ./config-example --debug=false` fails before CLI overrides are applied. This loader preserves that native behavior.
- Invalid YAML syntax, invalid selected typed values, and missing selected files return errors. The official YAML loader ignores unknown keys; this example does not add schema validation.
- Lists and maps retain Kong's native replacement behavior between sources. The example does not merge a list or map across YAML, environment, and flags.
- Reusing a parser reloads an explicitly selected config file for each parse. Optional default-path files are read when the parser is constructed; construct a new parser to reload them. Repeated `--config` flags select the last file.
- Other custom resolvers can still replace values. This recipe changes the supplied YAML loader, not Kong's global resolver ordering.

The tests exercise the original two-parse behavior and the regular `ConfigFlag` behavior as controls, then check the requested ordering, output, typed values, empty/invalid input, nested commands, file order, and repeated parses. Verified with Go 1.27.2 on macOS arm64. No upstream patch is required.

See Kong's official [configuration guidance](https://github.com/alecthomas/kong/blob/v1.16.1/README.md#configuration), [ConfigFlag implementation](https://github.com/alecthomas/kong/blob/v1.16.1/util.go), and [environment decoding](https://github.com/alecthomas/kong/blob/v1.16.1/model.go).

## Optional coffee

This example is free to use. If it saved you time, an optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
