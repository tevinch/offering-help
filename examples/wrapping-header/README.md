# Export a Rust wrapping integer with cbindgen

Give the concrete `Wrapping<u32>` type a Rust alias, then tell cbindgen to use `uint32_t` for that alias. This preserves Rust's wrapping arithmetic and produces a usable C or C++ field.

```rust
use std::num::Wrapping;

pub type WrappedU32 = Wrapping<u32>;

#[repr(C)]
pub struct Counter {
    pub marker: u8,
    pub value: WrappedU32,
}
```

For C, use:

```toml
language = "C"
include_guard = "COUNTER_H"
cpp_compat = true

[export]
exclude = ["WrappedU32"]

[export.rename]
WrappedU32 = "uint32_t"
```

`exclude` prevents cbindgen from emitting the alias's unresolved `Wrapping<u32>` body. `rename` maps uses of the named alias to the standard integer type. The generated field is:

```c
uint32_t value;
```

For C++, use `language = "C++"` with the same `exclude` and `rename` settings; see [cbindgen-cpp.toml](cbindgen-cpp.toml). Replace **every public occurrence** you want mapped with the Rust alias. A direct `Wrapping<u32>` occurrence remains unresolved. A rename key such as `"Wrapping<u32>"` does not match a named item.

This depends on Rust's documented guarantee that [`Wrapping<T>` has the same layout and ABI as `T`](https://doc.rust-lang.org/std/num/struct.Wrapping.html#layout-1). The enclosing structure still needs `#[repr(C)]`. A Rust type alias does not create a new type: the field remains `Wrapping<u32>`, so existing Rust operations, constructors and `.0` access still work.

## Run the complete example

Requires Rust with edition 2024 support, Python 3, and C/C++ compilers. The build commands in this example target macOS or Linux.

```sh
cargo install cbindgen --version 0.29.4 --locked
python3 verify.py
```

Or set `CBINDGEN` to an existing executable's path. `CC` and `CXX` can select compiler executables.

The script builds the Rust library, generates both headers in a temporary directory, compiles C11 and C++11 clients with warnings treated as errors, and runs both against the Rust library. Each client checks structure size/alignment/field offset, an adjacent field's value, zero and ordinary addition, overflow from `UINT32_MAX` to zero, and two further calls. The final output is:

```text
PASS: C11 and C++11 consumers called the Rust library
```

With cbindgen 0.29.4, generation still prints nonfatal warnings about the deliberately excluded `WrappedU32`; C mode also warns that it cannot mangle the underlying `Wrapping` type. The example does not hide those warnings. The generated headers use `uint32_t`, compile successfully, and are checked by the running clients.

To generate just the C header:

```sh
cbindgen --config cbindgen-c.toml --output counter.h
```

## Scope

Verified with cbindgen **0.29.4**, Rust **1.98.1**, and Apple Clang **15.0.0** on macOS arm64, including a fresh copy in a directory containing spaces. These are scripted compiler and runtime checks; other platforms and a recipient's original crate have not been tested.

This recipe explicitly maps one concrete standard type. Add a distinct Rust alias and correct C type for each other primitive width you expose. Do not map an unrelated custom wrapper to an integer unless its layout and ABI are independently guaranteed. cbindgen's renaming is not namespace-aware, so use an alias name unique within the generated API.

C/C++ clients see an ordinary integer, with that language's arithmetic rules. The example performs the wrapping arithmetic in Rust. It does not implement a C++ wrapping-arithmetic class or automatic simplification of arbitrary Rust generics.

The supported configuration is described in [cbindgen's configuration guide](https://github.com/mozilla/cbindgen/blob/0.29.4/docs.md#cbindgentoml); its [supported-type rules](https://github.com/mozilla/cbindgen/blob/0.29.4/docs.md#supported-types) explain representation and generic handling.

## Optional coffee

This example is free to use. If it saved you time, a coffee is welcome and entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
