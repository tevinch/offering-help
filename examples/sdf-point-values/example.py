"""Evaluate a radius-3 sphere at arbitrary points and on its generated mesh."""
import matplotlib
matplotlib.use("Agg")  # Headless, even when sdf imports pyplot.

import numpy as np
from sdf import sphere

f = sphere(3)
vertices = np.asarray(f.generate(
    step=0.25,
    bounds=((-3.5, -3.5, -3.5), (3.5, 3.5, 3.5)),
    workers=1,
    sparse=False,
    verbose=False,
), dtype=float)

# A single coordinate is still a batch with one row: (1, 3).
point = np.array([[0., 0., 0.]])
value = f(point)[0, 0]

# Each input row has a corresponding output row: (N, 3) -> (N, 1).
query_points = np.array([
    [0., 0., 0.], [3., 0., 0.], [0., 1.5, 0.],
    [0., 0., 4.], [-1.25, 2.5, -0.5],
])
query_values = f(query_points)

# generate() returns consecutive triples of vertices, one triple per triangle.
vertex_values = f(vertices)
centroids = vertices.reshape(-1, 3, 3).mean(axis=1)
centroid_values = f(centroids)

# The same SDF remains callable after generation and mesh evaluations.
fresh_points = np.array([[0., 0., 0.], [-4., 0., 0.]])
fresh_values = f(fresh_points)

print(f"Single point: {value:g}")
print(f"Mesh: {len(vertices)} vertex rows, {len(centroids)} triangles")
print(f"Shapes: vertices {vertices.shape}, values {vertex_values.shape}; "
      f"centroids {centroids.shape}, values {centroid_values.shape}")
print("kind,id,x,y,z,sdf")
for kind, points, values in (
    ("query", query_points, query_values),
    ("vertex", vertices, vertex_values),
    ("triangle_centroid", centroids, centroid_values),
):
    # Include a nonzero interpolation residual, with its original row ID.
    indices = range(len(points)) if kind == "query" else [0, int(np.argmin(values[:, 0]))]
    for index in indices:
        x, y, z = points[index]
        distance = values[index, 0]
        print(f"{kind},{index},{x:.6f},{y:.6f},{z:.6f},{distance:.9f}")
print("Fresh queries:", fresh_values[:, 0].tolist())
