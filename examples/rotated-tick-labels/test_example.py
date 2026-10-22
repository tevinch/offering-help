"""Rendered geometry and saved-file acceptance checks for the example."""
from copy import deepcopy
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import matplotlib as mpl
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.text import Text
from PIL import Image
import plotnine as pn

from example import draw_with_anchored_ticks, make_plot


def rendered_rows(figure):
    FigureCanvasAgg(figure)
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    rows = []
    for ax in figure.axes:
        for label in ax.get_xticklabels():
            if not label.get_visible() or not label.get_text():
                continue
            # The unrotated reference supplies actual font height. Recover the
            # rotated rectangle's right-edge midpoint from its bounding box.
            reference = Text(text=label.get_text(), fontproperties=label.get_fontproperties())
            reference.set_figure(figure)
            height = reference.get_window_extent(renderer).height
            box = label.get_window_extent(renderer)
            angle = math.radians(label.get_rotation())
            endpoint = (box.x1 - height * math.sin(angle) / 2,
                        box.y1 - height * math.cos(angle) / 2)
            tick = ax.get_xaxis_transform().transform((label.get_position()[0], 0))
            rows.append((label, endpoint, tick, box))
    return rows


class RenderedLabels(unittest.TestCase):
    def assert_anchored(self, figure, expected_count=3):
        rows = rendered_rows(figure)
        self.assertEqual(len(rows), expected_count)
        for label, endpoint, tick, box in rows:
            self.assertAlmostEqual(endpoint[0], tick[0], delta=0.1, msg=label.get_text())
            # The configured tick length + text margin is kept by the existing
            # label transform. Verify physical distance, independent of y=0.
            ax = label.axes or figure.axes[0]
            actual_tick = next(t for t in ax.xaxis.get_major_ticks() if t.label1 is label)
            expected_gap = (actual_tick.get_pad() + actual_tick.get_tick_padding()) * figure.dpi / 72
            self.assertAlmostEqual(tick[1] - endpoint[1], expected_gap, delta=0.1)
            self.assertGreaterEqual(box.x0, 0)
            self.assertGreaterEqual(box.y0, 0)
            self.assertLessEqual(box.x1, figure.bbox.x1)
            self.assertLessEqual(box.y1, figure.bbox.y1)
        # The title remains below all tick labels, rather than overlapping them.
        title = next(text for text in figure.texts if text.get_text() == "x")
        self.assertLess(title.get_window_extent().y1, min(row[3].y0 for row in rows))
        return [(label.get_text(), tuple(endpoint), tuple(tick)) for label, endpoint, tick, _ in rows]

    def test_original_workflow_and_repeat_draw(self):
        plot = make_plot()
        figure = draw_with_anchored_ticks(plot)
        first = self.assert_anchored(figure)
        self.assertEqual(first, self.assert_anchored(figure))
        self.assertEqual([row[0] for row in first], ["aaaaa", "bbbbb", "ccccc"])
        self.assertEqual(figure.axes[0].collections[0].get_offsets().tolist(), [[1, 1], [2, 1], [3, 1]])

    def test_input_theme_data_and_other_text_are_preserved(self):
        plot = make_plot() + pn.labs(title="Sample counts", subtitle="Three groups", caption="Example data")
        plot += pn.theme(axis_text_y=pn.element_text(color="#143d59"), panel_background=pn.element_rect(fill="#f2f5f7"))
        data_before = plot.data.clone() if hasattr(plot.data, 'clone') else plot.data.copy(deep=True)
        theme_before = repr(plot.theme.themeables)
        baseline = deepcopy(plot).draw()
        rendered_rows(baseline)
        y_before = [(t.get_text(), t.get_color(), t.get_fontsize(), t.get_rotation()) for t in baseline.axes[0].get_yticklabels()]
        figure = draw_with_anchored_ticks(plot)
        self.assert_anchored(figure)
        self.assertEqual(y_before, [(t.get_text(), t.get_color(), t.get_fontsize(), t.get_rotation()) for t in figure.axes[0].get_yticklabels()])
        self.assertEqual({t.get_text() for t in baseline.texts}, {t.get_text() for t in figure.texts})
        self.assertEqual(baseline.axes[0].get_facecolor(), figure.axes[0].get_facecolor())
        self.assertEqual(theme_before, repr(plot.theme.themeables))
        self.assertTrue(plot.data.equals(data_before))

    def test_saved_files_and_fresh_renders(self):
        with tempfile.TemporaryDirectory() as directory, mpl.rc_context({"svg.fonttype": "none"}):
            plot = make_plot(size=(7, 4))
            figure = draw_with_anchored_ticks(plot)
            before = self.assert_anchored(figure)
            for suffix in ("png", "svg", "pdf", "png"):
                path = Path(directory) / f"chart.{suffix}"
                figure.savefig(path)
                self.assertGreater(path.stat().st_size, 1000)
                self.assertEqual(before, self.assert_anchored(figure))
            with Image.open(Path(directory) / "chart.png") as image:
                self.assertEqual(image.size, (700, 400))
            svg = ET.parse(Path(directory) / "chart.svg").getroot()
            texts = ["".join(node.itertext()) for node in svg.iter('{http://www.w3.org/2000/svg}text')]
            self.assertTrue({"aaaaa", "bbbbb", "ccccc", "x", "y"}.issubset(texts))
            self.assertTrue((Path(directory) / "chart.pdf").read_bytes().startswith(b'%PDF-'))
            self.assertEqual(before, self.assert_anchored(draw_with_anchored_ticks(plot)))

    def test_unequal_labels_and_final_sizes(self):
        for size in ((6, 4), (9, 5)):
            with self.subTest(size=size):
                figure = draw_with_anchored_ticks(make_plot(("a", "Longer label", "middle"), size))
                self.assert_anchored(figure)

    def test_font_spacing_and_small_final_size(self):
        plot = make_plot(size=(3, 2)) + pn.theme(
            axis_text_x=pn.element_text(size=9, color="#345678", margin={"t": 8, "units": "pt"})
        )
        figure = draw_with_anchored_ticks(plot)
        self.assert_anchored(figure)
        self.assertTrue(all(t.get_fontsize() == 9 and t.get_color() == "#345678" for t in figure.axes[0].get_xticklabels()))

    def test_refuses_multiple_panels(self):
        with self.assertRaisesRegex(ValueError, "single-panel"):
            draw_with_anchored_ticks(make_plot() + pn.facet_wrap("x"))

    def test_omitting_layout_freeze_or_y_reset_fails_acceptance(self):
        for missing in ("freeze", "y reset"):
            with self.subTest(missing=missing):
                figure = make_plot().draw()
                figure.draw_without_rendering()
                if missing != "freeze":
                    figure.set_layout_engine("none")
                for label in figure.axes[0].get_xticklabels():
                    label.set(ha="right", va="center", rotation_mode="anchor")
                    if missing != "y reset":
                        label.set_y(0)
                with self.assertRaises(AssertionError):
                    self.assert_anchored(figure)

    def test_omitting_adjustment_fails_rendered_acceptance(self):
        with self.assertRaises(AssertionError):
            self.assert_anchored(make_plot().draw())


if __name__ == "__main__":
    unittest.main()
