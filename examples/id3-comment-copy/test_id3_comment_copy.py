"""Behavioral CLI checks using real Mutagen and original synthetic files."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from mutagen.id3 import ID3, TSIZ
from mutagen.mp3 import MP3

from synthetic_fixture import (
    AUDIO_PAYLOAD, CONVERTED_TEXT, IMPORTED_KEY, MAIN_COMMENT, OTHER_COMMENT, PICTURE_BYTES,
    make_fixture, media_payload,
)


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "id3_comment_copy.py"


def command(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True)


def convert(path):
    executable = Path(sys.executable).with_name("mid3iconv")
    return subprocess.run([str(executable), "-e", "shift_jis", "--remove-v1", str(path)],
                          capture_output=True, text=True)


class CommentCopyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = make_fixture(self.directory / "original.mp3")
        self.output = self.directory / "converted.mp3"

    def test_inspect_distinguishes_imported_and_actual_v2_comments(self):
        # Catches treating every default-loaded COMM as physical v2 data.
        before = self.source.read_bytes()
        result = command("inspect", self.source)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["has_v2"])
        self.assertTrue(report["has_v1"])
        comments = {row["key"]: row for row in report["comments"]}
        self.assertEqual(set(comments), {
            "COMM:Main:jpn", "COMM:Notes:fra", "COMM:ID3v1 Comment:eng"})
        self.assertEqual(comments[IMPORTED_KEY], {
            "key": IMPORTED_KEY, "language": "eng", "description": "ID3v1 Comment",
            "text": ["Short legacy note"], "in_v2": False})
        self.assertTrue(comments["COMM:Main:jpn"]["in_v2"])
        self.assertEqual(comments["COMM:Main:jpn"]["text"], [MAIN_COMMENT])
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(command("inspect", self.source).stdout, result.stdout)

    def test_real_mid3iconv_materializes_the_imported_comment(self):
        # Characterizes the CLI assumption that motivates this usage recipe.
        baseline = self.directory / "baseline.mp3"
        shutil.copyfile(self.source, baseline)
        self.assertNotIn(IMPORTED_KEY, ID3(baseline, load_v1=False))
        result = convert(baseline)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(baseline.read_bytes()[-128:-125], b"TAG")
        self.assertIn(IMPORTED_KEY, ID3(baseline, load_v1=False))
        self.assertEqual(ID3(baseline)["TXXX:Work note"].text, [CONVERTED_TEXT])

    def test_prepare_then_real_conversion_preserves_all_other_metadata_and_media(self):
        # Catches lost v1-only fallback, overbroad COMM removal and missing conversion.
        before = self.source.read_bytes()
        result = command("prepare", self.source, self.output,
                         "--drop-imported-comment", IMPORTED_KEY)
        self.assertEqual(result.returncode, 0, result.stderr)
        prepared = ID3(self.output, load_v1=False)
        self.assertEqual(prepared.version, (2, 4, 0))
        self.assertNotIn(IMPORTED_KEY, prepared)
        self.assertNotEqual(prepared["TXXX:Work note"].text, [CONVERTED_TEXT])
        result = convert(self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        tags = ID3(self.output, load_v1=False)
        self.assertEqual({key for key in tags if not key.startswith("PRIV:")}, {
            "COMM:Main:jpn", "COMM:Notes:fra", "TALB", "TPE2", "TXXX:Work note",
            "APIC:Sample", "WXXX:Reference",
            "TIT2", "TPE1", "TDRC", "TRCK", "TCON"})
        self.assertEqual(tags["COMM:Main:jpn"].text, [MAIN_COMMENT])
        self.assertEqual(tags["COMM:Notes:fra"].text, [OTHER_COMMENT])
        self.assertEqual(tags["TXXX:Work note"].text, [CONVERTED_TEXT])
        for key, value in {"TIT2": "Legacy title", "TPE1": "Legacy artist",
                           "TALB": "Actual v2 album", "TPE2": "Album artist",
                           "TDRC": "2026", "TRCK": "7", "TCON": "Rock"}.items():
            self.assertEqual(str(tags[key]), value, key)
        self.assertEqual(tags["APIC:Sample"].data, PICTURE_BYTES)
        self.assertEqual(tags.getall("PRIV")[0].data, b"private frame\x00\xff")
        self.assertEqual(len(tags.getall("PRIV")), 1)
        self.assertEqual(tags["WXXX:Reference"].url, "https://example.com/")
        self.assertEqual(media_payload(self.output), AUDIO_PAYLOAD)
        self.assertNotEqual(self.output.read_bytes()[-128:-125], b"TAG")
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(MP3(self.output).info.sample_rate, 44100)
        self.assertEqual(MP3(self.output).info.channels, 2)
        # A repeated real conversion neither reimports the comment nor changes values.
        converted_bytes = self.output.read_bytes()
        self.assertEqual(convert(self.output).returncode, 0)
        self.assertEqual(self.output.read_bytes(), converted_bytes)
        report = json.loads(command("inspect", self.output).stdout)
        self.assertFalse(report["has_v1"])
        self.assertTrue(all(row["in_v2"] for row in report["comments"]))

    def assert_refused_unchanged(self, source, key, output=None):
        output = self.output if output is None else output
        before = source.read_bytes()
        existed = output.exists() or output.is_symlink()
        output_before = output.read_bytes() if output.exists() else None
        result = command("prepare", source, output, "--drop-imported-comment", key)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error:", result.stderr.lower())
        self.assertEqual(source.read_bytes(), before)
        if existed:
            self.assertEqual(output.read_bytes() if output.exists() else None, output_before)
        else:
            self.assertFalse(output.exists())
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()),
                         self.initial_names)

    def test_v1_only_file_is_not_stripped_of_its_only_metadata(self):
        # Catches allowing omission-only preparation without a real v2 header.
        path = make_fixture(self.directory / "v1-only.mp3", v2=False)
        self.initial_names = sorted(p.name for p in self.directory.iterdir())
        self.assert_refused_unchanged(path, IMPORTED_KEY)

    def test_no_selected_fallback_and_non_comment_selection_are_refused(self):
        # Catches accepting arbitrary keys or a selected frame absent from the file.
        only_v2 = make_fixture(self.directory / "v2-only.mp3", v1=False)
        self.initial_names = sorted(p.name for p in self.directory.iterdir())
        for source, key in ((only_v2, IMPORTED_KEY), (self.source, "TIT2"),
                            (self.source, "COMM:missing:eng")):
            with self.subTest(key=key):
                self.assert_refused_unchanged(source, key)

    def test_physical_v2_comment_including_an_already_converted_one_is_refused(self):
        # Catches deleting by description/language without proving import provenance.
        converted = self.directory / "already.mp3"
        shutil.copyfile(self.source, converted)
        self.assertEqual(convert(converted).returncode, 0)
        self.initial_names = sorted(p.name for p in self.directory.iterdir())
        for source, key in ((self.source, "COMM:Main:jpn"), (converted, IMPORTED_KEY)):
            with self.subTest(key=key):
                self.assert_refused_unchanged(source, key)

    def test_existing_same_hardlink_and_symlink_outputs_are_never_overwritten(self):
        # Catches truncating an output or following a link back to the source.
        existing = self.directory / "existing.mp3"
        existing.write_bytes(b"valuable existing content")
        alias = self.directory / "alias.mp3"
        alias.symlink_to(self.source)
        hardlink = self.directory / "hardlink.mp3"
        hardlink.hardlink_to(self.source)
        dangling = self.directory / "dangling.mp3"
        dangling.symlink_to(self.directory / "missing-target")
        self.initial_names = sorted(p.name for p in self.directory.iterdir())
        for output in (self.source, existing, alias, hardlink, dangling):
            with self.subTest(output=output.name):
                self.assert_refused_unchanged(self.source, IMPORTED_KEY, output)

    def test_selection_is_required_and_repeat_prepare_cannot_overwrite(self):
        # Catches automatic removal and a second preparation overwriting output.
        result = command("prepare", self.source, self.output)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        first = command("prepare", self.source, self.output,
                        "--drop-imported-comment", IMPORTED_KEY)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.initial_names = sorted(p.name for p in self.directory.iterdir())
        self.assert_refused_unchanged(self.source, IMPORTED_KEY)

    def test_documented_demo_completes_real_conversion_in_a_new_directory(self):
        # Catches a demo that skips preparation, real conversion or preservation checks.
        directory = self.directory / "demo-output"
        result = subprocess.run([sys.executable, str(HERE / "demo.py"), str(directory)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["source_unchanged"])
        self.assertTrue(report["media_payload_unchanged"])
        self.assertEqual(report["converted_work_note"], "作業メモ")
        self.assertIn(IMPORTED_KEY, ID3(directory / "baseline.mp3", load_v1=False))
        self.assertNotIn(IMPORTED_KEY, ID3(directory / "converted.mp3", load_v1=False))
        self.assertEqual(media_payload(directory / "converted.mp3"), AUDIO_PAYLOAD)
        before = {path.name: path.read_bytes() for path in directory.iterdir()}
        repeated = subprocess.run([sys.executable, str(HERE / "demo.py"), str(directory)],
                                  capture_output=True, text=True)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual({path.name: path.read_bytes() for path in directory.iterdir()}, before)

    def test_version_specific_metadata_that_translation_drops_is_refused(self):
        # Catches default v2.4 translation silently dropping unrelated v2.3 TSIZ.
        tail = self.source.read_bytes()[-128:]
        tags = ID3(self.source, load_v1=False, translate=False)
        tags.add(TSIZ(encoding=0, text=["5004"]))
        tags.save(self.source, v1=0, v2_version=3)
        with self.source.open("ab") as output:
            output.write(tail)
        self.assertEqual(str(ID3(self.source, load_v1=False, translate=False)["TSIZ"]), "5004")
        self.initial_names = sorted(p.name for p in self.directory.iterdir())
        self.assert_refused_unchanged(self.source, IMPORTED_KEY)

    def test_unknown_v23_metadata_is_refused_before_creating_a_copy(self):
        # Catches forced v2.4 save silently dropping unrecognized v2.3 frame bytes.
        data = bytearray(self.source.read_bytes())
        position = 10
        while data[position] != 0:
            position += 10 + int.from_bytes(data[position + 4:position + 8], "big")
        payload = b"original custom metadata"
        frame = b"XABC" + len(payload).to_bytes(4, "big") + b"\x00\x00" + payload
        data[position:position + len(frame)] = frame
        self.source.write_bytes(data)
        self.assertEqual(len(ID3(self.source, load_v1=False, translate=False).unknown_frames), 1)
        self.initial_names = sorted(p.name for p in self.directory.iterdir())
        self.assert_refused_unchanged(self.source, IMPORTED_KEY)

    def test_loaded_empty_frame_that_serialization_omits_is_refused(self):
        # Catches known metadata surviving translation but disappearing on save.
        data = bytearray(self.source.read_bytes())
        position = 10
        while data[position] != 0:
            position += 10 + int.from_bytes(data[position + 4:position + 8], "big")
        frame = b"TIT3\x00\x00\x00\x02\x00\x00\x00\x00"
        data[position:position + len(frame)] = frame
        self.source.write_bytes(data)
        self.assertIn("TIT3", ID3(self.source))
        self.assertEqual(str(ID3(self.source)["TIT3"]), "")
        self.initial_names = sorted(p.name for p in self.directory.iterdir())
        self.assert_refused_unchanged(self.source, IMPORTED_KEY)


if __name__ == "__main__":
    unittest.main()
