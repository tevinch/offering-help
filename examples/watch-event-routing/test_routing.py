import contextlib
import io
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from watchfiles import Change
from watch_router import dispatch


class DispatchTests(unittest.TestCase):
    def test_mixed_batch_keeps_archive_companions_together(self):
        # Dropping temporary events, misrouting .tar.gz, or splitting one batch fails.
        changes = {
            (Change.added, "/sample/note.txt"),
            (Change.modified, "/sample/report.tar.gz"),
            (Change.deleted, "/sample/report.tar.gz.part"),
            (Change.modified, "/sample/other.tar.gz.crdownload"),
            (Change.deleted, "/sample/note.txt.part"),
            (Change.added, "/sample/image.png"),
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            dispatch(changes)
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        by_handler = {record["handler"]: record["events"] for record in records}
        self.assertEqual(len(records), 3)
        self.assertEqual(by_handler, {
            "text": [
                {"change": "added", "path": "/sample/note.txt", "temporary": False},
                {"change": "deleted", "path": "/sample/note.txt.part", "temporary": True},
            ],
            "archives": [
                {"change": "modified", "path": "/sample/other.tar.gz.crdownload", "temporary": True},
                {"change": "modified", "path": "/sample/report.tar.gz", "temporary": False},
                {"change": "deleted", "path": "/sample/report.tar.gz.part", "temporary": True},
            ],
            "other": [{"change": "added", "path": "/sample/image.png", "temporary": False}],
        })
        self.assertEqual(len(changes), 6)

    def test_empty_batch_does_not_call_handlers(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            dispatch(set())
        self.assertEqual(output.getvalue(), "")


@unittest.skipUnless(os.name == "posix", "The CLI stop check uses POSIX SIGINT")
class LiveRoutingTests(unittest.TestCase):
    def test_real_file_changes_reach_handlers_and_keep_watching(self):
        # Omitting the real watcher, a root, a handler, or clean shutdown fails.
        with tempfile.TemporaryDirectory(prefix="routing sample ") as temporary:
            base = Path(temporary).resolve()
            first, second = base / "first", base / "second"
            first.mkdir()
            second.mkdir()
            messages = queue.Queue()
            records = []
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith("WATCHFILES_")}
            env.update(WATCHFILES_DEBUG="1", WATCHFILES_FORCE_POLLING="false")
            with tempfile.TemporaryFile(mode="w+") as errors:
                process = subprocess.Popen(
                    [sys.executable, str(Path(__file__).with_name("watch_router.py")),
                     str(first), str(second)],
                    stdout=subprocess.PIPE, stderr=errors, text=True, env=env,
                )
                def collect():
                    try:
                        for line in process.stdout:
                            messages.put(json.loads(line))
                    except BaseException as error:
                        messages.put(error)
                    finally:
                        messages.put(None)
                reader = threading.Thread(target=collect, daemon=True)
                reader.start()

                def wait_for(predicate, start=0):
                    deadline = time.monotonic() + 8
                    while True:
                        for record in records[start:]:
                            if predicate(record):
                                return record
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            self.fail(f"Missing expected output; received {records[start:]}")
                        try:
                            record = messages.get(timeout=remaining)
                        except queue.Empty:
                            self.fail(f"Timed out; received {records[start:]}")
                        self.assertIsNotNone(record, "CLI ended before the expected event")
                        if isinstance(record, BaseException):
                            raise record
                        records.append(record)

                def checkpoint():
                    # The controlled producer is idle here. Drain previous output before
                    # the next write, so an old event cannot satisfy the new operation.
                    deadline = time.monotonic() + 8
                    while time.monotonic() < deadline:
                        try:
                            record = messages.get(timeout=0.25)
                        except queue.Empty:
                            return len(records)
                        self.assertIsNotNone(record, "CLI ended between operations")
                        if isinstance(record, BaseException):
                            raise record
                        records.append(record)
                    self.fail("Observer did not become idle between producer operations")

                def expect(path, change, handler, start):
                    return wait_for(lambda record: record.get("handler") == handler
                                    and any(event["path"] == str(path)
                                            and event["change"] in ((change,) if isinstance(change, str) else change)
                                            for event in record.get("events", [])), start)

                try:
                    wait_for(lambda record: record.get("status") == "watching")
                    note = first / "note.txt"
                    start = checkpoint()
                    note.write_text("one", encoding="utf-8")
                    expect(note, "added", "text", start)
                    start = checkpoint()
                    note.write_text("one and two", encoding="utf-8")
                    expect(note, ("added", "modified"), "text", start)

                    small = second / "small.tar.gz"
                    start = checkpoint()
                    small.write_bytes(b"synthetic archive content")
                    expect(small, "added", "archives", start)

                    staged = first / "large.tar.gz.part"
                    final = first / "large.tar.gz"
                    start = checkpoint()
                    staged.write_bytes(b"first piece")
                    record = expect(staged, "added", "archives", start)
                    self.assertTrue(next(e for e in record["events"] if e["path"] == str(staged))["temporary"])
                    start = checkpoint()
                    with staged.open("ab") as stream:
                        stream.write(b" plus another piece")
                    expect(staged, ("added", "modified"), "archives", start)
                    start = checkpoint()
                    staged.rename(final)
                    expect(staged, "deleted", "archives", start)
                    expect(final, "added", "archives", start)

                    # A different producer shape: final name exists while a companion is present.
                    paired = second / "paired.tar.gz"
                    companion = second / "paired.tar.gz.part"
                    start = checkpoint()
                    paired.write_bytes(b"first")
                    companion.write_bytes(b"progress")
                    expect(paired, "added", "archives", start)
                    expect(companion, "added", "archives", start)
                    start = checkpoint()
                    paired.write_bytes(b"first then second")
                    companion.unlink()
                    expect(paired, ("added", "modified"), "archives", start)
                    expect(companion, "deleted", "archives", start)

                    chrome = first / "next.tar.gz.crdownload"
                    chrome_final = first / "next.tar.gz"
                    start = checkpoint()
                    chrome.write_bytes(b"synthetic next archive")
                    expect(chrome, "added", "archives", start)
                    start = checkpoint()
                    chrome.rename(chrome_final)
                    expect(chrome, "deleted", "archives", start)
                    expect(chrome_final, "added", "archives", start)

                    start = checkpoint()
                    note.unlink()
                    expect(note, "deleted", "text", start)
                    start = checkpoint()
                    note.write_text("again", encoding="utf-8")
                    expect(note, "added", "text", start)
                    other = second / "image.png"
                    start = checkpoint()
                    other.write_bytes(b"synthetic other file")
                    expect(other, "added", "other", start)

                    # Producer-owned data is unchanged by the consumer.
                    self.assertEqual(note.read_text(encoding="utf-8"), "again")
                    self.assertEqual(small.read_bytes(), b"synthetic archive content")
                    self.assertEqual(final.read_bytes(), b"first piece plus another piece")
                    self.assertEqual(paired.read_bytes(), b"first then second")
                    self.assertEqual(chrome_final.read_bytes(), b"synthetic next archive")
                    self.assertEqual(other.read_bytes(), b"synthetic other file")
                    self.assertEqual({p.name for p in first.iterdir()}, {"note.txt", "large.tar.gz", "next.tar.gz"})
                    self.assertEqual({p.name for p in second.iterdir()}, {"small.tar.gz", "paired.tar.gz", "image.png"})

                    process.send_signal(signal.SIGINT)
                    wait_for(lambda record: record.get("status") == "stopped")
                    self.assertEqual(process.wait(timeout=5), 0)
                    reader.join(timeout=2)
                    self.assertFalse(reader.is_alive())
                    errors.seek(0)
                    diagnostic = errors.read()
                    self.assertEqual(diagnostic.count("watcher:"), 1, diagnostic)
                finally:
                    if report := os.environ.get("ROUTING_TEST_REPORT"):
                        errors.seek(0)
                        Path(report).write_text(json.dumps({"records": records, "diagnostic": errors.read()}, indent=2))
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=3)
                    reader.join(timeout=2)
                    process.stdout.close()


if __name__ == "__main__":
    unittest.main()
