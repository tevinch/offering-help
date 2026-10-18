# Synchronous binary stdio with Boa

When `read_bytes` changes from `Option<Vec<u8>>` to `io::Result<Option<Vec<u8>>>`, the caller must handle all three outcomes:

```rust
match read_bytes(/* reader and destination */) {
    Ok(Some(bytes)) => { /* copy bytes into the Uint8Array; return bytes.len() */ }
    Ok(None) => { /* clean EOF: return JavaScript null */ }
    Err(error) => { /* return a JavaScript exception */ }
}
```

Matching only `Ok(Some(bytes))` and returning `null` for everything else compiles but hides read errors as EOF. This example connects the full match to three real Boa bindings. It addresses the Result integration in [Boa discussion #5534](https://github.com/boa-dev/boa/discussions/5534).

## Run

The standalone crate pins `boa_engine = "=0.22.0"` and includes its lockfile. From the repository root:

```sh
cargo build --locked --manifest-path examples/boa-stdio/Cargo.toml
cargo test --locked --manifest-path examples/boa-stdio/Cargo.toml
python3 - <<'PY'
import struct
import subprocess

payloads = [bytes([0, 127, 128, 255, 226, 130, 172]), b"", b"*"]
wire = b"".join(struct.pack("<I", len(p)) + p for p in payloads)
result = subprocess.run(
    ["examples/boa-stdio/target/debug/boa-stdio-example"],
    input=wire, capture_output=True, check=True,
)
assert result.stdout == wire
assert result.stderr == (
    b"frame 1: 7 bytes, sum=1038\n"
    b"frame 2: 0 bytes, sum=0\n"
    b"frame 3: 1 bytes, sum=42\n"
)
print(result.stderr.decode(), end="")
PY
```

The fixed [`demo.js`](demo.js) reads a 4-byte little-endian length, checks a **deliberately small 64 KiB local demo cap before allocating**, accumulates the payload, computes a checksum in JavaScript, and echoes the original header and payload. This cap belongs to the demo; the `std.read` and `std.write` bindings impose no 64 KiB payload cap. Empty frames are valid. Multiple frames share one process. EOF between frames succeeds; an incomplete header, incomplete payload, or oversized frame fails with a nonzero exit status. Earlier complete frames may already have been emitted when a later frame fails.

The checksum is a diagnostic sum of byte values, not an integrity or security mechanism. Stdout contains only binary frames; diagnostics go to stderr.

## Use the bindings in another host

[`src/lib.rs`](src/lib.rs) exposes `install_stdio(&mut context, input, output, diagnostics)`. The streams implement `Read` / `Write` and must be owned (`'static`); [`src/main.rs`](src/main.rs) supplies `stdin()`, `stdout()` and `stderr()`. The three functions are synchronous. Use a fresh context, and install once before evaluating your script. This example stores only Rust I/O state in context data.

| Binding | Contract |
| --- | --- |
| `std.read(Uint8Array)` | Copies at most the view's length, changes only the bytes actually read, and returns their count. Short reads are normal. A nonempty view at clean EOF returns `null`. An empty valid view returns `0` without consuming input. `Interrupted` retries; other read errors throw. |
| `std.write(Uint8Array)` | Writes exactly the view's byte range using `write_all`, then flushes nonempty output and returns the full count. Empty views return `0`. Interrupted and short writes are handled by `write_all`; other write or flush errors throw. |
| `std.err(string)` | Writes the supplied text to stderr and flushes. It adds no newline. Ordinary Unicode and newlines are preserved. Unpaired UTF-16 surrogates are represented with escapes via `to_std_string_escaped`. Write or flush errors throw. |

Read and write reject missing arguments, ordinary objects, other typed-array kinds, and detached/out-of-bounds buffers with a `TypeError`. No string decoding is applied to binary input or output. View access uses Boa's public `JsUint8Array` API; no engine patch or unsafe block is needed.

**Write-error contract:** unlike the earlier version that returned `0` on a write failure, this example throws. Some bytes may already have reached stdout before a write or flush fails. Catch the error to report/terminate the message stream; do not retry the entire frame automatically, since that can duplicate an already-written prefix. A flush failure also does not establish that nothing was written.

This is a bounded byte-I/O example to adapt. It does not implement a JSON message layer, a browser extension, async Promise/job handling, or the original poster's unavailable `__index.js`. Only native execution is checked; WASI is unverified.

## Chrome native messaging

[Chrome's native messaging protocol](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging) has separate per-message limits:

| Direction | Maximum JSON payload |
| --- | --- |
| Browser to host | 64 MiB (67,108,864 bytes) |
| Host to browser | 1 MiB (1,048,576 bytes) |

Measure the serialized JSON's UTF-8 bytes, excluding the four-byte length prefix. That prefix uses the platform's native byte order. The local demo uses raw binary payloads and fixed little-endian framing; adapting it requires the browser's JSON protocol.

Increasing the demo's input cap alone would let its echo exceed the browser's output limit. Check input length before allocating and encoded output length before writing. Array element counts and JavaScript string length do not establish the encoded byte size.

Multiple responses need client-agreed JSON messages and reassembly. A `runtime.connectNative()` port supports multiple messages; `runtime.sendNativeMessage()` uses only the first host response and ignores later ones. Splitting raw bytes or adding output frames cannot transparently preserve an existing client's message contract. Browser integration and these larger boundaries have not been tested by this example.

## Verification

The tests exercise registered Boa callbacks with controlled short reads, `Interrupted`, genuine read/write errors, and a partial-output failure. They check nonzero-offset subarray sentinels, untouched unread tail bytes, zero-length reads without input consumption, EOF, NUL/non-UTF8 bytes, Unicode diagnostics, and detached/wrong-type rejection. A second suite starts the actual executable with pipes and compares binary frames, JavaScript-computed checksums, stderr, and exit status; it includes truncation, oversized headers, empty frames, multiple frames, and the exact 64 KiB boundary.

Controlled short-read fixtures prove accumulation even when OS pipes would combine writes. These are scripted tests, not human validation or a reproduction of the original application. Native toolchain used: Rust/Cargo 1.98.1, aarch64-apple-darwin.

Official references: [`Context`](https://docs.rs/boa_engine/0.22.0/boa_engine/context/struct.Context.html), [`ObjectInitializer`](https://docs.rs/boa_engine/0.22.0/boa_engine/object/struct.ObjectInitializer.html), [`JsUint8Array`](https://docs.rs/boa_engine/0.22.0/boa_engine/object/builtins/struct.JsUint8Array.html), [`Read::read`](https://doc.rust-lang.org/std/io/trait.Read.html#tymethod.read), [`Write::write_all`](https://doc.rust-lang.org/std/io/trait.Write.html#method.write_all).

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
