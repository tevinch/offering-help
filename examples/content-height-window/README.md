# Fit a GPUI window to its content height

This GPUI Kit 0.8.0 example keeps a native window as tall as its content while preserving its current width. Add/remove rows or change the width: wrapping text is measured again and the height follows it.

## Run

Install Rust and the [GPUI Kit platform prerequisites](https://gpui-kit.com/docs/getting-started), then run from this directory:

```sh
cargo run --locked
```

The first build downloads and compiles GPUI's native dependencies. The example has standard Add row, Remove row and Reset buttons; its row count is bounded to six so the demonstration stays small. Closing the window exits the application.

## The layout relationship

`h_auto()` affects an element's layout; resizing the native window is a separate operation. Put all content and padding in one intrinsic-height child. Observe that child's resolved bounds with [`on_children_prepainted`](https://docs.rs/gpui-pre/0.3.9/gpui/struct.Div.html#method.on_children_prepainted), then defer [`Window::resize`](https://docs.rs/gpui-pre/0.3.9/gpui/struct.Window.html#method.resize). That method takes the window's **content size**, so no titlebar-height adjustment is needed.

The essential part of [main.rs](src/main.rs) is:

```rust
div()
    .size_full()
    .child(content) // w_full(), intrinsic height, flex_shrink_0(); padding inside
    .on_children_prepainted(move |bounds, window, cx| {
        let measured = bounds[0].size.height;
        let viewport = window.viewport_size();
        let scale = window.scale_factor();
        let height = px(((f32::from(measured) * scale).ceil() / scale)
            .max(MIN_HEIGHT));

        if (f32::from(viewport.height - height)).abs() >= 1. / scale {
            window.defer(cx, move |window, _| {
                let current = window.viewport_size();
                if current.width == viewport.width && current.height != height {
                    window.resize(size(current.width, height));
                }
            });
        }
    })
```

Use the same minimum height in this calculation and `WindowOptions::window_min_size`. This example uses 100 logical pixels. The width check discards a measurement if the width changes before the deferred resize runs; the next layout supplies the new height. Pixel rounding and the size comparison prevent repeated resizing once the result settles.

Keep `h_full()` and `flex_1()` off the measured content child: those can make its height depend on the viewport you are trying to calculate. Preserve `gpui_kit::init` and `gpui_kit::open_window` so the normal Root setup remains in place.

This is a finite-content utility-window example. It does not implement every WPF `SizeToContent` behavior. For long documents or virtualized lists, choose an explicit maximum height and a scrollable viewport instead of trying to fit the entire document on screen. Fullscreen/maximized behavior and Windows/Linux native behavior have not been validated here.

## Reproduce the checks

```sh
cargo run --locked -- --verify
# Expected: 22 CHECKPOINT lines, then “Native verification passed”.

cargo run --locked -- --verify --no-fit
# Expected negative control: exit 1; initial native height does not match content.

cargo run --locked -- --trace
# Interactive example with layout and resize counts on stdout.
```

The verifier opens a real native window and sends **simulated GPUI pointer events** to the measured button bounds. It checks repeated additions/removals, reset, zero rows, the six-row limit, width changes from 520 to 360 to 760, and continued button operation after wrapping changes. It reads native viewport dimensions and rendered child bounds independently, then requests three further frames at every checkpoint to check that the callback runs and the resize count stays stable.

Verified on macOS 14.6 with Rust 1.98.1, GPUI Kit 0.8.0 and its pinned GPUI snapshot 0.3.9. At two rows the content/window height was 307 at width 520, 333 at width 360, and 281 at width 760. With fitting disabled, the same check failed at height 700 versus measured content height 307. These are scripted native checks, not human testing or operating-system pointer input.

## Optional coffee

This example is free. If it helps, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
