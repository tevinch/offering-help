# Navigate a Dioxus virtual list

Jump to any row in a 39,999-row list, submit with Enter, and return to the top while keeping the same data and mounted list. The row type does not implement `Clone`.

This example uses **fixed 48px rows**. Both the actual CSS height and `estimate_size` are 48. An estimate alone does not make a row that height; `index * 48` is not a correct general solution for unknown or changing row heights.

## Run

Install Rust stable, the `wasm32-unknown-unknown` target, and the official [Dioxus CLI 0.7.10](https://github.com/DioxusLabs/dioxus/releases/tag/v0.7.10). Then, in this directory:

```sh
rustup target add wasm32-unknown-unknown
dx serve --web --locked --port 8187 --addr 127.0.0.1 --open false
```

Open <http://127.0.0.1:8187>. Enter an index from **0 to 39998**, then press Enter or click **Go to row**. **Go to top** uses the same mounted viewport. Edit the first row's label, jump away, and return to index 0 to check that the data stays intact. Ordinary scrolling still works.

The first build downloads Rust dependencies and any missing CLI build tools. `Cargo.toml` pins Dioxus 0.7.10 and the official component revision; keep `Cargo.lock` for repeatable dependencies.

## The connection that matters

The [official VirtualList](https://github.com/DioxusLabs/dioxus-components/blob/9a758255ea26e2b20c8cecf4c1c946feb9e71da7/primitives/src/virtual_list.rs) spreads its `attributes` onto the real scrolling container. Pass its mount handler through the official `attributes!` macro:

```rust
use dioxus::prelude::*;
use dioxus_primitives::{dioxus_attributes::attributes, virtual_list::VirtualList};
use std::rc::Rc;

// Inside the component:
let mut viewport = use_signal(|| None::<Rc<MountedData>>);

// Inside VirtualList { ... }:
attributes: attributes!(div {
    class: "dx-virtual-list-container",
    onmounted: move |event: MountedEvent| viewport.set(Some(event.data())),
}),
```

At this revision, `onmounted` is not a direct `VirtualList` prop. The styled copy-in wrapper also forwards its `attributes` list, so the same connection applies there. Preserve the component's internal `id`: its scroll listener uses that id.

After validating the submitted index, use the saved container's [`MountedData::scroll`](https://docs.rs/dioxus-html/0.7.10/dioxus_html/events/struct.MountedData.html#method.scroll):

```rust
let offset = (0.0, index as f64 * 48.0).into();
element.scroll(offset, ScrollBehavior::Instant).await?;
```

This scrolls the actual container; the virtual list's existing listener updates which rows are rendered. A faraway row is not yet in the DOM, so calling `scroll_to` on that row is not the starting point. Near the end, the browser clamps the offset to its maximum and the final row remains visible at the bottom.

The form handles `onsubmit`, calls `prevent_default`, and reads the named field with `get_first("index")`. Enter and the submit button follow the same path. `count` remains `list.len()` throughout; there are no count resets, key remounts, or keydown/keyup timing tricks.

For variable row heights, use correct cumulative heights or a component API that exposes its measurements. This example deliberately does not approximate arbitrary dynamic-height navigation with the fixed-height formula. Only the web renderer is covered here.

## Check the complete interaction

With the app running, use Node.js 20 or later:

```sh
npm ci --ignore-scripts
npx playwright install chromium
npm test
```

`DEMO_URL` can select a different local URL. The check uses a separate headless Chromium instance. It starts with row 30000 absent from the DOM, edits row 0, submits several distant indexes with Enter and a button, reaches the last row, returns to the top, scrolls with the wheel, rejects invalid indexes, and repeats navigation. It inspects real `scrollTop`, target rectangles/text, the same DOM container, retained label, total count, and bounded rendered rows; a status message alone cannot pass it.

Verified with Dioxus 0.7.10 and Playwright 1.64.1 in software-operated Chromium on macOS. Row 30000 produced `scrollTop = 1440000` with 209 rendered rows; all 39,999 data rows remained present.

## Source and license

The example code is MIT licensed. It consumes the official Dioxus Labs `dioxus-primitives` component at revision `9a758255ea26e2b20c8cecf4c1c946feb9e71da7`, under its [MIT or Apache-2.0 license](https://github.com/DioxusLabs/dioxus-components/tree/9a758255ea26e2b20c8cecf4c1c946feb9e71da7). The component is used without source changes. The [original question](https://github.com/DioxusLabs/dioxus/discussions/5881) describes the navigation problem this example addresses.

## Optional coffee

This example is free. If it saved you time, you're welcome to buy me a coffee; it is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
