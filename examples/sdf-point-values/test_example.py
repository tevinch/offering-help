"""Run the complete example and check its point-to-value correspondence."""
import contextlib
import io
import math
from pathlib import Path
import runpy
import unittest

import numpy as np
from numpy.exceptions import AxisError


class ExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name("example.py")
        assert path.is_file(), "The runnable example is missing"
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cls.result = runpy.run_path(str(path))
        cls.output = output.getvalue()

    def assert_distances(self, points, values):
        self.assertEqual(values.shape, (len(points), 1))
        self.assertTrue(np.isfinite(values).all())
        expected = [[math.sqrt(x*x + y*y + z*z) - 3] for x, y, z in points]
        np.testing.assert_allclose(values, expected, rtol=0, atol=1e-12)

    def test_single_and_arbitrary_points(self):
        r = self.result
        self.assertEqual(r["point"].shape, (1, 3))
        self.assertEqual(r["value"], -3.0)
        np.testing.assert_array_equal(r["query_points"], [
            [0, 0, 0], [3, 0, 0], [0, 1.5, 0], [0, 0, 4], [-1.25, 2.5, -0.5]
        ])
        self.assert_distances(r["query_points"], r["query_values"])

    def test_real_mesh_vertices_and_centroids(self):
        r = self.result
        vertices = r["vertices"]
        self.assertEqual(vertices.ndim, 2)
        self.assertEqual(vertices.shape[1], 3)
        self.assertGreater(len(vertices), 3)
        self.assertEqual(len(vertices) % 3, 0)
        self.assertTrue(np.isfinite(vertices).all())
        # Bounds and surface proximity reject dummy geometry for this radius-3 mesh.
        np.testing.assert_allclose(vertices.min(axis=0), [-3, -3, -3], atol=0.02)
        np.testing.assert_allclose(vertices.max(axis=0), [3, 3, 3], atol=0.02)
        self.assert_distances(vertices, r["vertex_values"])
        self.assertLess(np.max(np.abs(r["vertex_values"])), 0.02)
        centroids = vertices.reshape(-1, 3, 3).mean(axis=1)
        np.testing.assert_array_equal(r["centroids"], centroids)
        self.assert_distances(centroids, r["centroid_values"])
        # The facets are planar; their centers are slightly inside the sphere.
        self.assertTrue(np.any(r["centroid_values"] < -0.001))

    def test_repeated_queries_preserve_inputs_and_still_work(self):
        r = self.result
        for point_name, value_name in [
            ("query_points", "query_values"), ("vertices", "vertex_values"),
            ("centroids", "centroid_values"), ("fresh_points", "fresh_values")
        ]:
            points = r[point_name]
            before = points.tobytes()
            for _ in range(2):
                values = r["f"](points)
                self.assertEqual(points.tobytes(), before)
                self.assert_distances(points, values)
                np.testing.assert_array_equal(values, r[value_name])
        np.testing.assert_array_equal(r["fresh_points"], [[0, 0, 0], [-4, 0, 0]])
        np.testing.assert_array_equal(r["fresh_values"], [[-3], [1]])

    def test_repeated_generation_then_point_query(self):
        r = self.result
        before = r["vertices"].tobytes()
        vertices = np.asarray(r["f"].generate(
            step=0.25, bounds=((-3.5, -3.5, -3.5), (3.5, 3.5, 3.5)),
            workers=1, sparse=False, verbose=False,
        ))
        self.assertEqual(r["vertices"].tobytes(), before)
        np.testing.assert_array_equal(vertices, r["vertices"])
        self.assert_distances(vertices, r["f"](vertices))
        self.assertEqual(r["f"](np.array([[0., 0., 4.]]))[0, 0], 1)

    def test_printed_mesh_rows_keep_ids_and_show_nonzero_residuals(self):
        seen_nonzero = set()
        for line in self.output.splitlines():
            fields = line.split(',')
            if fields[0] not in ('vertex', 'triangle_centroid'):
                continue
            kind, index = fields[0], int(fields[1])
            name = 'vertices' if kind == 'vertex' else 'centroids'
            value_name = 'vertex_values' if kind == 'vertex' else 'centroid_values'
            np.testing.assert_allclose([float(x) for x in fields[2:5]],
                                       self.result[name][index], rtol=0, atol=0.00000051)
            self.assertAlmostEqual(float(fields[5]), self.result[value_name][index, 0], places=8)
            if abs(float(fields[5])) > 0.000001:
                seen_nonzero.add(kind)
        self.assertEqual(seen_nonzero, {'vertex', 'triangle_centroid'})

    def test_one_dimensional_inputs_explain_original_error(self):
        for point in ([0., 0., 0.], (0., 0., 0.), np.array([0., 0., 0.])):
            with self.subTest(kind=type(point).__name__), self.assertRaises(AxisError):
                self.result["f"](point)


if __name__ == "__main__":
    unittest.main()
