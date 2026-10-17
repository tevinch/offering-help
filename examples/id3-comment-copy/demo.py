"""Run the complete example on original synthetic tags and silent MPEG frames."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from mutagen.id3 import ID3

from synthetic_fixture import (
    AUDIO_PAYLOAD, CONVERTED_TEXT, IMPORTED_KEY, MAIN_COMMENT, make_fixture, media_payload,
)


def run(*args):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout or "command failed")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="new directory for the synthetic files")
    args = parser.parse_args()
    try:
        args.directory.mkdir()  # Refuse to reuse an existing directory.
        source = make_fixture(args.directory / "original.mp3")
        original_bytes = source.read_bytes()
        baseline = args.directory / "baseline.mp3"
        shutil.copyfile(source, baseline)
        converter = Path(sys.executable).with_name("mid3iconv")
        script = Path(__file__).with_name("id3_comment_copy.py")
        before = json.loads(run(sys.executable, script, "inspect", source))
        run(converter, "-q", "-e", "shift_jis", "--remove-v1", baseline)
        run(sys.executable, script, "prepare", source, args.directory / "converted.mp3",
            "--drop-imported-comment", IMPORTED_KEY)
        output = args.directory / "converted.mp3"
        run(converter, "-q", "-e", "shift_jis", "--remove-v1", output)
        after = json.loads(run(sys.executable, script, "inspect", output))
        tags = ID3(output, load_v1=False)
        checks = {
            "baseline_imported_comment_is_now_in_v2": IMPORTED_KEY in ID3(baseline, load_v1=False),
            "selected_comment_absent": IMPORTED_KEY not in tags,
            "source_unchanged": source.read_bytes() == original_bytes,
            "media_payload_unchanged": media_payload(output) == AUDIO_PAYLOAD,
            "main_comment_preserved": tags["COMM:Main:jpn"].text == [MAIN_COMMENT],
            "other_fallback_preserved": (str(tags["TIT2"]) == "Legacy title"
                                         and str(tags["TPE1"]) == "Legacy artist"
                                         and str(tags["TRCK"]) == "7"),
            "encoding_converted": tags["TXXX:Work note"].text == [CONVERTED_TEXT],
            "v1_tail_removed": not after["has_v1"],
        }
        if not all(checks.values()):
            raise RuntimeError(f"verification failed: {checks}")
        print(json.dumps({**checks, "converted_work_note": tags["TXXX:Work note"].text[0],
                          "comments_before": before["comments"],
                          "comments_after": after["comments"]}, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
