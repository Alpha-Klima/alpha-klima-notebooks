"""Part-to-whole charts for portfolio breakdowns.

Both charts here answer a share question, so both are drawn as donuts with the total
in the centre:

- :func:`loss_mix_donut` splits an expected annual loss into its components. Expected
  losses add up, so the shares genuinely sum to the total.
- :func:`cluster_exposure_donut` splits the clustered exposure across clusters, to show
  how concentrated the correlated value is.

A donut is only used where the parts really do make up the whole. Value at Risk is not
additive across hazards or clusters, so it is compared with bars instead and never split
into shares.

Both figures carry a short title and nothing else. The reading, the caveats and any
share of the portfolio belong in the surrounding markdown, not inside the chart.
"""

from __future__ import annotations

import plotly.graph_objects as go

PALETTE = {
    "teal": "#0092A0",
    "orange": "#E15E0B",
    "violet": "#4A3AA7",
    "ink": "#0b0b0b",
    "ink2": "#52514e",
    "surface": "#fcfcfb",
}

# Component hues, checked for colour-vision separation as a set. Flood keeps the teal
# and heat the warm hue in every notebook, so the same component reads the same way.
# Most specific token first: "Flood: vehicles" must resolve as vehicles, not flood.
COMPONENT_FILL = {
    "vehicles": PALETTE["violet"],
    "wind": PALETTE["violet"],
    "heat": PALETTE["orange"],
    "flood": PALETTE["teal"],
}

# Sequential teal, light -> dark, monotonic in lightness; the darkest step takes the
# largest share.
TEAL_RAMP = [
    "#9FD8DE",
    "#6FC4CD",
    "#3FADBA",
    "#1799A8",
    "#00808D",
    "#00646F",
    "#004A53",
]

SURFACE_GAP = 2


def _srgb_to_lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lightness(hex_color: str) -> float:
    """Approximate OKLab lightness, used to pick a label colour that clears contrast."""
    h = hex_color.lstrip("#")
    r, g, b = (_srgb_to_lin(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4))
    lc = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    mc = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    sc = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    lc, mc, sc = lc ** (1 / 3), mc ** (1 / 3), sc ** (1 / 3)
    return 0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc


def _label_ink(fill: str) -> str:
    return "#ffffff" if _lightness(fill) < 0.62 else PALETTE["ink"]


def _sequential(n: int) -> list[str]:
    if n <= 1:
        return [TEAL_RAMP[3]]
    step = (len(TEAL_RAMP) - 1) / (n - 1)
    return [TEAL_RAMP[round(i * step)] for i in range(n)]


def _share_labels(values: list[float], *, min_share: float = 0.06) -> list[str]:
    """Percent labels, blank on slices too thin to hold text.

    A label that will not fit is dropped rather than rotated or clipped. The legend
    names the slice and the tooltip carries the value, so nothing is lost.
    """
    total = sum(values) or 1.0
    return [f"{v / total:.0%}" if v / total >= min_share else "" for v in values]


def component_fill(component: str) -> str:
    """Pick a component colour from its name, e.g. "Flood: vehicles" -> violet."""
    key = component.lower()
    for token, fill in COMPONENT_FILL.items():
        if token in key:
            return fill
    return PALETTE["teal"]


def _donut(
    labels: list[str],
    values: list[float],
    fills: list[str],
    *,
    title: str,
    subtitle: str,
    centre_value: str,
    centre_note: str,
    hover: str,
    height: int,
) -> go.Figure:
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            sort=False,
            direction="clockwise",
            marker=dict(
                colors=fills, line=dict(color=PALETTE["surface"], width=SURFACE_GAP)
            ),
            text=_share_labels(values),
            textinfo="text",
            textposition="inside",
            insidetextorientation="horizontal",
            insidetextfont=dict(color=[_label_ink(c) for c in fills], size=13),
            hovertemplate=hover,
        )
    )
    fig.add_annotation(
        text=(
            f"<span style='font-size:22px;color:{PALETTE['ink']}'><b>{centre_value}</b></span>"
            f"<br><span style='font-size:11px;color:{PALETTE['ink2']}'>{centre_note}</span>"
        ),
        showarrow=False,
        x=0.5,
        y=0.5,
        xanchor="center",
        yanchor="middle",
    )
    fig.update_layout(
        title=dict(
            text=(
                f"<b>{title}</b>"
                + (
                    f"<br><span style='font-size:12px;color:{PALETTE['ink2']}'>{subtitle}</span>"
                    if subtitle
                    else ""
                )
            ),
            font=dict(size=17, color=PALETTE["ink"]),
            x=0.01,
            xanchor="left",
            y=0.95,
        ),
        height=height,
        margin=dict(l=8, r=8, t=72, b=58),
        paper_bgcolor=PALETTE["surface"],
        plot_bgcolor=PALETTE["surface"],
        font=dict(color=PALETTE["ink2"], size=12),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.02,
            xanchor="center",
            x=0.5,
            font=dict(color=PALETTE["ink2"], size=12),
        ),
    )
    return fig


def loss_mix_donut(
    components: dict[str, float],
    *,
    title: str = "Expected annual loss breakdown",
    subtitle: str = "",
    height: int = 400,
) -> go.Figure:
    """Expected annual loss split by component, with the annual total in the centre."""
    labels = list(components)
    values = [float(components[k]) for k in labels]
    fills = [component_fill(k) for k in labels]
    total = sum(values)
    return _donut(
        labels,
        values,
        fills,
        title=title,
        subtitle=subtitle,
        centre_value=f"{total / 1e3:,.0f}k",
        centre_note="EUR/yr total",
        hover="%{label}<br>%{value:,.0f} EUR/yr  (%{percent:.1%})<extra></extra>",
        height=height,
    )


def cluster_exposure_donut(
    cluster_values: dict[str, float],
    *,
    title: str,
    max_slices: int = 6,
    height: int = 400,
) -> go.Figure:
    """Share of clustered exposure per cluster.

    A sequential hue is used rather than one colour per cluster: the reader's job here
    is to see how concentrated the value is, not to tell individual clusters apart.

    The caller supplies the title and explains the reading in surrounding text, so the
    figure carries no commentary of its own.
    """
    items = sorted(cluster_values.items(), key=lambda kv: kv[1], reverse=True)
    if len(items) > max_slices:
        head, tail = items[: max_slices - 1], items[max_slices - 1 :]
        items = head + [("Other clusters", sum(v for _, v in tail))]

    labels = [k for k, _ in items]
    values = [float(v) for _, v in items]
    clustered = sum(values)
    fills = list(reversed(_sequential(len(items))))

    return _donut(
        labels,
        values,
        fills,
        title=title,
        subtitle="",
        centre_value=f"{clustered / 1e6:,.1f}M",
        centre_note="EUR clustered",
        hover="%{label}<br>%{value:,.0f} EUR exposed  (%{percent:.1%} of clustered)<extra></extra>",
        height=height,
    )
