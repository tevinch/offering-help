# Static Typography CSS for plain HTML

[typography.min.css](./typography.min.css) is a ready-to-use stylesheet built from **Tailwind CSS / CLI 4.3.3** and **Typography 0.5.20**. Copy it to a static site or your own CDN and link it like any other CSS file. The consuming page needs no JavaScript, framework, Node.js or package installation.

This is an independent build with a bounded class list. Publishing a prebuilt file in the official Typography package remains an upstream decision.

## Use the ready file

Copy `typography.min.css` and `THIRD-PARTY-LICENSES.txt` to your site's assets, then add the stylesheet and a `prose` container:

```html
<link rel="stylesheet" href="./typography.min.css">

<article class="prose prose-slate">
  <h1>A useful document</h1>
  <p>Plain HTML, including output from a Markdown renderer, goes here.</p>
  <ul><li>A readable list item</li></ul>
</article>
```

Use the actual deployed path for your stylesheet. Fonts and page backgrounds remain your site's choice. You can open [index.html](./index.html) locally to see the included examples; `demo.css` supplies only that demonstration page's layout and existing widget styles.

## Included classes

| Purpose | Classes |
| --- | --- |
| Article container | `prose` |
| Text sizes | `prose-sm`, `prose-base`, `prose-lg`, `prose-xl`, `prose-2xl` |
| Gray themes | `prose-gray`, `prose-slate`, `prose-zinc`, `prose-neutral`, `prose-stone` |
| Light text palette | `prose-invert` |
| Exclude a descendant subtree | `not-prose` |

Size and color modifiers go alongside `prose`, for example `class="prose prose-lg prose-stone"`. At the default 16px root font size, the five text scales are 14, 16, 18, 20 and 24px. `prose-invert` changes text colors; provide your own dark background.

`not-prose` skips Typography's descendant selectors. Normal inheritance still applies, so an embedded widget should keep its own font/color styles when those need to differ from the surrounding article. The example demonstrates this with an existing styled widget and native controls.

The bundle contains these classes and their article element rules. Add other desired classes to `@source inline(...)` in [input.css](./input.css) and rebuild. Responsive variants, `dark:` variants, element modifiers and general Tailwind utilities are not included in this frozen file.

## Page styles and long content

The stylesheet uses a single CSS layer named `typography`. It omits global Preflight and emits no global theme color variables. Small rules scoped to `.prose`, excluding `not-prose`, supply the table and quote border defaults needed without Preflight. Your existing unlayered CSS takes precedence over rules in this layer; check the article in its actual host styles.

The plugin scrolls long code blocks. Wrap a wide table in a container with `overflow-x: auto` to keep it reachable on narrow screens, as shown in `index.html` and `demo.css`:

```html
<div style="max-width: 100%; overflow-x: auto">
  <table style="min-width: 900px">
    <!-- your wide table -->
  </table>
</div>
```

## Rebuild the file

The source and lockfile are included. To reproduce the build, use Node.js 24 (tested with 24.19.0) and run these commands in this directory:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
```

The build uses the official CLI to generate `typography.min.css`. `source(none)` prevents unrelated HTML files from changing which classes are generated. The source imports the theme values and utilities separately and does not import Preflight.

Keep the license notice at the top of the CSS and the [upstream MIT notices](./THIRD-PARTY-LICENSES.txt) with redistributed copies. The example's own source is also [MIT licensed](./LICENSE).

## Validation and browser support

The official CLI build was checked with Node.js 24.19.0 on macOS 14.6 arm64. A clean install from the lockfile reproduced the compiled CSS byte for byte.

Software-operated Chromium 153.0.8010.12 checks loaded only copied HTML/CSS assets, with JavaScript disabled. At desktop and 375px widths, they checked article styles, all five sizes/themes, inversion and scrolling to the end of long code/table content without page overflow. Adding the stylesheet to an existing document preserved typed drafts, native control state, outside/not-prose styles and an existing theme token. The copy also worked with network access offline. Omitted-CSS and omitted-plugin controls failed typography checks; a build adding global Preflight failed the existing-style comparison.

These checks use the included synthetic page. Other browsers and the requester's site have not been verified. The stylesheet contains no runtime JavaScript or external font/asset requests.

Tailwind v4 targets [modern browsers](https://tailwindcss.com/docs/compatibility#browser-support). Check your own browser targets and site styles when adopting this file.

Sources: [official Typography usage](https://github.com/tailwindlabs/tailwindcss-typography#readme), [official CLI](https://tailwindcss.com/docs/installation/tailwind-cli), [explicit class generation](https://tailwindcss.com/docs/detecting-classes-in-source-files#safelisting-specific-utilities), [Preflight configuration](https://tailwindcss.com/docs/preflight#disabling-preflight), and the [original prebuilt-CSS request](https://github.com/tailwindlabs/tailwindcss/discussions/20542).

## Optional coffee

This example is free. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
