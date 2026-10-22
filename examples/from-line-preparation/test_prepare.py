"""Exercise real Perl processing, file copies and concatenated record boundaries."""
import hashlib
import errno
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("prepare.sh")


class PreparationTests(unittest.TestCase):
    def test_null_list_preserves_order_and_unusual_filenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ["second\nline.txt", "-first file.txt", "tab\tname.txt"]
            files = [root / name for name in names]
            for index, path in enumerate(files):
                path.write_bytes(f"From {index}\r\nFrom body".encode())
            listing = root / "inputs.list0"
            listing.write_bytes(b"".join(os.fsencode(p) + b"\0" for p in files))
            out = root / "out"
            result = subprocess.run(["bash", str(SCRIPT), "--files0-from", str(listing), str(out)], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((out / "combined.txt").read_bytes(), b"From 0\r\n>From body\nFrom 1\r\n>From body\nFrom 2\r\n>From body\n")
            for index, path in enumerate(files):
                self.assertEqual(path.read_bytes(), f"From {index}\r\nFrom body".encode())
                self.assertEqual((out / "parts" / path.name).read_bytes(), f"From {index}\r\n>From body".encode())

    def test_null_list_rejects_empty_or_unterminated_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "one"
            source.write_bytes(b"From first\nFrom body\n")
            for index, payload in enumerate([b"", b"\0", os.fsencode(source), os.fsencode(source) + b"\0\0"]):
                listing = root / f"list{index}"
                listing.write_bytes(payload)
                out = root / f"out{index}"
                result = subprocess.run(["bash", str(SCRIPT), "--files0-from", str(listing), str(out)], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(out.exists())

    def test_null_list_completes_when_argument_vector_is_too_large(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root
            while len(os.fsencode(source_dir)) < 750:
                source_dir = source_dir / ("d" * 90)
                source_dir.mkdir()
            count = os.sysconf("SC_ARG_MAX") // (len(os.fsencode(source_dir)) + 10) + 64
            if count > 4000:
                self.skipTest("Host argument limit exceeds this bounded fixture")
            files = [source_dir / f"{i:05d}.txt" for i in range(count)]
            for path in files:
                path.write_bytes(b"From first\nFrom body")
            with self.assertRaises(OSError) as caught:
                subprocess.run(["bash", str(SCRIPT), str(root / "argument-output"), *map(str, files)], check=True)
            self.assertEqual(caught.exception.errno, errno.E2BIG)
            listing = root / "inputs.list0"
            listing.write_bytes(b"".join(os.fsencode(p) + b"\0" for p in files))
            out = root / "list-output"
            subprocess.run(["bash", str(SCRIPT), "--files0-from", str(listing), str(out)], check=True)
            self.assertEqual(len(list((out / "parts").iterdir())), count)
            self.assertEqual((out / "combined.txt").read_bytes(), b"From first\n>From body\n" * count)
            for path in files:
                self.assertEqual(path.read_bytes(), b"From first\nFrom body")
                self.assertEqual((out / "parts" / path.name).read_bytes(), b"From first\n>From body")

    def test_complete_workflow_and_repeat(self):
        with tempfile.TemporaryDirectory(prefix="from line example ") as tmp:
            root = Path(tmp)
            fixtures = {
                "one.txt": b"From first@example.test Thu Oct 22 10:00:00 2026\nSubject: One\n\nFrom body\n>From already quoted\nlast without newline",
                "two.txt": b"From second@example.test Thu Oct 22 11:00:00 2026\r\nSubject: Two\r\n\r\nFrom body\r\nFrom: broad match\r\nFromage too\r\n\xff\r\n",
            }
            expected = {
                "one.txt": b"From first@example.test Thu Oct 22 10:00:00 2026\nSubject: One\n\n>From body\n>From already quoted\nlast without newline",
                "two.txt": b"From second@example.test Thu Oct 22 11:00:00 2026\r\nSubject: Two\r\n\r\n>From body\r\n>From: broad match\r\n>Fromage too\r\n\xff\r\n",
            }
            inputs = []
            for name, data in fixtures.items():
                f = root / name
                f.write_bytes(data)
                inputs.append(f)
            original = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}
            out = root / "prepared"
            subprocess.run(["bash", str(SCRIPT), str(out), *map(str, inputs)], check=True)
            for name, data in expected.items():
                self.assertEqual((out / "parts" / name).read_bytes(), data)
            merged = (out / "combined.txt").read_bytes()
            self.assertEqual(merged, expected["one.txt"] + b"\n" + expected["two.txt"])
            records = re.split(rb"(?m)(?=^From)", merged)[1:]
            self.assertEqual(records, [expected["one.txt"] + b"\n", expected["two.txt"]])
            self.assertEqual({f: hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}, original)
            again = root / "again"
            subprocess.run(["bash", str(SCRIPT), str(again), *map(str, [out / "parts" / f.name for f in inputs])], check=True)
            for name, data in expected.items():
                self.assertEqual((again / "parts" / name).read_bytes(), data)
            self.assertEqual((again / "combined.txt").read_bytes(), merged)
            # Negative controls independently exercise the claimed boundaries.
            self.assertEqual(len(re.findall(rb"(?m)^From", b"".join(expected.values()))), 1)
            wrong_global = re.sub(rb"(?m)^From", b">From", fixtures["two.txt"])
            self.assertNotEqual(wrong_global, expected["two.txt"])
            self.assertNotEqual(re.sub(rb"(?m)^From", b">From", fixtures["one.txt"]), expected["one.txt"])

    def test_empty_no_match_delayed_first_and_raw_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = {
                "empty": (b"", b""),
                "none": (b"\xff\x00data\r\nFrom lower? no, here it is", b"\xff\x00data\r\nFrom lower? no, here it is"),
                "delayed": (b"preamble\r\nFrom first\r\nFrom second", b"preamble\r\nFrom first\r\n>From second"),
                "zero": (b"from lowercase\n>From escaped\n", b"from lowercase\n>From escaped\n"),
            }
            inputs = []
            for name, (data, _) in cases.items():
                f = root / name
                f.write_bytes(data)
                inputs.append(f)
            out = root / "out"
            subprocess.run(["bash", str(SCRIPT), str(out), *map(str, inputs)], check=True)
            for name, (data, wanted) in cases.items():
                self.assertEqual((out / "parts" / name).read_bytes(), wanted)
                self.assertEqual((root / name).read_bytes(), data)

    def test_refuses_existing_output_and_duplicate_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "one.txt"
            f.write_bytes(b"From one\nFrom body\n")
            existing = root / "existing"
            existing.mkdir()
            marker = existing / "keep.txt"
            marker.write_bytes(b"unchanged")
            r = subprocess.run(["bash", str(SCRIPT), str(existing), str(f)], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(marker.read_bytes(), b"unchanged")
            d = root / "other"
            d.mkdir()
            other = d / f.name
            other.write_bytes(b"From different\n")
            out = root / "collision"
            r = subprocess.run(["bash", str(SCRIPT), str(out), str(f), str(other)], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse((out / "combined.txt").exists())
            self.assertEqual(f.read_bytes(), b"From one\nFrom body\n")
            self.assertEqual(other.read_bytes(), b"From different\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
