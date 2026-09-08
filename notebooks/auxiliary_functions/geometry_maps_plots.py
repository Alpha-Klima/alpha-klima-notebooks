import math

import numpy as np
import plotly.graph_objects as go
from shapely import MultiPolygon, Polygon, wkt

SURFACE = "#fcfcfb"
ASSET_MARKER = "#52514e"  # recessive: the cluster footprint is the subject

# One colour per hazard, so a cluster map is recognisable at a glance. Water hazards
# share a blue family, wind takes the blue-green, and the aggregated Combined view is
# deliberately neutral because it is not a hazard of its own. These are kept clear of
# the scenario colours used on the financial charts, so a blue on a map is never
# mistaken for the historical scenario.
HAZARD_FILL = {
    "RiverineInundation": "#14406E",
    "CoastalInundation": "#1B4F86",
    "Wind": "#0092A0",
    "Fire": "#E15E0B",
    "Landslide": "#4A3AA7",
    "Combined": "#8E8C86",
    "MultiHazard": "#8E8C86",
}
DEFAULT_FILL = "#0092A0"

# maplibre tiles are 512px at zoom 0
_TILE_PX = 512


def _hex_to_rgb_str(color: str) -> str:
    """Accept "#2F6FB3" or an already-built "r, g, b" string."""
    if not color.startswith("#"):
        return color
    h = color.lstrip("#")
    return ", ".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def _mercator_y(lat: float) -> float:
    """Normalized Web Mercator y in [0, 1]."""
    lat = max(min(lat, 85.05112878), -85.05112878)
    rad = math.radians(lat)
    return 0.5 - math.log(math.tan(math.pi / 4 + rad / 2)) / (2 * math.pi)


def fit_view(
    lats: list[float],
    lons: list[float],
    *,
    width: int = 1000,
    height: int = 600,
    pad: float = 0.18,
    max_zoom: float = 13.0,
) -> tuple[float, float, float]:
    """Centre and zoom that bring every given point into view.

    Plotly has no fitbounds for map traces, so the zoom is derived from the bounding
    box: without it the figure opens on the whole world.
    """
    lats = [float(v) for v in lats if v is not None and np.isfinite(v)]
    lons = [float(v) for v in lons if v is not None and np.isfinite(v)]
    if not lats or not lons:
        return 0.0, 0.0, 1.0

    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    centre_lat = (lat_min + lat_max) / 2
    centre_lon = (lon_min + lon_max) / 2

    lon_span = (lon_max - lon_min) * (1 + 2 * pad)
    y_span = abs(_mercator_y(lat_max) - _mercator_y(lat_min)) * (1 + 2 * pad)

    zooms = []
    if lon_span > 0:
        zooms.append(math.log2(width / _TILE_PX * 360 / lon_span))
    if y_span > 0:
        zooms.append(math.log2(height / _TILE_PX / y_span))
    zoom = min(zooms) if zooms else 10.0  # a single point has no span to fit
    return centre_lat, centre_lon, max(1.0, min(zoom, max_zoom))


