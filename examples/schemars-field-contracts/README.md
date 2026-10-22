# Schemars field contracts

Generate request and response schemas for asymmetric Serde fields, or include both fields in one annotated document. This example uses Schemars **1.2.3** and addresses the sample in [Schemars #540](https://github.com/GREsau/schemars/issues/540).

`schema_for!(Sample)` describes deserialization by default. With these attributes:

```rust
#[serde(skip_deserializing)]
name: String,
#[serde(skip_serializing)]
name2: String,
#[serde(skip)]
name3: String,
```

the input schema contains `name2`, while the output schema contains `name`. `name3` appears in neither. You can choose the output direction explicitly:

```rust
let schema = schemars::generate::SchemaSettings::draft2020_12()
    .for_serialize()
    .into_generator()
    .into_root_schema_for::<Sample>();
```

The [Generating Schemas guide](https://graham.cool/schemars/generating/#serialize-vs-deserialize-contract) explains the separate serialization and deserialization contracts. The [settings API](https://docs.rs/schemars/1.2.3/schemars/generate/struct.SchemaSettings.html) documents the default.

## Include both fields

If a documentation consumer needs both fields in one schema, add a schema-only override to `name`:

```rust
#[derive(serde::Deserialize, serde::Serialize, schemars::JsonSchema)]
struct CombinedSample {
    #[serde(skip_deserializing)]
    #[schemars(!skip_deserializing, default, extend("readOnly" = true))]
    name: String,
    #[serde(skip_serializing)]
    name2: String,
    #[serde(skip)]
    name3: String,
}

let schema = schemars::schema_for!(CombinedSample);
```

The `!skip_deserializing` override tells **Schemars** to include that field. `extend` adds its `readOnly` annotation. `default` keeps it out of the combined schema's `required` array and records its empty-string default. These attributes leave Serde's behavior unchanged. See the [supported attributes](https://graham.cool/schemars/deriving/attributes/).

The combined schema's relevant content is:

```json
{
  "properties": {
    "name": {"type": "string", "default": "", "readOnly": true},
    "name2": {"type": "string", "writeOnly": true}
  },
  "required": ["name2"]
}
```

Use this combined schema for its annotated field list. For validating input and output, use the separate schemas from `Sample`.

JSON Schema treats [`readOnly`, `writeOnly`, and `default` as annotations](https://json-schema.org/understanding-json-schema/reference/annotations). A general validator does not make `name2` optional in responses because it is `writeOnly`, and does not insert a missing default. Consequently, the actual response `{"name":"response value"}` passes the output schema but fails the combined schema, which still requires `name2`. The tests check this explicitly. An application or API tool may add its own interpretation of these annotations; that behavior is outside this example.

## Run

Install a current stable Rust toolchain, then run from this directory:

```sh
cargo test --locked
cargo run --locked --quiet
```

The command prints one JSON document containing all three schemas and the real Serde operation:

```text
Input:    {"name":"ignored input","name2":"request value","name3":"ignored internal"}
Decoded:  {"name":"","name2":"request value","name3":""}
Set name to "response value".
Response: {"name":"response value"}
```

Both struct variants produce the same response. The tests also use the separate `jsonschema` validator to consume the generated schemas, reject missing or wrongly typed required values, check the combined annotations, and run the command itself. The validator is a test dependency with network/file fetching features disabled. Dependencies are pinned in `Cargo.lock`.

Tested with Rust/Cargo 1.98.1. These are scripted tests. No change to Schemars or Serde is needed. Copy the relevant attributes or schema settings into your own type; this directory is a runnable example, not a library to add as a dependency.

MIT licensed; see [LICENSE](LICENSE).

## Optional coffee

The example is free. If it helps and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
