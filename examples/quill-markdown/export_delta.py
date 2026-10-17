"""Export the documented text subset of a Quill document Delta as Markdown.

Python 3.10+, standard library only. See README.md for the supported formats.
"""

import argparse
import html
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit


INLINE = {"bold", "italic", "underline", "link"}
BLOCK = {"header", "list", "indent"}
MARKDOWN_PUNCTUATION = set("\\`*_{}[]()#+-.!|~=")


def _validate_attributes(attributes, text):
    if not isinstance(attributes, dict):
        raise ValueError("attributes must be an object")
    unknown = attributes.keys() - INLINE - BLOCK
    if unknown:
        raise ValueError(f"unsupported attributes: {', '.join(map(str, unknown))}")
    for name in ("bold", "italic", "underline"):
        if name in attributes and attributes[name] is not True:
            raise ValueError(f"{name} must be true in a document snapshot")
    if "link" in attributes:
        link = attributes["link"]
        if not isinstance(link, str) or not link or any(
                (char.isspace() and char != " ") or ord(char) < 32 or ord(char) == 127
                or 0xD800 <= ord(char) <= 0xDFFF or char == "\\" for char in link):
            raise ValueError("link must be a nonempty URL without controls, invalid Unicode or backslashes")
        try:
            parts = urlsplit(link)
            valid = parts.scheme in ("", "http", "https", "mailto", "tel", "sms")
            if parts.scheme in ("http", "https") or (not parts.scheme and parts.netloc):
                valid = bool(parts.hostname) and not any(char.isspace() for char in parts.hostname)
                parts.port  # Reject invalid ports too.
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("unsupported link: use HTTP(S), mailto, tel, sms, or a relative/fragment URL")
    if "header" in attributes:
        value = attributes["header"]
        if type(value) is not int or value not in (1, 2, 3):
            raise ValueError("header must be the integer 1, 2 or 3")
    if "list" in attributes and attributes["list"] not in ("ordered", "bullet"):
        raise ValueError("list must be ordered or bullet")
    if "header" in attributes and "list" in attributes:
        raise ValueError("a line cannot be both a header and a list item")
    if "indent" in attributes:
        value = attributes["indent"]
        if "list" not in attributes or type(value) is not int or not 0 <= value <= 8:
            raise ValueError("indent is supported only for lists, as an integer from 0 to 8")
    if attributes.keys() & BLOCK and not text.endswith("\n"):
        raise ValueError("line formats must be attached to an insert ending in a newline")


def _render_spans(spans):
    """Escape prose before adding our own inline HTML; keep edge/repeated spaces."""
    plain = "".join(text for text, _ in spans)
    position = 0
    rendered = []
    for text, attributes in spans:
        escaped = []
        for char in text:
            if char == " " and (position == 0 or position == len(plain) - 1
                                or plain[position - 1] == " " or plain[position + 1] == " "):
                escaped.append("&#160;")
            elif char in "&<>":
                escaped.append(html.escape(char, quote=False))
            elif char in MARKDOWN_PUNCTUATION:
                escaped.append("\\" + char)
            else:
                escaped.append(char)
            position += 1
        run = "".join(escaped)
        for name, tag in (("bold", "strong"), ("italic", "em"), ("underline", "u")):
            if name in attributes:
                run = f"<{tag}>{run}</{tag}>"
        if "link" in attributes:
            run = f'<a href="{html.escape(attributes["link"], quote=True)}">{run}</a>'
        rendered.append(run)
    return "".join(rendered)


def convert_delta(document) -> str:
    """Convert a complete, supported document snapshot; raise ValueError on loss.

    No file is read or written by this function. Attributes on each newline
    select its line format; preceding text runs keep their own inline formats.
    """
    if not isinstance(document, dict) or set(document) != {"ops"}:
        raise ValueError("expected a document object containing only an ops array")
    operations = document["ops"]
    if not isinstance(operations, list) or not operations:
        raise ValueError("ops must be a nonempty array ending with a newline")

    lines = []
    spans = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or not {"insert"} <= operation.keys() <= {"insert", "attributes"}:
            raise ValueError(f"op {index}: expected insert, not retain/delete or other keys")
        text = operation["insert"]
        if not isinstance(text, str) or not text:
            raise ValueError(f"op {index}: only nonempty text inserts are supported; embeds are unsupported")
        if any((ord(char) < 32 and char != "\n") or ord(char) == 127
               or 0xD800 <= ord(char) <= 0xDFFF for char in text):
            raise ValueError(f"op {index}: tabs, control characters and unpaired surrogates are unsupported")
        attributes = operation.get("attributes", {})
        _validate_attributes(attributes, text)
        chunks = text.split("\n")
        for offset, chunk in enumerate(chunks):
            if chunk:
                spans.append((chunk, attributes))
            if offset < len(chunks) - 1:
                lines.append((spans, {name: attributes[name] for name in BLOCK if name in attributes}))
                spans = []
    if not operations[-1]["insert"].endswith("\n"):
        raise ValueError("a complete Quill document must end with a newline")

    output = []
    lists = []
    for spans, attributes in lines:
        content = _render_spans(spans)
        if "list" not in attributes:
            if output:
                output.append("")
            lists.clear()
            if "header" in attributes:
                output.append("#" * attributes["header"] + " " + (content or "<br>"))
            else:
                output.append(content or "<p><br></p>")
            continue

        depth = attributes.get("indent", 0)
        if depth > len(lists):
            raise ValueError("list indentation must start at 0 and increase by at most one level")
        kind = attributes["list"]
        del lists[depth + 1:]
        if depth == len(lists):
            if not lists and output:
                output.append("")
            lists.append({"kind": kind, "count": 0, "padding": 0})
        elif lists[depth]["kind"] != kind:
            output.append("")
            lists[depth] = {"kind": kind, "count": 0, "padding": 0}
        context = lists[depth]
        context["count"] += 1
        marker = f'{context["count"]}. ' if kind == "ordered" else "- "
        padding = lists[depth - 1]["padding"] if depth else 0
        context["padding"] = padding + len(marker)
        output.append(" " * padding + marker + (content or "<br>"))
    return "\n".join(output) + "\n"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 JSON from quill.getContents()")
    parser.add_argument("output", type=Path, help="Markdown destination (replaced on success)")
    arguments = parser.parse_args()
    temporary = None
    try:
        source, destination = arguments.input, arguments.output
        if source.resolve() == destination.resolve() or (
                destination.exists() and source.samefile(destination)):
            raise ValueError("input and output must be different files, including hardlink aliases")
        document = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        markdown = convert_delta(document)
        # The complete document has passed validation before creating any output.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=destination.parent, prefix=".quill-export-",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(markdown)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
