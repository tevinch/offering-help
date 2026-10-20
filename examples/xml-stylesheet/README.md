# Keep XML reports and XSL stylesheets in separate files

An XML report can keep its own URL and its separate `estilo.xsl` stylesheet when using [XSLT Polyfill](https://github.com/mfreed7/xslt_polyfill). Put the two XHTML script elements **inside the existing XML root**, before the data:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="estilo.xsl"?>
<ficha>
  <script xmlns="http://www.w3.org/1999/xhtml">window.xsltUsePolyfillOnlyIfNeeded = true;</script>
  <script src="vendor/xslt-polyfill.min.js" xmlns="http://www.w3.org/1999/xhtml"></script>

  <studentHeader><!-- your existing data --></studentHeader>
  <!-- tarea, trabajo, examen, calif, nota ... -->
</ficha>
```

Placing those scripts before `<ficha>` creates multiple top-level elements. [XML requires exactly one root element](https://www.w3.org/TR/xml/#sec-well-formed), so that placement can produce a parsing error or a blank transformed page. The XML file does not need HTML `<head>` or `<body>` elements. The stylesheet produces the HTML report.

## Try the complete example

[report.xml](report.xml) contains synthetic report data; [estilo.xsl](estilo.xsl) renders homework, papers, exams, the summary and notices. No real student records are included.

Save these two files in the same directory, then download the fixed library version and its license:

```sh
mkdir -p vendor
curl --fail --location --output vendor/xslt-polyfill.min.js \
  https://cdn.jsdelivr.net/npm/xslt-polyfill@1.0.31/xslt-polyfill.min.js
curl --fail --location --output vendor/LICENSE.xslt-polyfill \
  https://cdn.jsdelivr.net/npm/xslt-polyfill@1.0.31/LICENSE
```

You can also open those two download links in a browser and save the files under the same names. The JavaScript file's SHA-256 is `186ed479a219268fbe4a2e69c6dacec7c619b68a5f8858fb6dd8ed4ba46fd3bf`.

The files served by your existing HTTP(S) host should be:

```text
report.xml
estilo.xsl
vendor/
  xslt-polyfill.min.js
  LICENSE.xslt-polyfill
```

For a local preview, if Python is available, run this from that directory:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/report.xml`. It should show “Sample grade report”, two homework rows, one paper, two exams, notices and a final score of `08.00`. Reloading should show the same report. Narrow screens can scroll the wider tables horizontally.

The deployed files are static; they do not require Node.js, a build step or a server-side application. Use HTTP(S) rather than opening `report.xml` as a local file, because the polyfill fetches its resources. Serve the XML and stylesheet as XML, such as `application/xml`, and the library as JavaScript. Keep their relative paths valid; the polyfill's resource requests are subject to normal same-origin/CORS rules.

## Native browsers and the fallback

In a browser with native XSLT, the `xml-stylesheet` instruction transforms the source before these source scripts execute. This example's stylesheet selects the report data explicitly and does not copy the loader scripts into the result, so the native path does not download the polyfill.

When native XSLT is unavailable, the XHTML scripts can run and the library performs the transformation. The setting appears before the library, as required by the [upstream usage guide](https://github.com/mfreed7/xslt_polyfill#usage). Setting it in the source XML does not force a browser with native XSLT to run the fallback.

When adapting an existing stylesheet, keep its data templates and check that it does not copy the loader scripts into the output or render their text through generic templates. This sample uses explicit selections such as `tarea`, `trabajo` and `examen`. If your data uses a default XML namespace, its XSLT selectors also need the corresponding namespace prefixes; this sample follows a non-namespaced `ficha` structure.

## Checked behavior

Checked with XSLT Polyfill **1.0.31** in Chromium **151.0.7922.34**, at desktop and narrow widths, with native XSLT enabled and disabled in separate test browser processes. Both paths rendered all report sections, preserved accented text, Chinese text and escaped `<`/`&` content, and handled repeated reloads plus a second synthetic report. The fallback check confirmed the library actually loaded and used its own processor. A valid XML control without the loader stayed untransformed when native XSLT was disabled.

The original campus stylesheet, server, student data, Firefox and Pale Moon were not tested. In particular, this example does not address Pale Moon's separate WebAssembly compatibility error.

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free to use.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
