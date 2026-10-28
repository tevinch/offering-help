# Try styles in the Pele playground

The [Pele playground](https://pele.run/playground) now has a **CSS** tab next to **Mermaid** in the **Source** panel. Use that tab for live CSS editing. The maintainer [added it in this change](https://github.com/obsidianmd/pele/commit/951a643e431f66700487a547c200ac124ff1a9bc) and [closed the original question](https://github.com/obsidianmd/pele/issues/48).

The native editor scopes its CSS to the Pele output, and **Copy share link** includes that editor's CSS. Its default `.pele` selector targets the diagram SVG. The `#pele-output` selector in [theme.css](./theme.css) is for the archived developer-tools workflow below; do not paste that file unchanged into the scoped CSS editor.

You can also style individual nodes and edges in Mermaid source. The earlier developer-tools approach is archived below for reference. Native CSS-tab availability and sharing were checked against the current source and page HTML on 2026-10-29; the developer-tools workflow was checked on 2026-10-22. The new CSS-tab interaction was not browser-tested for this update.

## Change individual nodes and edges

Paste [diagram.mmd](./diagram.mmd) into the playground's **Source** editor. Append these lines:

```mermaid
classDef waiting fill:#fef3c7,stroke:#d97706,color:#78350f
class review,draft waiting
style done fill:#dcfce7,stroke:#15803d,color:#14532d
linkStyle 0 stroke:#2563eb,stroke-width:3px
```

Edit a color value and watch the **Pele** output update. `classDef` defines reusable diagram styles, `style` changes one node, and `linkStyle 0` selects the first declared edge. These declarations travel with the Mermaid source, including its share link. Their fixed colors override theme colors. This syntax is part of the diagram; it is not a general CSS stylesheet editor.

## Archived: developer-tools workflow before the CSS tab (2026-10-22)

These steps describe the playground before its native CSS tab. Current native CSS defines variables on the child `.pele` SVG, which can override values inherited from the parent `#pele-output` rule below. Use the native CSS tab for current editing; the historical steps are not a verified alternative for today's defaults.

1. Start with the original [diagram.mmd](./diagram.mmd), without the extra styling lines above.
2. Right-click the Pele diagram and choose **Inspect**. In the browser's **Elements** panel, select its containing element with `id="pele-output"`.
3. In **Styles**, add a rule with selector `#pele-output`. Paste the declarations from inside the braces in [theme.css](./theme.css) into that rule. It scopes the experiment to the Pele preview and also applies to the replacement SVG when you edit the source.
4. Change `--pele-surface` to `#4c1d95`, then to `#1e3a5f`. The node fills change immediately. Try `--pele-line` for connectors and `--pele-fg` for text.
5. Edit a node's label in **Source**. The chart redraws while the container's CSS rule stays in effect. Switch between **Pele**, **SVG** and **Compare** to keep working; this rule does not style the separate Mermaid preview.
6. Delete or disable the added rule to restore the site's colors. The Mermaid source stays intact.

Color changes need no redraw. Fonts affect layout: if you set `--pele-font` or `--pele-font-mono` on `#pele-output`, make a source edit, such as adding a blank line, to make this playground measure and render again. Changing only a label's CSS font can leave its node sized for the old font. In your own application using `mount()`, call the returned handle's `refresh()` after a font change.

Developer-tool edits are temporary and normally disappear on reload. The playground's **Copy share link** includes Mermaid source and CSS from its native CSS editor; it does not include this developer-tools stylesheet. **Copy SVG** also does not package your developer-tool stylesheet; keep the CSS separately and apply it to an embedded SVG in your own page. For per-diagram colors that should travel in the source, use the first approach.

The developer-tools steps above describe the earlier preview workflow. Prefer the native CSS tab for current editing and sharing. Pele's [theming guide](https://pele.run/theming) documents its CSS variables and SVG classes; its [API guide](https://pele.run/api) explains `mount()` and `refresh()`.

## Optional coffee

This example is free. If it saves you time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
