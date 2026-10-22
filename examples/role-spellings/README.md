# Parse role spellings with Strum

Accept `cast-member`, `cast_member`, and `casTMember` as the same Rust enum variant using Strum's existing attributes. This example addresses the concrete input spellings in [Strum #495](https://github.com/Peternator7/strum/issues/495), with Strum **0.28.0**.

```rust
use strum::EnumString;

#[derive(Debug, PartialEq, EnumString)]
#[strum(ascii_case_insensitive)]
enum PersonRole {
    #[strum(
        serialize = "CastMember",
        serialize = "cast-member",
        serialize = "cast_member"
    )]
    CastMember,
}

assert_eq!("cast_member".parse(), Ok(PersonRole::CastMember));
assert_eq!("casTMember".parse(), Ok(PersonRole::CastMember));
assert_eq!("CAST-MEMBER".parse(), Ok(PersonRole::CastMember));
```

The aliases handle separators; `ascii_case_insensitive` handles letter case. Once you specify aliases, the implicit variant name is replaced, so include `CastMember` explicitly to retain the joined spelling. Repeat the three aliases for other multiword variants. Single-word variants only need the enum-level case setting.

The [versioned EnumString documentation](https://docs.rs/strum_macros/0.28.0/strum_macros/derive.EnumString.html) and [additional attributes](https://docs.rs/strum/0.28.0/strum/additional_attributes/index.html) describe these settings. The normal generated matching path compares the input against the aliases with `eq_ignore_ascii_case`; no lowercased input string is needed. This example does not enable `use_phf` or make a performance benchmark claim.

## Structured input

The runnable example also parses `ExecutiveProducer`, `Director`, and `Translator`. [src/lib.rs](src/lib.rs) implements a Serde string visitor that delegates to the same `parse()` implementation. This step matters: deriving Serde's `Deserialize` separately would not make it use Strum's aliases.

Serde's `Serialize` emits canonical kebab-case names. The included fixture contains all three cast-member spellings, mixed case, an escaped role string, and names with quotes and Unicode. Their names, order, and title survive parsing and serialization.

With a current stable Rust toolchain, run from this directory:

```sh
cargo test --locked
cargo run --locked --quiet < fixtures/work.json
```

The output has these role values, in order:

```text
cast-member
cast-member
cast-member
executive-producer
director
translator
```

[fixtures/expected.json](fixtures/expected.json) contains the complete expected JSON document. The command reads stdin and writes its result to stdout; it does not edit the input file. An invalid document or role exits nonzero, explains the error on stderr, and produces no result on stdout. Correct `cast__member` to `cast_member` and rerun to complete the operation.

## Boundaries

This covers the three conventional spellings, with ASCII case ignored. It does not remove arbitrary separators, trim whitespace, or perform Unicode case folding. For example, `cast__member`, `c-astmember`, `cast member`, and `DİRECTOR` are rejected. Direct `parse()` returns `strum::ParseError::VariantNotFound`; structured input errors include the bad value and the canonical allowed names.

The JSON format here is a small consumer example with `title` and an `affiliated` list of `role`/`names` records. Unknown fields are rejected so they cannot be silently discarded. It is not the full Hayagriva format, and this does not change Hayagriva's deserializer or implement a new Strum comparator attribute. Copy the enum attributes and Serde integration into your own types, retaining your application's full schema.

Tested by scripted checks with Rust/Cargo 1.98.1. The tests exercise real parsing, content-preserving serialization, invalid inputs, and the stdin/stdout command. This has not been tested inside Hayagriva. Dependencies are pinned in `Cargo.lock`. MIT licensed; see [LICENSE](LICENSE).

## Optional coffee

The example is free. If it helps and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
