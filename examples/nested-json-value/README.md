# Read a typed value from nested JSON

If an API puts a user at `data.user`, select that value before deserializing it. `User` can keep its ordinary `Deserialize` implementation, so it also works with a standalone user object.

```rust
use serde::Deserialize;
use serde_json::Value;

#[derive(Debug, Deserialize)]
struct User {
    id: u64,
    name: String,
}

let response: Value = serde_json::from_str(input)?;
let value = response
    .pointer("/data/user")
    .ok_or("missing /data/user")?;
let user = User::deserialize(value)?;
```

`&Value` implements Serde's `Deserializer`, so the last line reads the selected subtree without cloning or removing it. The resulting `User` owns its `String`. There are no `Response` or `Data` wrapper types and no special attributes on `User`.

This is an explicit selection step. `serde_json::from_str::<User>(input)` still expects a standalone user; it does not automatically look under `data.user`.

## Run

This example uses Serde 1.0.229 and serde_json 1.0.154, fixed in `Cargo.lock`. From this directory:

```sh
cargo run --locked --quiet < response.json
```

Output:

```json
{"id":123,"name":"John"}
```

The executable reads one JSON document from standard input. A missing path, a `null` user, invalid fields or invalid JSON produce an error on standard error and exit status 2, without a partial user on standard output.

## Boundaries

- `pointer` takes a [JSON Pointer](https://docs.rs/serde_json/1.0.154/serde_json/value/enum.Value.html#method.pointer), such as `/data/user`, rather than a dotted path. Array indices are supported; a literal `/` in a key is escaped as `~1`, and `~` as `~0`.
- The complete response is first stored as a `Value`. This saves model boilerplate, not the memory needed to hold the JSON. If extraction during deserialization matters, [serde-query](https://github.com/pandaman64/serde-query) offers query attributes through a separate derive and is another option to evaluate.
- Missing and `null` are different: a missing pointer is reported explicitly; a present `null` reaches `User::deserialize` and is rejected as an invalid user. Make that policy explicit if your API uses nullable results.
- This demonstrates selection after receiving a response. API errors, including GraphQL's `errors` field, still need handling according to that API's contract before this step.

The ordinary standalone form remains available:

```rust
let user: User = serde_json::from_str(r#"{"id":123,"name":"John"}"#)?;
```

## Checks

```sh
cargo test --locked
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
```

The tests cover the original nested response, standalone deserialization, repeated extraction without changing the response, Unicode and unrelated fields, missing versus null values, invalid fields, and complete executable input/output including malformed or trailing input. The original direct deserialization of the envelope is also checked to fail. These are scripted checks; they do not establish adoption in the original application.

References: [Serde's deserialize method](https://docs.rs/serde/1.0.229/serde/trait.Deserialize.html#tymethod.deserialize), [serde_json::Value](https://docs.rs/serde_json/1.0.154/serde_json/value/enum.Value.html).

## Optional coffee

If this example saves you some time, you're welcome to buy me a coffee. It is entirely optional; the example stays free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
