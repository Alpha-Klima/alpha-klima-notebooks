"""TEMPORARY: client-side VaR / Expected Shortfall, to be replaced by the platform API.

This module previews midway endpoints that will expose these tail metrics directly. It exists only so
the demo notebooks can price the tail today; delete it once those endpoints land and call the API
instead.

The math mirrors Alpha-Klima's financial module, so the numbers here match what the endpoint will
return. Any change to this module must keep that parity.

Input is the ``impact_distribution`` the asset impact endpoint already returns per asset: bin edges
(length ``N + 1``) and bin probabilities (length ``N``). Bins are half-open ``(lower, upper]`` and the
probabilities need not sum to one: the deficit ``1 - sum(probabilities)`` is the zero-impact mass.
"""

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

VAR_METRIC = "VaR [€]"
ES_METRIC = "ES [€]"

DEFAULT_PERCENTILES = (95.0, 99.0, 99.5)


def _check_percentile(percentile: float) -> float:
    "Validate the 0 to 100 percentile convention used by the reference implementation."

    if not 0 < percentile < 100:
        raise ValueError("Percentile must be between 0 and 100.")
    return percentile / 100.0


def _trapezoid(y: Sequence[float], x: Sequence[float]) -> float:
    "Trapezoidal integral of y over x (numpy>=2 dropped ``np.trapz``)."

    y_arr, x_arr = np.asarray(y, float), np.asarray(x, float)
    return float(np.sum((y_arr[:-1] + y_arr[1:]) / 2 * np.diff(x_arr)))


def _edges_and_mass(
    bin_edges: Sequence[float], probabilities: Sequence[float], scale: float
) -> tuple[np.ndarray, np.ndarray, float]:
    "Scaled bin edges, bin masses and the zero-impact mass, with the shape contract enforced."

    if bin_edges is None or probabilities is None:
        raise ValueError(
            "No impact_distribution for this asset, hazard, scenario and year. "
            "Check that the request asked for them and that the asset id matches."
        )

    edges = np.asarray(bin_edges, float) * float(scale)
    mass = np.asarray(probabilities, float)
    if edges.size != mass.size + 1:
        raise ValueError(
            f"bin_edges must have one more element than probabilities, got {edges.size} and {mass.size}."
        )
    if np.any(mass < 0):
        raise ValueError("probabilities must be non-negative.")

    zero_mass = 1.0 - float(mass.sum())
    if zero_mass < -1e-9:
        raise ValueError("probabilities sum to more than one.")
    return edges, mass, max(zero_mass, 0.0)


