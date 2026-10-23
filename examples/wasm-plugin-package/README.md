# Package a dprint Wasm plugin for npm

A compatible dprint Wasm plugin can be distributed as an npm package with
`package.json` and a root `plugin.wasm`. The native CLI reads that file directly;
it does not use `main` or `exports` to locate it. The Wasm must already implement
the [dprint plugin interface](https://github.com/dprint/dprint/blob/0.64.3/docs/wasm-plugin-development.md).

This example includes a small package template and a real pack/install/format
check. The check uses the official JSON plugin temporarily; it does not publish
anything or include a Wasm binary in this repository.

## Minimum layout

```text
package/
├── package.json
└── plugin.wasm
```

For a plugin you own, use your package name and version:

```json
{
  "name": "@your-scope/your-plugin",
  "version": "1.0.0",
  "files": ["plugin.wasm"]
}
```

`name` and `version` are normal npm metadata. The `files` allowlist ensures the
built artifact is packed; it is not a dprint-specific field. Include your README
and appropriate license notice as well. npm normally includes those files
automatically. Inspect the actual tarball before publishing.

`main`, `exports`, `type`, and `keywords` are unnecessary for native Wasm plugin
loading. Add them if you also provide a JavaScript interface, want explicit
exports for JavaScript consumers, or want package discovery metadata. They do
not replace the Wasm file or change the CLI's default path.

The supplied [template](template/package.json) has `private: true` to prevent
accidental publication. It intentionally contains no formatter binary. Copy
your own compiled, compatible plugin into the package directory before packing.

## Check your own package locally

From your package directory:

```sh
npm pack --ignore-scripts
tar -tzf your-scope-your-plugin-1.0.0.tgz
```

Confirm `package/plugin.wasm` is present, then install the tarball in a separate
consumer directory:

```sh
mkdir consumer
cd consumer
npm init -y
npm install --ignore-scripts /absolute/path/to/your-scope-your-plugin-1.0.0.tgz
```

Use the installed package without a version in `dprint.json`:

```json
{
  "plugins": ["npm:@your-scope/your-plugin"]
}
```

Run `dprint fmt` and `dprint check` on an actual file supported by your plugin.
An unversioned `npm:` reference searches `node_modules` upward from the config
directory. This validates the installed tarball, including its file layout.

After publishing your own package, a registry reference can pin its version:

```json
{
  "plugins": ["npm:@your-scope/your-plugin@1.0.0"]
}
```

The versioned form fetches from the npm registry; it is a different resolution
route. A local tarball test does not establish that registry publication works.
Before publishing, use a package name you control, set the intended version and
license, inspect `npm pack`, and follow npm's account and publishing
requirements. Remove `private: true` only from your own release package.

## Use a custom Wasm path

If the archive contains `package/wasm/format.wasm`, set
`"files": ["wasm/format.wasm"]` and specify the path explicitly:

```json
{
  "plugins": ["npm:@your-scope/your-plugin/wasm/format.wasm"]
}
```

The registry form is
`npm:@your-scope/your-plugin@1.0.0/wasm/format.wasm`.
Leaving off the path still requests `plugin.wasm`, even if `main` or `exports`
points at `wasm/format.wasm`.

## Run the complete example

Requirements: Python 3.9+, npm on `PATH`, and network access to npm and GitHub.
The script selects a native macOS arm64/x64 or Linux glibc arm64/x64 CLI package.

```sh
python3 verify.py
```

The script downloads dprint **0.64.3** and the official **@dprint/json 0.25.2**
fixture into a temporary directory. It verifies the npm tarballs against pinned
SHA512 integrity values and checks the upstream MIT notices against pinned
source checksums. No npm lifecycle scripts run. The native CLI is invoked
directly, without a JavaScript install wrapper.

It checks the actual packed Wasm bytes, installs each tarball in a fresh
consumer outside the source tree, and proves:

- Root `plugin.wasm` works without `main`, `exports`, `type`, or `keywords`.
- Native formatting changes unformatted JSON to exact expected bytes using
  `indentWidth: 4`; JSON values and an unrelated existing file are preserved.
- A second check and formatting run succeed without further changes.
- An explicit custom subpath works; its default path fails despite `main` and
  `exports` pointing at the custom file.
- A `files` allowlist that excludes the Wasm still packs successfully, but the
  installed package fails when dprint tries to load the missing file.

Each consumer config contains only an `npm:` plugin reference, with no URL
fallback. npm cache/user/global config and dprint cache/config locations are
isolated in the temporary directory; it is removed afterward. The fixture
retains its upstream MIT notice and attribution in each temporary package, and
all fixture packages remain `private: true`.

Validated with scripted local checks on macOS arm64, Python 3.12.4, and npm
10.7.0. Other listed platform binaries are selected with pinned checksums but
have not been run here. This checks Wasm packaging and native local resolution;
it does not test registry publication, process plugins, plugin compilation, or
adoption by another project.

See the official [npm specifier documentation](https://dprint.dev/config/#specifying-plugins-from-npm),
the stable [specifier defaults](https://github.com/dprint/dprint/blob/0.64.3/crates/dprint/src/utils/npm_specifier.rs),
and [native npm resolution](https://github.com/dprint/dprint/blob/0.64.3/crates/dprint/src/plugins/npm_resolution.rs).
The validation fixture is [dprint-plugin-json](https://github.com/dprint/dprint-plugin-json/tree/f643fb7f6a119e7e8e87abbe8da7d9ca69aaebd9),
MIT, copyright 2020 David Sherret. The example code is [MIT licensed](LICENSE).

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
