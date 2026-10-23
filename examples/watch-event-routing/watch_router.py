"""One watcher, with separate handlers for text, archive and other event paths."""

import argparse
from contextlib import closing
import json
from pathlib import Path
from threading import Event

from watchfiles import Change, watch

FileChange = tuple[Change, str]


TEMPORARY_SUFFIXES = (".part", ".crdownload")


def emit_events(handler: str, changes: set[FileChange]) -> None:
    # Sort only to make the output readable: a batch is a set, not a time line.
    events = [
        {"change": change.name, "path": path,
         "temporary": path.endswith(TEMPORARY_SUFFIXES)}
        for change, path in sorted(changes, key=lambda event: (event[1], int(event[0])))
    ]
    print(json.dumps({"handler": handler, "events": events}), flush=True)


def handle_text(changes: set[FileChange]) -> None:
    emit_events("text", changes)


def handle_archives(changes: set[FileChange]) -> None:
    # Temporary-file events stay available to an application-specific policy.
    emit_events("archives", changes)


def handle_other(changes: set[FileChange]) -> None:
    emit_events("other", changes)


def dispatch(changes: set[FileChange]) -> None:
    text: set[FileChange] = set()
    archives: set[FileChange] = set()
    other: set[FileChange] = set()
    for event in changes:
        path = event[1]
        base = path
        for suffix in TEMPORARY_SUFFIXES:
            if base.endswith(suffix):
                base = base[:-len(suffix)]
                break
        if base.endswith(".txt"):
            text.add(event)
        elif base.endswith(".tar.gz"):
            archives.add(event)
        else:
            other.add(event)

    if text:
        handle_text(text)
    if archives:
        handle_archives(archives)
    if other:
        handle_other(other)


def run(paths: list[Path], stop_event: Event | None = None) -> None:
    announced = False
    # Timeout yields let the CLI announce readiness after the watcher is opened.
    with closing(watch(*paths, watch_filter=None, stop_event=stop_event,
                       debounce=200, step=50, rust_timeout=200,
                       yield_on_timeout=True, raise_interrupt=False)) as batches:
        for changes in batches:
            if not announced:
                print(json.dumps({"status": "watching"}), flush=True)
                announced = True
            dispatch(changes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", type=Path, nargs="+")
    args = parser.parse_args()
    paths = [path.resolve() for path in args.directories]
    if any(not path.is_dir() for path in paths):
        parser.error("each path must be an existing directory")
    try:
        run(paths)
    except KeyboardInterrupt:
        pass
    print(json.dumps({"status": "stopped"}), flush=True)


if __name__ == "__main__":
    main()
