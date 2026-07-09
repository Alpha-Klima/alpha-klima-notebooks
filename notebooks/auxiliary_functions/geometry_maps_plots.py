import numpy as np
import plotly.graph_objects as go
from shapely import MultiPolygon, Polygon, wkt


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
    color: str = "0, 146, 160",
) -> go.Figure:
    fillcolor = "rgba(" + color + ", 0.5)"
    linecolor = "rgba(" + color + ", 1.0)"

    fig = go.Figure()

    for n, g, v in zip(cluster_names, geometries, values, strict=True):
        g = wkt.loads(g)
        if isinstance(g, Polygon):
            geom = [g]
        elif isinstance(g, MultiPolygon):
            geom = list(g.geoms)
        else:
            raise ValueError(f"Not valid geometry {type(g)}")

        for poly in geom:
            lon, lat = poly.exterior.xy

            fig.add_trace(
                go.Scattermap(
                    lon=list(lon),
                    lat=list(lat),
                    mode="lines",
                    fill="toself",
                    fillcolor=fillcolor,
                    line=dict(color=linecolor, width=2),
                    hovertext=f"Name: {n}. Value: {v}",
                    hoverinfo="text",
                )
            )

    fig.add_trace(
        go.Scattermap(
            lat=asset_lat,
            lon=asset_lon,
            mode="markers",
            marker=dict(
                symbol="circle",
                size=10,
                color="rgba(117,117,117,0.8)",
            ),
            text=asset_name,
        )
    )

    fig.update_layout(
        map=dict(
            style="carto-positron",
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        width=1000,
        height=600,
        showlegend=False,
    )

    return fig
