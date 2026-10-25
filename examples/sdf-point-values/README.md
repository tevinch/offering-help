# Evaluate an SDF at points after mesh generation

A 3D SDF takes an array with shape `(N, 3)` and returns `(N, 1)`, in the same row order. For one XYZ coordinate, keep the outer pair of brackets:

```python
import numpy as np
from sdf import sphere

f = sphere(3)
value = f(np.array([[0., 0., 0.]]))[0, 0]  # -3.0
```

A flat list, tuple or array has shape `(3,)`. It lacks the row axis and raises `AxisError` for this sphere. Use the public `f(points)` call; accessing `f.f` is unnecessary.

This follows the project's documented [SDF input and output contract](https://github.com/nobodyinperson/sdf#sdf-implementation) and answers [the point-evaluation question](https://github.com/nobodyinperson/sdf/issues/5).

## Run the complete example

Use Python 3.12. From this directory, run these commands on macOS or Linux:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir --index-url https://pypi.org/simple -r requirements.txt
.venv/bin/python example.py
.venv/bin/python -m unittest -v
```

Tested with Python 3.12.4 on macOS arm64.

The distribution is **`sdfcad`**, and its Python import is **`sdf`**. The unrelated PyPI package named `sdf` is not used. Requirements pin `sdfcad==0.5.2` and the scientific packages used for this example. No Jupyter extras are needed.

`example.py` generates a radius-3 sphere mesh, then evaluates the same SDF at arbitrary coordinates, every mesh vertex and every triangle centroid. It prints shapes and a small CSV-style table with point or triangle IDs, XYZ and SDF values. For each mesh set, the table includes its first row and its smallest SDF value. All full arrays remain in the script for further processing:

```python
vertex_values = f(vertices)  # (M, 1), matching the M vertex rows
centroids = vertices.reshape(-1, 3, 3).mean(axis=1)
centroid_values = f(centroids)  # one value per triangle
```

`generate()` returns vertex rows grouped in consecutive triples, rather than a deduplicated vertex list with face indices. Triangle `i` uses rows `3*i` through `3*i+2`; centroid row `i` and distance row `i` refer to that triangle. Shared vertices can therefore appear more than once.

The example uses explicit bounds, step `0.25`, one worker and no sparse skipping. It selects a headless plotting backend, opens no viewer and writes no mesh or result files. Existing output files are left alone.

## Interpret and check the values

For this sphere, the exact signed distance is `sqrt(x*x + y*y + z*z) - 3`: negative inside, zero on the surface, positive outside. The center returns `-3`, `(3, 0, 0)` returns `0`, and `(0, 0, 4)` returns `1`.

Marching-cubes interpolation can leave small nonzero SDF values at mesh vertices. Facet centroids can lie inside the curved surface. Do not replace either array with zeros. These values evaluate the original SDF, rather than measuring distance to the triangulated mesh.

The scripted tests check every returned value against the analytic sphere, correspondence and shapes, unchanged inputs, repeated queries, repeated real mesh generation and continued point queries. They also reproduce the flat-input error. The original downstream postprocessor and Windows environment are not tested. Arbitrary CSG operations or nonuniform scaling are not guaranteed to retain exact Euclidean signed distances.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
