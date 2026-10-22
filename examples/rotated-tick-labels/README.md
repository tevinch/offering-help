# Anchor rotated plotnine tick labels

Place the center-right end of each 45° x-axis label directly below its tick. This example keeps the plot data, theme, font, text color, tick spacing and axis titles, and saves the result as PNG, SVG and PDF.

In plotnine 0.15.8, `axis_text_x=element_text(va="center")` controls vertical justification within the tick-label row. It does not pass `va="center"` directly to each Matplotlib text artist. As a result, adding `rotation_mode="anchor"` to that theme setting can still leave the rotated labels too far left or below their ticks. The [versioned theme implementation](https://github.com/has2k1/plotnine/blob/v0.15.8/plotnine/themes/themeable.py) and [label positioning](https://github.com/has2k1/plotnine/blob/v0.15.8/plotnine/_mpl/layout_manager/_layout_items.py) show those two stages.

For a final-size, single-panel export, finish plotnine's layout first, then use the returned Figure's public text settings:

```python
from copy import deepcopy

fig = deepcopy(plot).draw()
fig.draw_without_rendering()
fig.set_layout_engine("none")

for label in fig.axes[0].get_xticklabels():
    label.set(ha="right", va="center", rotation_mode="anchor", y=0)

fig.savefig("chart.png")
```

Keep the 45° rotation in your `axis_text_x` theme. `y=0` restores the bottom-axis baseline; the existing text transform still supplies the configured tick length and text margin. `deepcopy` leaves your plot available for a fresh render. Use `fig.savefig(...)` after the adjustment: a new plotnine render recalculates label positions.

## Run the example

Use Python 3.12 and a fresh environment in this directory:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python example.py
python -m unittest -v
```

On Windows, activate with `.venv\Scripts\activate` instead. The script writes `output/rotated-labels.png`, `.svg` and `.pdf`. `make_plot()` includes the three-category Polars input; PyArrow is included because plotnine converts that input to pandas.

To apply it to your own plot, finish setting its size, fonts, labels and theme first:

```python
from example import draw_with_anchored_ticks

fig = draw_with_anchored_ticks(plot)
fig.savefig("chart.svg")
```

This is a small export recipe. It freezes layout on that Figure, so changing its size or adding text afterwards does not trigger layout recalculation. Change the original plot and call `draw_with_anchored_ticks` again for another size. The example checks for a single panel; facets, polar axes, multiline tick labels, and interactive resizing are outside its tested scope. Keep sufficient space for long labels, as with any static plot.

## Verification

Tested with plotnine 0.15.8, Matplotlib 3.11.2, Polars 2.0.0, PyArrow 26.0.0 and Python 3.12.4. The full tested dependency set is pinned in `requirements.txt`.

The scripted checks measure the rendered label endpoints against the tick positions, retain the configured physical gap, check image bounds and title separation, and verify the point data and other text remain intact. They cover unequal label lengths, final sizes, a custom font/color/margin, repeated draws, fresh renders, and repeated PNG/SVG/PDF saves. The original theme-only result fails the geometric check; omitting either the layout freeze or the baseline reset also fails. These checks do not establish adoption in another application.

Pandas 3.1.0 emits `Pandas4Warning` deprecation notices from plotnine's `reset_index(inplace=...)` calls with this dependency set. The render/export checks still pass.

References: [plotnine `element_text`](https://plotnine.org/reference/element_text.html), [plotnine `draw`](https://plotnine.org/reference/ggplot.html#draw), [Matplotlib rotation modes](https://matplotlib.org/stable/gallery/text_labels_and_annotations/demo_text_rotation_mode.html), [Figure layout engines](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.set_layout_engine.html), and the [original usage question](https://github.com/has2k1/plotnine/issues/1141).

MIT licensed; see [LICENSE](LICENSE).

## Optional coffee

The example is free. If it helps and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
