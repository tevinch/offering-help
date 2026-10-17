# Export a saved Quill chapter to Markdown with Python

If a chapter has several differently styled pieces of text in one paragraph, adjacent Delta operations are not pairs. Each text insert carries its own inline styles. A newline carries the format of the line it ends. One insert can also contain several newlines.

This example reads a complete saved Delta JSON file and exports the text formats below. It addresses the Python file export workflow discussed in [Quill #4828](https://github.com/slab/quill/discussions/4828). It is a small example to adapt, with no package installation or extra runtime required for export.

## Run it

Use Python 3.10 or newer. From the repository root:

```sh
python3 examples/quill-markdown/export_delta.py examples/quill-markdown/chapter.json chapter-export.md
python3 -m unittest discover -s examples/quill-markdown -v
```

The first command writes `chapter-export.md`. Compare it with the included [`chapter.md`](chapter.md). To export another saved chapter, supply its JSON path and a different Markdown path:

```sh
python3 examples/quill-markdown/export_delta.py my-chapter.json my-chapter.md
```

Save the complete document returned by [`quill.getContents()`](https://quilljs.com/docs/api#getcontents), including the final newline. A `text-change` event Delta can describe edits to an existing document and is not a complete chapter. The input shape is `{"ops": [...]}`; it must contain only text `insert` operations and optional `attributes` objects.

To call it from Python, place `export_delta.py` alongside your own script:

```python
import json
from pathlib import Path
from export_delta import convert_delta

document = json.loads(Path("my-chapter.json").read_text(encoding="utf-8"))
markdown = convert_delta(document)
```

`convert_delta(document)` returns a string or raises `ValueError`. Use the CLI when writing a file: it validates and converts the whole chapter, writes a temporary file beside the destination, then replaces the destination. A validation or write error returns a nonzero exit status and leaves existing destination content intact. Input and output cannot be the same file, including symlink and hardlink aliases. The destination directory must already exist.

## Supported scope

| Content | Output and limits |
| --- | --- |
| Plain paragraphs and Unicode text | Markdown paragraphs; each Delta newline ends a paragraph or other block. Literal Markdown punctuation and HTML are escaped. |
| Bold, italic, underline, combinations | Inline `<strong>`, `<em>` and `<u>` tags retain styles without Markdown emphasis delimiter edge cases. Active values must be `true`. |
| Links | Inline `<a>` tags; `http`, `https`, `mailto`, `tel`, `sms`, relative paths, fragments and protocol-relative URLs. Original `href` text, including ordinary spaces, is retained and HTML-escaped. Controls, invalid Unicode, backslashes and other explicit schemes are rejected. |
| Headings | Markdown levels 1–3, selected by the newline's integer `header` attribute. |
| Ordered and bullet lists | Markdown lists. Ordered siblings count consecutively; a change of list type or an intervening paragraph starts a new list. |
| Nested lists | Integer `indent` from 0–8, attached to list newlines. A list starts at 0 and can increase only one level at a time. Nested type switches and returning to a parent are supported. |
| Blank paragraphs | Explicit `<p><br></p>` blocks; empty headings and list items use `<br>`. Repeated Markdown blank lines alone cannot retain empty paragraphs. |
| Repeated, leading and trailing spaces | Nonbreaking space entities keep these spaces visible. Ordinary single spaces between words remain spaces. This preserves prose spacing rather than byte-for-byte text identity. |

Render the result with a CommonMark renderer that allows HTML and retains these tags. Underline and explicit empty paragraphs depend on that support; a renderer that strips HTML will change the result. This is a format conversion for the listed text subset, not a universal or lossless Quill renderer.

Relative links resolve against the exported document's location or its renderer's base URL. The converter does not rewrite destinations, fetch links, or check whether they exist. Link schemes follow [Quill 2.0.3's link format](https://github.com/slab/quill/blob/v2.0.3/packages/quill/src/formats/link.ts); HTTP(S) and protocol-relative URLs must have a hostname and a valid port if supplied.

The converter rejects embeds (including images), custom attributes, colors, fonts, alignment, code blocks, blockquotes, strike-through, checklists and other unlisted formats. It also rejects `retain`/`delete` changes, missing final newlines, invalid attribute values, line formats attached to inserts without a trailing newline, skipped list indentation, tabs and control characters. The CLI rejects malformed JSON and duplicate object keys. Unsupported content fails explicitly instead of producing an export with silently missing text or styles.

The listed inline styles, headings and flat lists match Quill 2.0.3's default Snow toolbar. Pasted content and custom editor settings can introduce formats outside this scope. Keep the original JSON for editing and future exports.

## How it works and what is checked

The converter accumulates text runs until each newline, renders the runs with their own inline attributes, then selects the block type from that newline's attributes. It never relies on whether an operation is odd or even in the array.

The fixture includes a heading, many inline runs in one paragraph, combined styles, a link, multiple newlines in one insert, Unicode, literal markup, a blank paragraph and mixed nested lists. The standard-library test suite checks those results plus contact/relative links, repeated export, revised content, input preservation and failure without replacing a previous export. The full 25-test suite passed on Python 3.12.4.

For the data model, see the official [Delta reference](https://quilljs.com/docs/delta) and [design guide](https://quilljs.com/docs/guides/designing-the-delta-format). If your export already runs beside a browser editor and HTML meets your needs, Quill also provides [`getSemanticHTML()`](https://quilljs.com/docs/api#getsemantichtml).

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
