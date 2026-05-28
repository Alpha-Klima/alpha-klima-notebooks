"""Plotting helpers for Physrisk exceedance curves and financial metrics.

The functions in this module are intentionally lightweight wrappers around the
API response structures used in the notebooks. They normalize response payloads
into chart-friendly shapes and apply a consistent Plotly visual style.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import plotly.graph_objects as go


# Scenario aliases share colors so equivalent transition pathways are displayed
# consistently across exceedance curves, VaR, and ES charts.
LIGHT_COLORS = {
    "historical": "hsl(210, 60%, 45%)",
    "optimistic": "hsl(160, 55%, 40%)",
    "rcp2p6": "hsl(160, 55%, 40%)",
    "rcp2.6": "hsl(160, 55%, 40%)",
    "ssp119": "hsl(160, 55%, 40%)",
    "ssp126": "hsl(160, 55%, 40%)",
    "moderate": "hsl(45, 85%, 48%)",
    "rcp4p5": "hsl(45, 85%, 48%)",
    "rcp4.5": "hsl(45, 85%, 48%)",
    "ssp245": "hsl(45, 85%, 48%)",
    "ssp370": "hsl(28, 80%, 50%)",
    "pessimistic": "hsl(8, 75%, 50%)",
    "rcp8p5": "hsl(8, 75%, 50%)",
    "rcp8.5": "hsl(8, 75%, 50%)",
    "ssp585": "hsl(8, 75%, 50%)",
}

DARK_COLORS = {
    "historical": "hsl(210, 70%, 65%)",
    "optimistic": "hsl(160, 60%, 55%)",
    "rcp2p6": "hsl(160, 60%, 55%)",
    "rcp2.6": "hsl(160, 60%, 55%)",
    "ssp119": "hsl(160, 60%, 55%)",
    "ssp126": "hsl(160, 60%, 55%)",
    "moderate": "hsl(45, 90%, 60%)",
    "rcp4p5": "hsl(45, 90%, 60%)",
    "rcp4.5": "hsl(45, 90%, 60%)",
    "ssp245": "hsl(45, 90%, 60%)",
    "ssp370": "hsl(28, 85%, 60%)",
    "pessimistic": "hsl(8, 80%, 62%)",
    "rcp8p5": "hsl(8, 80%, 62%)",
    "rcp8.5": "hsl(8, 80%, 62%)",
    "ssp585": "hsl(8, 80%, 62%)",
}

SCENARIO_ORDER = [
    "historical",
    "optimistic",
    "rcp2p6",
    "rcp2.6",
    "ssp119",
    "ssp126",
    "moderate",
    "rcp4p5",
    "rcp4.5",
    "ssp245",
    "ssp370",
    "pessimistic",
    "rcp8p5",
    "rcp8.5",
    "ssp585",
]

TERM_ORDER = ["historical", "short", "st", "middle", "long", "lt"]

SCENARIO_ORDER_INDEX = {scenario: index for index, scenario in enumerate(SCENARIO_ORDER)}
TERM_ORDER_INDEX = {term: index for index, term in enumerate(TERM_ORDER)}

SCENARIO_LABELS = {
    "historical": "Historical",
    "orderly": "Orderly",
    "disorderly": "Disorderly",
    "hot-house world": "Hot-House World",
    "optimistic": "Orderly",
    "moderate": "Disorderly",
    "pessimistic": "Hot-House World",
    "rcp2p6": "RCP 2.6",
    "rcp2.6": "RCP 2.6",
    "rcp4p5": "RCP 4.5",
    "rcp4.5": "RCP 4.5",
    "rcp8p5": "RCP 8.5",
    "rcp8.5": "RCP 8.5",
    "ssp119": "SSP1 1.9",
    "ssp126": "SSP1 2.6",
    "ssp245": "SSP2 4.5",
    "ssp370": "SSP3 7.0",
    "ssp585": "SSP5 8.5",
}

TERM_LABELS = {
    "historical": "Historical",
    "ST": "Short",
    "LT": "Long",
    "short": "Short-Term",
    "middle": "Middle-Term",
    "long": "Long-Term",
    "shortterm": "Short",
    "longterm": "Long",
}

DEFAULT_SCENARIO_COLOR = "hsl(220, 13%, 52%)"


def plot_exceedance_curves(
    response: Mapping[str, Any],
    *,
    name: str = "Cluster/Portfolio",
    selected_term: str | None = None,
    dark: bool = False,
) -> go.Figure:
    """Create a Plotly line chart from an exceedance-curve API response.

    Parameters
    ----------
    response:
        API response containing an ``exceedance_curves`` list.
    name:
        Label used in the chart title, usually the cluster or portfolio name.
    selected_term:
        Optional term filter. When omitted, the first display term is selected.
    dark:
        Whether to use the dark color palette and chart background.

    Returns
    -------
    go.Figure
        Plotly figure with one line per available scenario.
    """

    curves = response.get("exceedance_curves", [])
    term = selected_term or first_display_term(curves)
    chart_data = transform_exceedance_curves(curves, term=term)
    scenario_config = build_scenario_config(
        available_scenarios(curves, term=term), dark=dark
    )
    probabilities = [point["probability"] for point in chart_data]

    fig = go.Figure()
    for scenario, config in scenario_config.items():
        y_values = [point.get(scenario) for point in chart_data]
        if all(value is None for value in y_values):
            continue

        fig.add_trace(
            go.Scatter(
                x=probabilities,
                y=y_values,
                mode="lines+markers",
                name=config["label"],
                connectgaps=True,
                line={"color": config["color"], "width": 2},
                marker={"color": config["color"], "size": 6},
                hovertemplate=(
                    "Exceedance Probability: %{x:.2%}<br>"
                    f"{config['label']}: %{{y:,.0f}} EUR<extra></extra>"
                ),
            )
        )

    title_term = f" ({format_term_label(term)})" if term else ""
    apply_common_layout(
        fig,
        title=f"{name} - Exceedance Curve{title_term}",
        xaxis_title="Exceedance Probability",
        yaxis_title="Loss [EUR]",
        dark=dark,
        xaxis_extra={"tickformat": ".1%", "autorange": "reversed"},
    )
    return fig


def filter_curves(
    curves: Sequence[Mapping[str, Any]],
    *,
    term: str | None = None,
) -> list[Mapping[str, Any]]:
    """Filter curves by term while retaining the historical baseline.

    Historical observations are kept even when a future term is selected so the
    plotted scenario set always has a baseline for comparison.
    """

    result = []
    normalized_term = term.lower() if term else None

    for curve in curves:
        curve_term = str(curve.get("term") or "")
        normalized_curve_term = curve_term.lower()
        scenario = scenario_key(curve)
        is_historical = normalized_curve_term == "historical" or scenario == "historical"
        term_matches = True

        if normalized_term:
            term_matches = normalized_curve_term == normalized_term or is_historical
        if term_matches:
            result.append(curve)

    return result


def transform_exceedance_curves(
    curves: Sequence[Mapping[str, Any]],
    *,
    term: str | None = None,
) -> list[dict[str, float | None]]:
    """Convert nested exceedance curves into chart rows.

    The returned list is keyed by exceedance probability, with one column per
    scenario. Missing values are represented as ``None`` so Plotly can connect
    or skip gaps according to the trace configuration.
    """

    filtered = filter_curves(curves, term=term)
    if not filtered:
        return []

    probability_key_to_value: dict[str, float] = {}
    curve_probability_maps: list[dict[str, float]] = []

    for curve in filtered:
        probability_map: dict[str, float] = {}
        exceedance_curve = curve.get("exceedance_curve", {})
        values = exceedance_curve.get("values", [])
        probabilities = exceedance_curve.get("probabilities", [])

        for index, probability in enumerate(probabilities):
            if probability is None or index >= len(values) or values[index] is None:
                continue

            key = normalize_probability_key(float(probability))
            value = float(values[index])
            probability_key_to_value[key] = float(key)
            probability_map[key] = value

        curve_probability_maps.append(probability_map)

    probabilities_sorted = sorted(probability_key_to_value.values(), reverse=True)
    rows: list[dict[str, float | None]] = []

    for probability in probabilities_sorted:
        key = normalize_probability_key(probability)
        row: dict[str, float | None] = {"probability": probability}
        for curve, probability_map in zip(filtered, curve_probability_maps, strict=True):
            scenario = scenario_key(curve)
            if scenario:
                row[scenario] = probability_map.get(key)
        rows.append(row)

    return rows


def plot_var(
    response: Mapping[str, Any],
    *,
    name: str = "Cluster/Portfolio",
    selected_term: str | None = None,
    dark: bool = False,
) -> go.Figure:
    """Create a Plotly bar chart from a Value-at-Risk API response.

    The function accepts either cluster-level or portfolio-level metric payloads
    and preserves the original response shape expected by the notebook.
    """

    curves = metric_curves(response)
    term = selected_term or first_display_term(curves)
    chart_data = transform_var(curves, term=term)
    scenario_config = build_scenario_config(
        available_scenarios(curves, term=term), dark=dark
    )

    fig = go.Figure()
    add_metric_bars(fig, chart_data, scenario_config)

    title_term = f" ({format_term_label(term)})" if term else ""
    apply_common_layout(
        fig,
        title=f"{name} - Value at Risk{title_term}",
        xaxis_title="Percentile",
        yaxis_title="Value at Risk [EUR]",
        dark=dark,
        xaxis_extra={"tickformat": ".1%"},
    )
    return fig


def transform_var(
    curves: Sequence[Mapping[str, Any]],
    *,
    term: str | None = None,
) -> dict[str, dict[str, list]]:
    """Group VaR metrics by scenario for bar-chart plotting.

    Returns the same nested structure used by ``plot_var``:
    ``{scenario: {"percentiles": [...], "values": [...]}}``.
    """

    filtered = filter_curves(curves, term=term)
    if not filtered:
        return []

    rows = defaultdict(lambda: defaultdict(list))
    for curve in filtered:
        if curve["metric"] == "VaR [€]":
            scenario = scenario_key(curve)
            rows[scenario]["percentiles"].append(curve["percentile"])
            rows[scenario]["values"].append(curve["value"])

    return rows


def plot_es(
    response: Mapping[str, Any],
    *,
    name: str = "Cluster/Portfolio",
    selected_term: str | None = None,
    dark: bool = False,
) -> go.Figure:
    """Create a Plotly bar chart from an Expected Shortfall API response.

    The input handling mirrors ``plot_var`` so cluster and portfolio metric
    payloads can be passed directly from the notebook.
    """

    curves = metric_curves(response)
    term = selected_term or first_display_term(curves)
    chart_data = transform_es(curves, term=term)
    scenario_config = build_scenario_config(
        available_scenarios(curves, term=term), dark=dark
    )

    fig = go.Figure()
    add_metric_bars(fig, chart_data, scenario_config)

    title_term = f" ({format_term_label(term)})" if term else ""
    apply_common_layout(
        fig,
        title=f"{name} - Expected Shortfall{title_term}",
        xaxis_title="Percentile",
        yaxis_title="Expected Shortfall [EUR]",
        dark=dark,
        xaxis_extra={"tickformat": ".1%"},
    )
    return fig


def transform_es(
    curves: Sequence[Mapping[str, Any]],
    *,
    term: str | None = None,
) -> dict[str, dict[str, list]]:
    """Group ES metrics by scenario for bar-chart plotting.

    This preserves the original metric-selection behavior used by the notebook
    while organizing the response into the same nested structure as VaR.
    """

    filtered = filter_curves(curves, term=term)
    if not filtered:
        return []

    rows = defaultdict(lambda: defaultdict(list))
    for curve in filtered:
        if curve["metric"] == "VaR [€]":
            scenario = scenario_key(curve)
            rows[scenario]["percentiles"].append(curve["percentile"])
            rows[scenario]["values"].append(curve["value"])

    return rows


def available_scenarios(
    curves: Sequence[Mapping[str, Any]],
    *,
    term: str | None = None,
) -> list[str]:
    """Return unique scenarios from filtered curves in display order."""

    scenarios = set()
    for curve in filter_curves(curves, term=term):
        scenario = scenario_key(curve)
        if scenario:
            scenarios.add(scenario)

    return sorted(scenarios, key=scenario_sort_key)


def available_terms(curves: Sequence[Mapping[str, Any]]) -> list[str]:
    """Return unique terms in the same order used by the chart UI."""

    terms = {str(curve.get("term") or "") for curve in curves if curve.get("term")}
    return sorted(terms, key=term_sort_key)


def first_display_term(lists: Sequence[Mapping[str, Any]]) -> str | None:
    """Pick the first non-historical term, falling back to historical."""

    terms = available_terms(lists)
    for term in terms:
        if term.lower() != "historical":
            return term
    return terms[0] if terms else None


def build_scenario_config(
    scenarios: Sequence[str], *, dark: bool = False
) -> dict[str, dict[str, str]]:
    """Build scenario labels and colors for Plotly traces."""

    color_map = DARK_COLORS if dark else LIGHT_COLORS
    sorted_scenarios = sorted(scenarios, key=scenario_sort_key)
    return {
        scenario.lower(): {
            "label": format_scenario_label(scenario),
            "color": color_map.get(scenario.lower(), DEFAULT_SCENARIO_COLOR),
        }
        for scenario in sorted_scenarios
    }


def metric_curves(response: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    """Return cluster-level metrics, falling back to portfolio-level metrics."""

    curves = response.get("cluster_level_metrics", [])
    if not curves:
        curves = response.get("portfolio_level_metrics", [])
    return curves


def add_metric_bars(
    fig: go.Figure,
    chart_data: Mapping[str, Mapping[str, list]],
    scenario_config: Mapping[str, Mapping[str, str]],
) -> None:
    """Add one percentile bar trace per configured scenario."""

    for scenario, config in scenario_config.items():
        x_list: list = chart_data.get(scenario).get("percentiles")
        y_list: list = chart_data.get(scenario).get("values")

        fig.add_trace(
            go.Bar(
                x=[format_percentile(percentile) for percentile in x_list],
                y=y_list,
                name=config["label"],
                marker_color=config["color"],
                marker_line_width=0,
                marker_cornerradius=5,
                width=0.15,
                hovertemplate=f"{config['label']}: %{{y:,.0f}} EUR<extra></extra>",
            )
        )


def apply_common_layout(
    fig: go.Figure,
    *,
    title: str,
    xaxis_title: str,
    yaxis_title: str,
    dark: bool,
    xaxis_extra: Mapping[str, Any] | None = None,
) -> None:
    """Apply the shared chart layout used by all plotting functions."""

    xaxis = {
        "showgrid": True,
        "gridcolor": grid_color(dark),
        "zerolinecolor": grid_color(dark),
    }
    if xaxis_extra:
        xaxis.update(xaxis_extra)

    fig.update_layout(
        title=dict(text=title, font={"color": font_color(dark)}),
        xaxis_title=xaxis_title,
        xaxis_title_font=dict(color=font_color(dark)),
        xaxis_tickfont=dict(color=font_color(dark)),
        yaxis_title=yaxis_title,
        yaxis_title_font=dict(color=font_color(dark)),
        yaxis_tickfont=dict(color=font_color(dark)),
        xaxis=xaxis,
        yaxis={
            "showgrid": True,
            "gridcolor": grid_color(dark),
            "zerolinecolor": grid_color(dark),
            "rangemode": "nonnegative",
        },
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
            "font": {"color": font_color(dark)},
        },
        hovermode="x unified",
        height=400,
        margin={"t": 70, "r": 30, "l": 70, "b": 60},
        plot_bgcolor=plot_color(dark),
        paper_bgcolor=paper_color(dark),
    )


def scenario_key(curve: Mapping[str, Any]) -> str:
    """Return the normalized scenario name from an API curve object."""

    return str(curve.get("scenario_name") or curve.get("scenario") or "").lower()


def normalize_probability_key(probability: float) -> str:
    """Normalize floating-point probabilities for dictionary joins."""

    return f"{probability:.6f}"


def scenario_sort_key(scenario: str) -> tuple[int, str]:
    """Sort known scenarios by configured order, unknown scenarios last."""

    normalized = scenario.lower()
    return (SCENARIO_ORDER_INDEX.get(normalized, 999), normalized)


def term_sort_key(term: str) -> tuple[int, str]:
    """Sort known terms by configured order, unknown terms last."""

    normalized = term.lower()
    return (TERM_ORDER_INDEX.get(normalized, 999), normalized)


def format_scenario_label(scenario: str) -> str:
    """Return a display label for a scenario key."""

    normalized = scenario.lower()
    return SCENARIO_LABELS.get(normalized, scenario[:1].upper() + scenario[1:])


def format_term_label(term: str | None) -> str:
    """Return a display label for a time-horizon term."""

    if not term:
        return ""
    return TERM_LABELS.get(term, TERM_LABELS.get(term.lower(), term))


def format_percentile(percentile: float) -> str:
    """Format percentile values as labels such as ``P95`` or ``P99.5``."""

    return f"P{percentile:.0f}" if percentile.is_integer() else f"P{percentile:.1f}"


def grid_color(dark: bool) -> str:
    """Return the grid line color for the selected theme."""

    return "rgba(255, 255, 255, 0.2)" if dark else "rgba(0, 0, 0, 0.2)"


def paper_color(dark: bool) -> str:
    """Return the Plotly paper background color for the selected theme."""

    return "#1C1D22" if dark else "#F7F7F7"


def plot_color(dark: bool) -> str:
    """Return the plotting area background color for the selected theme."""

    return "#131417" if dark else "#FFFFFF"


def font_color(dark: bool) -> str:
    """Return the text color for the selected theme."""

    return "hsl(210, 10%, 80%)" if dark else "hsl(210, 10%, 40%)"
