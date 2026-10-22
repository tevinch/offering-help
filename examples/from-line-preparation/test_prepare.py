"""Exercise real Perl processing, file copies and concatenated record boundaries."""
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("prepare.sh")


class PreparationTests(unittest.TestCase):
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
