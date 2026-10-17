"""Inspect ID3 comment origins and prepare a new copy for mid3iconv."""

import argparse
from io import BytesIO
import json
from pathlib import Path
import shutil

from mutagen import MutagenError
from mutagen.id3 import COMM, ID3, ID3NoHeaderError


def read_tags(path):
    """Return the default merged view and a view of actual ID3v2 frames."""
    merged = ID3(path)
    try:
        actual_v2 = ID3(path, load_v1=False, translate=False)
    except ID3NoHeaderError:
        actual_v2 = None
    return merged, actual_v2


def inspect(path):
    merged, actual_v2 = read_tags(path)
    with path.open("rb") as source:
        source.seek(0, 2)
        has_v1 = False
        if source.tell() >= 128:
            source.seek(-128, 2)
            has_v1 = source.read(3) == b"TAG"
    return {
        "has_v2": actual_v2 is not None,
        "has_v1": has_v1,
        "comments": [
            {"key": key, "language": frame.lang, "description": frame.desc,
             "text": list(frame.text),
             "in_v2": actual_v2 is not None and key in actual_v2}
            for key, frame in sorted(merged.items()) if isinstance(frame, COMM)
        ],
    }


def prepare(source, output, selected):
    merged, actual_v2 = read_tags(source)
    if actual_v2 is None:
        raise ValueError("source has no ID3v2 header; keep its v1 metadata and diagnose separately")
    if selected in actual_v2:
        raise ValueError("selected key is already in ID3v2; its origin needs separate diagnosis")
    if selected not in merged or not isinstance(merged[selected], COMM):
        raise ValueError("select the exact key of an imported COMM shown by inspect")
    if actual_v2.version[1] not in (3, 4):
        raise ValueError("this copy recipe supports only ID3v2.3/v2.4; diagnose older tags separately")
    reject_unknown_frames(actual_v2)
    translated_v2 = ID3(source, load_v1=False)
    if frame_view(actual_v2) != frame_view(translated_v2):
        raise ValueError("automatic v2.4 translation changes source frames; diagnose version-specific metadata separately")
    del merged[selected]

    # Validate the actual v2.4 serialization in memory before creating a copy.
    # A known empty text frame, for example, can load successfully but be omitted.
    before_save = frame_view(merged)
    with BytesIO() as buffer:
        merged.save(buffer, v1=0, v2_version=4)
        buffer.seek(0)
        round_trip = ID3(buffer, load_v1=False, translate=False)
        if frame_view(round_trip) != before_save:
            raise ValueError("loaded metadata cannot round-trip through v2.4 unchanged; diagnose separately")

    # Exclusive creation also refuses source aliases, existing files and symlinks.
    # Keep the handle open so Mutagen saves into the file we created.
    with output.open("xb+") as destination:
        try:
            with source.open("rb") as original:
                shutil.copyfileobj(original, destination)
            destination.flush()
            destination.seek(0)
            merged.save(destination, v1=0, v2_version=4)
        except BaseException:
            destination.close()
            output.unlink()
            raise
    return {"output": str(output), "removed": selected, "encoding_conversion": "pending"}


def frame_view(tags):
    """Compare complete known-frame representations on the pinned version."""
    return {key: repr(frame) for key, frame in tags.items()}


def reject_unknown_frames(tags):
    if tags.unknown_frames:
        raise ValueError("unrecognized ID3 frames need separate preservation/migration")
    for frame in tags.values():
        nested = getattr(frame, "sub_frames", None)
        if nested is not None:
            reject_unknown_frames(nested)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspection = commands.add_parser("inspect", help="show actual-v2 and imported comments")
    inspection.add_argument("source", type=Path)
    preparation = commands.add_parser("prepare", help="prepare a new copy, without converting encoding")
    preparation.add_argument("source", type=Path)
    preparation.add_argument("output", type=Path)
    preparation.add_argument("--drop-imported-comment", required=True, metavar="EXACT_KEY")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect(args.source)
        else:
            result = prepare(args.source, args.output, args.drop_imported_comment)
    except (OSError, MutagenError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
