# Collecting Eros errors from a loop

This example processes every item, collects the original Eros errors with their context and backtraces, and propagates the collection alongside other errors with `?`. It addresses [the collection question in Eros #31](https://github.com/mcmah309/eros/discussions/31) using the published Eros 0.8.1 APIs.

## The pattern

`Vec<ErrorUnion<…>>` does not implement `std::error::Error`. Wrap the vector in a local type that does:

```rust
pub type ItemError = ErrorUnion<(Odd, Overflow)>;

#[derive(Debug)]
pub struct BatchErrors(pub Vec<ItemError>);

impl std::fmt::Display for BatchErrors {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} items failed", self.0.len())
    }
}

impl std::error::Error for BatchErrors {}
```

Push each entire `ItemError` into that vector. Moving the union retains its original diagnostics. Then `Err(BatchErrors(errors)).union()` produces a normal Eros error that can be widened into a return type containing the other possible errors:

```rust
pub type BatchReport = ErrorUnion<(ParseIntError, BatchErrors, CountMismatch)>;

let expected = expected_count.parse::<usize>().union()?;
let values = collect_results(numbers.into_iter().map(double_even)).widen()?;
// A separate fallible step can now use `?` before returning the values.
```

See [src/lib.rs](src/lib.rs) for the complete imports, loop, context annotations, prerequisite and finalization steps. The example doubles even `u8` values and reports odd numbers and overflow independently.

## Reporting the children

The final caller uses `render_report`: it formats the outer report, borrows `BatchErrors` with `downcast_inner_ref`, and formats every child union with `Debug`. Printing only the outer Eros report shows the count summary; it does **not** recursively print all child reports. Rust's `Error::source` represents one chain, so this example explicitly handles the sibling errors.

Eros's default features provide context and backtrace support. The manifest also enables `location`. Set `RUST_LIB_BACKTRACE=1` before starting the process to capture backtraces. Each child keeps its original capture; the aggregate has a separate capture. With capture disabled, the errors and contexts remain available.

## Run

From this directory, using Rust and Cargo:

```sh
cargo test --locked
cargo run --locked -- success
RUST_LIB_BACKTRACE=1 cargo run --locked -- mixed
```

`success` prints `Values: [0, 4, 8, 252]` and exits 0. `mixed` visits all eight inputs, reports five errors with their item contexts and exits 1. Other scenarios are `original` (the question's `0..5` range, two errors), `before` (invalid count, no items visited), and `after` (all three items succeed, then the count check fails). These three exit 1 as expected. No argument selects `mixed`.

## Behavior and limits

- Inputs are processed sequentially and fully when the prerequisite succeeds. This collector expects a finite iterator.
- Successful batches return all values in order. If any item fails, successful values are discarded, matching the question's example. Retaining partial successes requires a separate application outcome type.
- A prerequisite error stops before the loop. A batch error skips finalization. A finalization error propagates after all items succeed. This does not collect unrelated errors from steps that have not run.
- The wrapper is concrete to this example. It does not change Eros or introduce automatic error-tree rendering.

Verified with Rust/Cargo 1.98.1, Eros 0.8.1 and thiserror 2.0.21. The tests cover complete traversal, preserved child reports and backtrace allocations, typed prerequisite/finalization errors, empty and boundary inputs, repeated calls, and actual process output with backtraces enabled and disabled.

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
