"""Extract JSON authoring records to PO and compile reviewed translations back."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import re
from pathlib import Path
import sys

from translate.storage.pypo import pofile, pounit


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_catalog(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(data, dict) or not data:
        raise ValueError("catalog must be a nonempty JSON object")
    for key, entry in data.items():
        if not key or not isinstance(entry, dict):
            raise ValueError(f"invalid entry: {key!r}")
        if not isinstance(entry.get("defaultMessage"), str) or not entry["defaultMessage"]:
            raise ValueError(f"{key}: defaultMessage must be a nonempty string")
        if not isinstance(entry.get("description", ""), str):
            raise ValueError(f"{key}: description must be a string")
        flags = entry.get("weblateFlags", [])
        if not isinstance(flags, list) or any(not isinstance(f, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", f) or f == "fuzzy" for f in flags):
            raise ValueError(f"{key}: weblateFlags must contain simple flag names, excluding the translation-state flag fuzzy")
    return data


def extract(data):
    store = pofile()
    header = store.header()
    header.target = (
        "Project-Id-Version: Messages\n"
        "MIME-Version: 1.0\n"
        "Content-Type: text/plain; charset=UTF-8\n"
        "Content-Transfer-Encoding: 8bit\n"
    )
    header.markfuzzy(False)
    for key, entry in data.items():
        unit = pounit(entry["defaultMessage"])
        unit.setcontext(key)
        unit.addnote(entry.get("description", ""), "developer")
        for flag in entry.get("weblateFlags", []):
            unit.settypecomment(flag)
        store.addunit(unit)
    return bytes(store)


def compile_catalog(data, path):
    with Path(path).open("rb") as source:
        store = pofile(source)
    units = {}
    for unit in store.units:
        if unit.isheader() or unit.isobsolete():
            continue
        key = unit.getcontext()
        if key not in data or key in units:
            raise ValueError(f"unknown or duplicate PO context: {key!r}")
        if unit.hasplural():
            raise ValueError(f"{key}: this recipe expects one PO message per JSON record")
        if unit.source != data[key]["defaultMessage"]:
            raise ValueError(f"{key}: source differs; update the PO from the current POT first")
        if unit.isfuzzy() or not unit.target:
            raise ValueError(f"{key}: translation is fuzzy or empty; review it before compiling")
        for flag in data[key].get("weblateFlags", []):
            if not unit.hastypecomment(flag):
                raise ValueError(f"{key}: required flag is missing from PO: {flag}")
        units[key] = unit
    if set(units) != set(data):
        raise ValueError("PO does not contain every catalog context")
    result = deepcopy(data)
    for key, unit in units.items():
        result[key]["defaultMessage"] = str(unit.target)
    return (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")



def refresh_metadata(data, path):
    """Restore source-owned simple flags after GNU msgmerge's filtering."""
    with Path(path).open("rb") as source:
        store = pofile(source)
    seen = set()
    for unit in store.units:
        if unit.isheader() or unit.isobsolete():
            continue
        key = unit.getcontext()
        if key not in data or key in seen or unit.source != data[key]["defaultMessage"]:
            raise ValueError(f"unexpected merged context/source: {key!r}")
        seen.add(key)
        existing = [flag.strip() for line in unit.typecomments for flag in line.removeprefix("#,").strip().split(",") if flag.strip()]
        if any(not re.fullmatch(r"[a-z][a-z0-9-]*", flag) for flag in existing):
            raise ValueError(f"{key}: this recipe only refreshes simple, unparameterized flags")
        for flag in existing:
            if flag != "fuzzy":
                unit.settypecomment(flag, False)
        for flag in data[key].get("weblateFlags", []):
            unit.settypecomment(flag)
    if seen != set(data):
        raise ValueError("merged PO does not contain every catalog context")
    return bytes(store)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    extract_parser = commands.add_parser("extract")
    extract_parser.add_argument("source_json")
    extract_parser.add_argument("output_pot")
    compile_parser = commands.add_parser("compile")
    compile_parser.add_argument("source_json")
    compile_parser.add_argument("translated_po")
    compile_parser.add_argument("output_json")
    refresh_parser = commands.add_parser("refresh-flags")
    refresh_parser.add_argument("source_json")
    refresh_parser.add_argument("merged_po")
    refresh_parser.add_argument("output_po")
    args = parser.parse_args()
    try:
        data = load_catalog(args.source_json)
        if args.command == "extract":
            payload, destination = extract(data), args.output_pot
        elif args.command == "compile":
            payload, destination = compile_catalog(data, args.translated_po), args.output_json
        else:
            payload, destination = refresh_metadata(data, args.merged_po), args.output_po
        # The source and any existing destination are never overwritten.
        with Path(destination).open("xb") as output:
            output.write(payload)
    except (ValueError, OSError) as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