def pmf_from_distribution(
    bin_edges: Sequence[float],
    probabilities: Sequence[float],
    *,
    scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Probability mass function from an ``impact_distribution``, normalised to sum to one.

    Each bin is represented by its centre, which is the convention the platform's own mean impact uses,
    so the mean of this PMF equals the ``impact_mean`` the platform reports for the same asset. The
    zero-impact mass ``1 - sum(probabilities)`` becomes an atom at zero.

    Parameters
    ----------
    bin_edges:
        Impact bin edges, length ``N + 1``. Impact ratios unless ``scale`` is given.
    probabilities:
        Probability of each bin, length ``N``.
    scale:
        Multiplies the edges, e.g. the asset value base to express losses in currency units.

    Returns
    -------
    tuple
        ``(values, probs)`` sorted ascending by value, with ``probs`` summing to one.
    """

    edges, mass, zero_mass = _edges_and_mass(bin_edges, probabilities, scale)
    centres = (edges[:-1] + edges[1:]) / 2

    values = np.concatenate([[0.0], centres])
    probs = np.concatenate([[zero_mass], mass])

    order = np.argsort(values, stable=True)
    return values[order], probs[order]


def _cdf_knots(
    bin_edges: Sequence[float], probabilities: Sequence[float], scale: float
) -> tuple[np.ndarray, np.ndarray]:
    "Piecewise-linear CDF over the bin edges, assuming uniform density within each bin."

    edges, mass, zero_mass = _edges_and_mass(bin_edges, probabilities, scale)

    # F(edges[k]) = zero_mass + sum(mass[:k]); the leading knot carries the atom at zero.
    cumulative = np.concatenate([[0.0], np.cumsum(mass)])
    values = np.concatenate([[0.0], edges])
    cdf = np.concatenate([[zero_mass], zero_mass + cumulative])
    return values, np.clip(cdf, 0.0, 1.0)


def compute_var(
    bin_edges: Sequence[float],
    probabilities: Sequence[float],
    percentile: float = 95.0,
    *,
    scale: float = 1.0,
    interpolate: bool = False,
) -> float:
    r"""Value-at-Risk at ``percentile``, the loss exceeded with annual probability ``1 - p``.

    With ``interpolate=False`` this is the discrete quantile :math:`\inf\{x : F(x) \geq p\}` of the PMF,
    the smallest loss whose cumulative probability reaches ``p``, as in Alpha-Klima's financial module.
    There is no interpolation, so the result is always an actual support point.

    With ``interpolate=True`` the loss is modelled as uniform within each bin, which is the assumption the
    platform's own impact bins are built on, and the quantile is read off the piecewise-linear CDF. Prefer
    this when the distribution has few bins, where the discrete quantile snaps coarsely.
    """

    p = _check_percentile(percentile)

    if interpolate:
        values, cdf = _cdf_knots(bin_edges, probabilities, scale)
        return float(np.interp(p, cdf, values))

    values, probs = pmf_from_distribution(bin_edges, probabilities, scale=scale)
    cdf = np.cumsum(probs)
    index = np.where(np.isclose(cdf, p) + (cdf > p))[0][0]
    return float(values[index])


def compute_es(
    bin_edges: Sequence[float],
    probabilities: Sequence[float],
    percentile: float = 95.0,
    *,
    scale: float = 1.0,
    interpolate: bool = False,
) -> float:
    r"""Expected Shortfall at ``percentile``, the mean loss over the worst ``1 - p`` tail.

    Both branches evaluate :math:`\mathrm{ES}^{p} = \frac{1}{1-p} \int_{p}^{1} \mathrm{VaR}^{q} \, dq`
    under the loss model selected by ``interpolate``, so ``ES >= VaR`` always holds.

    With ``interpolate=False`` the integral has the closed form used by Alpha-Klima's financial module:
    the mass of the VaR atom lying beyond ``p`` plus every heavier atom, divided by ``1 - p``.
    """

    p = _check_percentile(percentile)

    if interpolate:
        values, cdf = _cdf_knots(bin_edges, probabilities, scale)
        grid = np.linspace(p, 1.0, 1001)
        return _trapezoid(np.interp(grid, cdf, values), grid) / (1.0 - p)

    values, probs = pmf_from_distribution(bin_edges, probabilities, scale=scale)
    cdf = np.cumsum(probs)

    k = min(int(np.searchsorted(cdf, p, side="left")), values.size - 1)
    tail_sum = float(np.sum(values[k + 1 :] * probs[k + 1 :]))
    partial_mass = float(values[k] * (cdf[k] - p))
    return (partial_mass + tail_sum) / (1.0 - p)


def var_es(
    bin_edges: Sequence[float],
    probabilities: Sequence[float],
    percentiles: Sequence[float] = DEFAULT_PERCENTILES,
    *,
    scale: float = 1.0,
    interpolate: bool = False,
) -> dict[float, tuple[float, float]]:
    """Value-at-Risk and Expected Shortfall at each percentile, as ``{percentile: (VaR, ES)}``.

    Percentiles follow the 0 to 100 convention, e.g. ``99`` for the 1-in-100-year loss.
    """

    return {
        float(p): (
            compute_var(
                bin_edges, probabilities, p, scale=scale, interpolate=interpolate
            ),
            compute_es(
                bin_edges, probabilities, p, scale=scale, interpolate=interpolate
            ),
        )
        for p in percentiles
    }


def metric_rows(
    var_es_by_scenario: Mapping[str, Mapping[float, tuple[float, float]]],
    *,
    term: str = "long",
) -> list[dict[str, Any]]:
    """Long-format metric rows, one per scenario, percentile and metric.

    This is the row shape Alpha-Klima's financial module writes for its metrics tables, and the shape the
    future endpoint will serve. The value field is named ``value`` rather than the module's
    ``metric_value`` because that rename happens at the serialization layer the plotters read from.
    """

    return [
        {
            "metric": metric,
            "scenario_name": scenario,
            "term": term,
            "percentile": float(percentile),
            "value": value,
        }
        for scenario, by_percentile in var_es_by_scenario.items()
        for percentile, (var_value, es_value) in by_percentile.items()
        for metric, value in ((VAR_METRIC, var_value), (ES_METRIC, es_value))
    ]


class _MetricsResponse:
    """Minimal stand-in for ``requests.Response``, exposing only ``json()``.

    ``financial_metrics_plots.plot_var`` and ``plot_es`` read their curves from ``response.json()``
    because they are written against the live endpoint. Wrapping the locally derived rows lets those
    plotters be reused unchanged, and keeps the call site identical to what it will be once the
    endpoint exists.
    """

    def __init__(self, curves: list[dict[str, Any]]) -> None:
        self._curves = curves

    def json(self) -> list[dict[str, Any]]:
        return self._curves


def metrics_response(
    var_es_by_scenario: Mapping[str, Mapping[float, tuple[float, float]]],
    *,
    term: str = "long",
) -> _MetricsResponse:
    """Wrap :func:`metric_rows` so ``plot_var`` and ``plot_es`` can consume it.

    The payload carries both metrics; each plotter selects the rows it needs by label, so the same
    object is passed to both.
    """

    return _MetricsResponse(metric_rows(var_es_by_scenario, term=term))
