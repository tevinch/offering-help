# AsciiDoc preview colors

Set the IntelliJ AsciiDoc preview's body background and table of contents colors with a shared docinfo file. This adds CSS to the existing stylesheet and keeps the native layout, code, table, and admonition styles.

For the ordinary standalone AsciiDoc preview with JCEF or JavaFX. Swing does not support this styling. Antora uses different styles and is outside this example.

1. In your documentation folder, merge the two attributes from [`.asciidoctorconfig`](.asciidoctorconfig) into your existing configuration. Keep all existing attributes. The configuration also applies to subfolders.
2. Add the `<style>…</style>` block from [`.asciidoctor/docinfo.html`](.asciidoctor/docinfo.html) to your shared docinfo file. Keep its existing HTML and styles. If you have no shared docinfo setup, use the supplied folder and file.
3. Open an existing document in the preview. Adjust the six colors at the top of the style block, save, and refresh the preview if it has not updated. [The sample](sample.adoc) includes a nested TOC, table, note, and included file.

If you already set `docinfodir`, keep that directory and add the style there. If `docinfo` already includes `shared` or `shared-head`, keep it. Otherwise add `shared-head` to the existing comma-separated value; for example, `private` becomes `private,shared-head`. A document header can override these attributes; apply the same merge there if it sets them. Do not replace an existing config or docinfo file with this example.

`--preview-body-bg` sets the body background; `--preview-toc-bg` sets the TOC background. `--preview-text` sets body defaults and TOC text/title, while the remaining variables set TOC links, hover/focus links, and border. The TOC background and border need `!important` because the native dark stylesheet uses it. The title's `filter: none` prevents that stylesheet from inverting your chosen title color. An existing custom theme may require different selectors.

This is a fixed palette, not automatic light/dark switching or a complete accessibility theme. Other elements retain their existing theme colors. Check your own content after changing the palette. The supplied palette's computed body/TOC text and TOC link pairs exceeded 4.5:1 contrast in the browser check.

Verified with AsciidoctorJ 3.0.1 (Asciidoctor 2.0.26), the default CSS plus plugin 0.45.9's native dark CSS, and software-operated Chromium: full document rendering, preserved config/docinfo content and includes, TOC navigation, hover/focus, and a second palette. Actual IntelliJ/JCEF and JavaFX execution was not tested. The `:visited` rule uses the same link color; browsers hide actual visited-history colors from style inspection.

The supported loading and injection behavior is documented in the official [custom stylesheets guide](https://intellij-asciidoc-plugin.ahus1.de/docs/users-guide/features/advanced/stylesheets.html) and [configuration guide](https://intellij-asciidoc-plugin.ahus1.de/docs/users-guide/features/advanced/asciidoctorconfig-file.html), and was checked against the [0.45.9 configuration/docinfo source](https://github.com/asciidoctor/asciidoctor-intellij-plugin/blob/0.45.9/src/main/java/org/asciidoc/intellij/AsciiDocWrapper.java) and [preview source](https://github.com/asciidoctor/asciidoctor-intellij-plugin/blob/0.45.9/src/main/java/org/asciidoc/intellij/editor/jcef/AsciiDocJCEFHtmlPanel.java).

## Optional coffee

This example is free to use. If it helped, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
