"""Render a plot with the center-right end of each x tick label anchored."""
from copy import deepcopy
from pathlib import Path

import plotnine as pn
import polars as pl


def make_plot(labels=("aaaaa", "bbbbb", "ccccc"), size=(6, 4)):
    data = pl.DataFrame({"x": list(labels), "y": [1] * len(labels)})
    return (
        pn.ggplot(data, pn.aes("x", "y"))
        + pn.geom_point()
        + pn.theme(
            figure_size=size,
            axis_text_x=pn.element_text(
                rotation=45, ha="right", va="center", rotation_mode="anchor"
            ),
        )
    )


def draw_with_anchored_ticks(plot):
    """Return a final-size, single-panel Figure with anchored x tick labels."""
    figure = deepcopy(plot).draw()
    if len(figure.axes) != 1:
        raise ValueError("This recipe is for a single-panel plot.")
    figure.draw_without_rendering()  # Finish plotnine's size/position calculation.
    figure.set_layout_engine("none")  # Keep that layout during subsequent saves.
    for label in figure.axes[0].get_xticklabels():
        label.set(ha="right", va="center", rotation_mode="anchor", y=0)
    return figure


if __name__ == "__main__":
    output = Path("output")
    output.mkdir(exist_ok=True)
    figure = draw_with_anchored_ticks(make_plot())
    for extension in ("png", "svg", "pdf"):
        figure.savefig(output / f"rotated-labels.{extension}")
    print("Saved output/rotated-labels.png, .svg and .pdf")
