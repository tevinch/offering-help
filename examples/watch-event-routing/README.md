# One watcher, separate event handlers

When several categories use the same directories and watch settings, start with one `watch()` loop and dispatch each batch to separate handlers. This example routes text, archive and other paths without creating a watcher for each category.

In [watchfiles 1.3.0](https://github.com/samuelcolvin/watchfiles/blob/v1.3.0/watchfiles/main.py), each consumed `watch()` generator opens its own `RustNotify`, and the Python filter runs after the backend collects changes. Different filters therefore do not make overlapping watchers share a backend. A single watcher can also [watch several paths](https://watchfiles.helpmanual.io/api/watch/#watch).

Separate watchers are useful when roots, debounce settings or lifetimes need to differ. This is a choice about shared work and ownership; this example does not measure how expensive an additional watcher is on your filesystem.

## Run

Use Python 3.10 or newer. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt
mkdir -p sample
.venv/bin/python watch_router.py sample
```

On Windows, use `.venv\Scripts\python.exe` for the environment's Python. Pass more existing directories as extra arguments to the same command. Directories are watched recursively.

After `{"status": "watching"}` appears, create or change files in another terminal. Each nonempty category produces a JSON line, for example:

```json
{"handler": "archives", "events": [{"change": "added", "path": "/example/sample/report.tar.gz.part", "temporary": true}]}
```

The watcher continues across subsequent operations. Ctrl+C closes it and prints `{"status": "stopped"}`.

## Adapt the handlers

Replace `handle_text`, `handle_archives` and `handle_other` in [watch_router.py](watch_router.py) with your application's work. Each receives a set of original `(Change, path)` tuples for its category from the current batch. The example's handlers only print; they do not read or change the watched files.

Routing is case sensitive and based on path suffixes:

| Path suffix | Handler |
| --- | --- |
| `.txt`, `.txt.part`, `.txt.crdownload` | `handle_text` |
| `.tar.gz`, `.tar.gz.part`, `.tar.gz.crdownload` | `handle_archives` |
| Everything else | `handle_other` |

Only one trailing `.part` or `.crdownload` is removed for classification. The original path, event type and temporary-file events remain available to the handler. This also works for deleted paths, where looking up the current file is no longer possible. A directory with a matching suffix will be classified the same way; suffix routing does not establish the object's type.

`watch_filter=None` deliberately retains all backend changes for dispatch, including temporary-file events. If you add a filter, keep every event your handlers need. Handler calls are synchronous: slow work delays consuming the next batch. If work must run concurrently, hand it to your application's bounded queue and preserve whatever ordering that application needs.

## Download completion is a separate decision

An `added` event can arrive before writing finishes. A removed temporary file can mean a rename, cancellation or other cleanup. Batches are sets, can combine changes, and do not provide chronological ordering or a universal browser-download transaction. The example's `temporary` flag describes the filename only.

Use a completion contract from the producer when available, or an explicitly chosen application policy. Neither the 200 ms debounce nor a period without events proves that a download succeeded. This example retains the final-name and companion-file events so your policy has those inputs; it does not label files as completed downloads.

## Verification

```sh
.venv/bin/python -m unittest -v
```

The three tests check batch routing and run the actual CLI against two temporary directories. The live test independently observes handler output while creating, writing, deleting and recreating a text file; creating an archive; appending to a `.part` file then renaming it; updating a final-name file while removing its companion; renaming a `.crdownload`; and creating an unrelated file. It checks final file contents, continued delivery and a clean stop. Debug output is checked for one backend watcher.

Tested with watchfiles 1.3.0, Python 3.12.4 and the native macOS 14.6 arm64 backend. On that backend, a later write can still be reported as `added`; the live test accepts `added` or `modified` for writes while a separate batch test verifies event types are preserved. Exact grouping and event mapping may differ elsewhere. The live shutdown test uses POSIX SIGINT and is skipped on Windows. These are scripted local file operations, not browser-download tests.

## Optional coffee

This example is free. If it saved you time, an optional coffee is appreciated.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