def show_portfolio(
    *,
    latitudes: list[float],
    longitudes: list[float],
    asset_ids: list[int] | None = None,
    names: list[str] | None = None,
    values: list[float] | None = None,
) -> go.Figure:
    customdata_cols = []
    hover_lines = []
    marker_sizes = 10

    if asset_ids is not None:
        customdata_cols.append(asset_ids)
        hover_lines.append(f"ID: %{{customdata[{len(customdata_cols) - 1}]}}<br>")

    if names is not None:
        customdata_cols.append(names)
        hover_lines.append(f"Name: %{{customdata[{len(customdata_cols) - 1}]}}<br>")

    if values is not None:
        customdata_cols.append(values)
        hover_lines.append(
            f"Value: %{{customdata[{len(customdata_cols) - 1}]:,.0f}} EUR<br>"
        )
        marker_sizes = np.interp(
            values,
            (np.min(values), np.max(values)),
            (8, 30),
        )

    trace_kwargs = dict(
        lat=latitudes,
        lon=longitudes,
        mode="markers",
        marker=dict(
            symbol="circle",
            size=marker_sizes,
            color="rgba(0, 146, 160, 1.0)",
        ),
    )
    if customdata_cols:
        trace_kwargs["customdata"] = np.stack(customdata_cols, axis=-1)
        trace_kwargs["hovertemplate"] = "".join(hover_lines) + "<extra></extra>"

    center_lat = np.mean(latitudes)
    center_lon = np.mean(longitudes)

    fig = go.Figure()

    fig.add_trace(go.Scattermap(**trace_kwargs))

    fig.update_layout(
        map=dict(
            style="carto-positron",
            zoom=5,
            center=dict(
                lat=center_lat,
                lon=center_lon,
            ),
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        width=1000,
        height=600,
        showlegend=False,
    )

    return fig


def plot_clusters(
    *,
    geometries: list[Polygon | MultiPolygon],
    cluster_names: list[str],
    values: list[float],
    asset_lat: list[float] | None = None,
    asset_lon: list[float] | None = None,
    asset_name: list[str] | None = None,
    hazard: str | None = None,
    color: str | None = None,
    width: int = 1000,
    height: int = 600,
    fit_to: str = "clusters",
) -> go.Figure:
    """Cluster footprints with the portfolio assets on top.

    The view is fitted to what the map is meant to show. ``fit_to="clusters"`` frames
    the cluster footprints, which can be far larger than the assets inside them;
    ``fit_to="all"`` also keeps every asset in frame.
    """
    if color is None:
        color = HAZARD_FILL.get(hazard, DEFAULT_FILL) if hazard else DEFAULT_FILL
    rgb = _hex_to_rgb_str(color)
    fillcolor = f"rgba({rgb}, 0.35)"
    linecolor = f"rgba({rgb}, 1.0)"

    fig = go.Figure()
    poly_lats: list[float] = []
    poly_lons: list[float] = []

    for n, g, v in zip(cluster_names, geometries, values, strict=True):
        g = wkt.loads(g) if isinstance(g, str) else g
        if isinstance(g, Polygon):
            geom = [g]
        elif isinstance(g, MultiPolygon):
            geom = list(g.geoms)
        else:
            raise ValueError(f"Not valid geometry {type(g)}")

        for poly in geom:
            lon, lat = poly.exterior.xy
            poly_lats.extend(lat)
            poly_lons.extend(lon)

            fig.add_trace(
                go.Scattermap(
                    lon=list(lon),
                    lat=list(lat),
                    mode="lines",
                    fill="toself",
                    fillcolor=fillcolor,
                    line=dict(color=linecolor, width=2),
                    hovertext=f"{n}<br>Value: {v:,.0f} EUR",
                    hoverinfo="text",
                )
            )

    if asset_lat is not None and asset_lon is not None:
        # Map markers take no outline, so the surface ring is a slightly larger
        # marker drawn underneath. It keeps the assets legible on any cluster fill,
        # including the neutral Combined one.
        fig.add_trace(
            go.Scattermap(
                lat=asset_lat, lon=asset_lon, mode="markers",
                marker=dict(symbol="circle", size=12, color=SURFACE),
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scattermap(
                lat=asset_lat,
                lon=asset_lon,
                mode="markers",
                marker=dict(symbol="circle", size=8, color=ASSET_MARKER),
                text=asset_name,
                hoverinfo="text",
            )
        )

    fit_lats = list(poly_lats)
    fit_lons = list(poly_lons)
    if fit_to == "all" and asset_lat is not None and asset_lon is not None:
        fit_lats += list(asset_lat)
        fit_lons += list(asset_lon)
    centre_lat, centre_lon, zoom = fit_view(fit_lats, fit_lons, width=width, height=height)

    fig.update_layout(
        map=dict(
            style="carto-positron",
            center=dict(lat=centre_lat, lon=centre_lon),
            zoom=zoom,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        width=width,
        height=height,
        showlegend=False,
    )

    return fig
