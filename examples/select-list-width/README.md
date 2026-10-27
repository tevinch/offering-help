# Give one Svelte Select a wider dropdown

Give the chosen `Select` a class, then qualify the list selector with that class. The input keeps its normal width and other selects keep their default dropdown widths.

```svelte
<script>
  import Select from 'svelte-select';
  const items = ['One', 'Two', 'Three'];
</script>

<Select {items} class="wide-options" />
<Select {items} />

<style>
  :global(.wide-options .svelte-select-list) {
    width: min(60rem, calc(100vw - 2rem)) !important;
  }
</style>
```

The selector reaches only the list inside `.wide-options`. Keep `!important`: the component writes an inline list width when it opens and updates its position. `listAutoWidth={false}` changes that inline width to `auto`; it does not set a custom width. There is no `--list-width` custom property in the current theming list.

Here `60rem` is the desired dropdown width. The `min()` also caps it at the viewport width minus two rem, so it fits on narrower screens. Use `width: 60rem !important` instead if you deliberately want a fixed width even when it exceeds the viewport. For several custom widths, give those controls their own classes and corresponding rules. Remove the original unqualified global list rule.

## Run the complete example

Use Node.js 20.19+ or 22.12+ (verified with Node.js 24.22.1). In this directory:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm run preview -- --port 4173
```

Open [the local example](http://127.0.0.1:4173). Open the first select, filter its options and choose one. Its dropdown is wider than its input on a wide screen. Open the second select: its dropdown matches its own input. Both selected values appear below the controls. Reopen them and resize the window to see the width rule persist.

For development, use `npm run dev`. The example pins Svelte Select 6.0.0, Svelte 5.57.3, Vite 8.3.5 and the Svelte Vite plugin 7.3.1. Svelte Select 6 requires Svelte 5; this example does not establish which version an existing application uses or require upgrading it just to scope a selector.

## Verification and references

The compiled example was checked in software-operated Chromium 156 on macOS. At a 1440px viewport with a 16px root font, the chosen list measured 960px and both inputs measured 288px; the second list measured 288px. At a 390px viewport, the chosen list measured 358px. Filtering, pointer and keyboard selection, hidden form values, repeated reopening, resizing and the other control's selection were checked. Removing the class or `!important`, or restoring the broad selector, made the relevant visible-width checks fail. Other browsers, assistive technology and the original application were not tested.

The [Svelte Select README](https://github.com/rob-balfre/svelte-select#props) documents the `class` and `listAutoWidth` props. Its [class example](https://github.com/rob-balfre/svelte-select/blob/acfbcb5ac2c0efe01185ee9ca1b87a95e3f8921a/src/routes/examples/props/class/+page.svelte), [list width setter](https://github.com/rob-balfre/svelte-select/blob/acfbcb5ac2c0efe01185ee9ca1b87a95e3f8921a/src/lib/Select.svelte#L847) and [theming variables](https://github.com/rob-balfre/svelte-select/blob/acfbcb5ac2c0efe01185ee9ca1b87a95e3f8921a/docs/theming_variables.md) explain the configuration. Svelte Select is a separate dependency with [its own license](https://github.com/rob-balfre/svelte-select/blob/acfbcb5ac2c0efe01185ee9ca1b87a95e3f8921a/LICENSE).

## Optional coffee

This example is free. If it saved you time, a small coffee contribution is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
