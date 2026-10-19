"""Check a clean PyArrow environment and exercise its file formats."""

import importlib.util
import json
import platform
import sys
import tempfile
from importlib import metadata
from pathlib import Path


if sys.prefix == sys.base_prefix:
    raise SystemExit("Use the Python interpreter inside a fresh virtual environment.")

if importlib.util.find_spec("numpy") is not None:
    raise SystemExit("NumPy is visible: use a fresh venv without --system-site-packages.")

try:
    metadata.distribution("numpy")
except metadata.PackageNotFoundError:
    pass
else:
    raise SystemExit("NumPy package metadata is visible; check this environment's paths.")

import pyarrow as pa
import pyarrow.ipc as ipc
import pyarrow.parquet as pq


if pa.__version__ != "26.0.0":
    raise SystemExit(f"Expected PyArrow 26.0.0, found {pa.__version__}.")

rows = [
    {"id": 1, "name": "café", "value": 1.5, "enabled": True},
    {"id": 2, "name": "上海", "value": None, "enabled": False},
    {"id": 3, "name": None, "value": -2.25, "enabled": None},
]
schema = pa.schema(
    [("id", pa.int64()), ("name", pa.string()), ("value", pa.float64()), ("enabled", pa.bool_())]
)
table = pa.Table.from_pylist(rows, schema=schema)
ipc_roundtrips = 0
parquet_roundtrips = 0

with tempfile.TemporaryDirectory(prefix="arrow-roundtrip-") as directory:
    for number in (1, 2):
        ipc_path = Path(directory) / f"rows-{number}.arrow"
        with ipc.new_file(str(ipc_path), table.schema) as writer:
            writer.write_table(table)
        with ipc.open_file(str(ipc_path)) as reader:
            restored = reader.read_all()
        if not restored.equals(table, check_metadata=True) or restored.to_pylist() != rows:
            raise SystemExit(f"IPC round trip {number} changed the data or schema.")
        ipc_roundtrips += 1

        parquet_path = Path(directory) / f"rows-{number}.parquet"
        pq.write_table(restored, str(parquet_path), compression="NONE")
        table = pq.read_table(str(parquet_path))
        if not table.equals(restored, check_metadata=True) or table.to_pylist() != rows:
            raise SystemExit(f"Parquet round trip {number} changed the data or schema.")
        parquet_roundtrips += 1

if (ipc_roundtrips, parquet_roundtrips) != (2, 2):
    raise SystemExit("Both file formats must complete two round trips.")
if "numpy" in sys.modules:
    raise SystemExit("The data operations loaded NumPy unexpectedly.")

print(json.dumps({
    "status": "ok",
    "python": platform.python_version(),
    "pyarrow": pa.__version__,
    "numpy": None,
    "ipc_roundtrips": ipc_roundtrips,
    "parquet_roundtrips": parquet_roundtrips,
    "rows": len(rows),
}, sort_keys=True))
