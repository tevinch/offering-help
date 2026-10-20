"""Run actual jq processes against full-line comment configurations."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
JQ = os.environ.get("JQ", "jq")


class ReadConfigTests(unittest.TestCase):
    def run_filter(self, content, *, original=False):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "config.json"
            source.write_bytes(content)
            before = hashlib.sha256(source.read_bytes()).digest()
            args = [JQ, "."] if original else [JQ, "-Rs", "-f", str(HERE / "read-config.jq")]
            result = subprocess.run([*args, str(source)], capture_output=True)
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)
            return result

    def assert_parsed(self, text, expected):
        result = self.run_filter(text)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(result.stdout), expected)
        self.assertEqual(result.stderr, b"")

    def test_original_failure_then_complete_configuration_and_query(self):
        content = (HERE / "config.json").read_bytes()
        original = self.run_filter(content, original=True)
        self.assertNotEqual(original.returncode, 0)
        self.assertIn(b"parse error", original.stderr)
        result = self.run_filter(content)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        value = json.loads(result.stdout)
        self.assertEqual(value, {
            "service": {"endpoint": "https://example.com/a//b", "label": "literal // stays", "quote": 'say "//"'},
            "enabled": True, "items": [1, None, "中文"],
        })
        query = subprocess.run([JQ, "-r", ".service.endpoint"], input=result.stdout, capture_output=True)
        self.assertEqual(query.returncode, 0, query.stderr.decode())
        self.assertEqual(query.stdout, b"https://example.com/a//b\n")
        self.assertEqual(query.stderr, b"")

    def test_line_endings_indentation_and_final_comment(self):
        self.assert_parsed(b'{\r\n \t// disabled option\r\n "a": 1\r\n}\r\n// end', {"a": 1})

    def test_array_and_nested_comment_lines(self):
        self.assert_parsed(b'[\n// first\n"// text",\n{"x":\n  // detail\n2}\n]', ["// text", {"x": 2}])

    def test_all_json_top_level_types(self):
        for value in [False, None, True, 0, 3.5, "// text", [], {}]:
            with self.subTest(value=value):
                self.assert_parsed(b"// heading\n" + json.dumps(value).encode(), value)

    def test_unsupported_or_invalid_syntax_is_not_silently_ignored(self):
        for text in [b'{"x":1 // inline\n}', b'/* block */\n{}', b'{"x":1,\n}', b'{"x":}', b'// comments only\n', b'{}\n{}', b'']:
            with self.subTest(text=text):
                result = self.run_filter(text)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")
                self.assertIn(b"jq: error", result.stderr)


if __name__ == "__main__":
    unittest.main()
