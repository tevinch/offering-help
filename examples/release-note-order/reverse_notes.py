"""Reverse flat GitHub-generated change entries, leaving other bytes in place."""

import argparse
from pathlib import Path
import re
import sys


CHANGE = re.compile(
    r"\* .+ by @[^\s]+ in https://github\.com/[^/\s]+/[^/\s]+/pull/[1-9][0-9]*[ \t]*"
)


def _content(line: str) -> str:
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith("\n"):
        return line[:-1]
    return line


def reverse_changes(text: str) -> str:
    """Reverse one flat What's Changed list; reject unsupported list formats."""
    if "\r" in text.replace("\r\n", ""):
        raise ValueError("only LF and CRLF line endings are supported")
    lines = text.splitlines(keepends=True)
    headings = [i for i, line in enumerate(lines) if _content(line) == "## What's Changed"]
    if len(headings) != 1:
        raise ValueError("expected exactly one ## What's Changed heading")
    start = headings[0] + 1
    while start < len(lines) and not _content(lines[start]).strip():
        start += 1
    end = start
    while end < len(lines) and CHANGE.fullmatch(_content(lines[end])):
        end += 1
    boundary = end
    while boundary < len(lines) and not _content(lines[boundary]).strip():
        boundary += 1
    if boundary < len(lines):
        tail = _content(lines[boundary])
        if tail != "## New Contributors" and not tail.startswith("**Full Changelog**: "):
            raise ValueError("unsupported What's Changed content; expected flat single-line PR entries")
    contents = [_content(line) for line in lines[start:end]]
    reversed_lines = [
        content + line[len(_content(line)):]
        for content, line in zip(reversed(contents), lines[start:end])
    ]
    return "".join(lines[:start] + reversed_lines + lines[end:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 generated notes")
    parser.add_argument("output", type=Path, help="new output file (must not exist)")
    args = parser.parse_args()
    created = False
    try:
        ordered = reverse_changes(args.input.read_bytes().decode("utf-8")).encode("utf-8")
        with args.output.open("xb") as output:
            created = True
            output.write(ordered)
    except (OSError, UnicodeError, ValueError) as error:
        if created:
            args.output.unlink(missing_ok=True)
        print(f"reverse_notes: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
