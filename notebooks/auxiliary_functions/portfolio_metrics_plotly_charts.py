import ast
import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


RISK_SCORES_SHEET = "Portfolio risk scores by hazard"
PORTFOLIO_METRICS_SHEET = "Portfolio metrics"
HAZARD_METRICS_SHEET = "Portfolio metrics by hazard"

RISK_LEVELS = ["Low", "Medium", "High"]
RISK_COLORS = {
    "Low": "#2f9e44",
    "Medium": "#f59f00",
    "High": "#e03131",
}
METRIC_COLORS = {
    "NEAR": "#5c7cfa",
    "CEAR": "#f08c00",
}




def _as_number(value):
    if value is None or pd.isna(value):
        return 0.0
    if isinstance(value, str):
        value = value.replace("€", "").replace("%", "").replace(",", "").strip()
    return float(value)


def _norm_name(value):
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _find_column(columns, candidates, contains_any=None):
    normalized = {_norm_name(col): col for col in columns}
    for candidate in candidates:
        key = _norm_name(candidate)
        if key in normalized:
            return normalized[key]

    if contains_any:
        for col in columns:
            key = _norm_name(col)
            if any(token in key for token in contains_any):
                return col

    return None


def _compact_euro(value):
    value = _as_number(value)
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"€{value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"€{value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"€{value / 1_000:.1f}K"
    return f"€{value:,.0f}"


def _percent_label(value, decimals=1):
    return f"{100 * _as_number(value):.{decimals}f}%"


def _metric_as_amount(value, portfolio_total):
    value = _as_number(value)
    if abs(value) <= 1:
        return value * portfolio_total
    return value


def _metric_as_fraction(value, portfolio_total):
    value = _as_number(value)
    if abs(value) <= 1:
        return value
    if portfolio_total:
        return value / portfolio_total
    return 0.0


def _add_axis_anchors(fig, x_values, axis_max):
    if not x_values:
        return

    fig.add_scatter(
        x=[x_values[0], x_values[-1]],
        y=[0, axis_max],
        yaxis="y",
        mode="markers",
        marker=dict(size=1, color="rgba(0, 0, 0, 0.001)"),
        showlegend=False,
        hoverinfo="skip",
    )
    fig.add_scatter(
        x=[x_values[0], x_values[-1]],
        y=[0, 1],
        yaxis="y2",
        mode="markers",
        marker=dict(size=1, color="rgba(0, 0, 0, 0.001)"),
        showlegend=False,
        hoverinfo="skip",
    )


def _hazard_labels(df, hazard_col, indicator_col=None):
    hazards = df[hazard_col].astype(str).str.strip()
    duplicate_hazard = hazards.duplicated(keep=False)

    if indicator_col is None or indicator_col not in df.columns:
        return hazards

    indicators = df[indicator_col].astype(str).str.strip()
    return hazards.where(
        ~duplicate_hazard,
        hazards + " (" + indicators + ")",
    )


def _portfolio_frame(portfolio_asset):
    df = pd.DataFrame(portfolio_asset).copy()
    if "asset_id" not in df.columns and "id" in df.columns:
        df["asset_id"] = df["id"].astype(str)
    if "asset_id" in df.columns:
        df["asset_id"] = df["asset_id"].astype(str)
    if "gross_exposure" not in df.columns:
        raise ValueError("Portfolio data must contain a gross_exposure field.")
    df["gross_exposure"] = pd.to_numeric(df["gross_exposure"], errors="coerce").fillna(0.0)
    return df


def _normalize_risk_score(value):
    if value is None or pd.isna(value):
        return "No risk"

    text = str(value).strip()
    key = text.lower().replace("_", " ").replace("-", " ")
    if key in {"no risk", "none", "nan", "0", "0.0"}:
        return "No risk"
    if key in {"low", "1", "1.0"}:
        return "Low"
    if key in {"medium", "med", "2", "2.0"}:
        return "Medium"
    if key in {"high", "3", "3.0", "4", "4.0"}:
        return "High"
    return text.title()


def _read_excel_sheet(path, sheet_name):
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    raw = raw.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)

    hazard_header_rows = raw.apply(
        lambda row: row.astype(str).str.strip().str.lower().eq("hazard").any(),
        axis=1,
    )
    if hazard_header_rows.any():
        header_idx = int(hazard_header_rows[hazard_header_rows].index[0])
        header = [
            f"blank_{idx}" if pd.isna(value) else str(value).strip()
            for idx, value in enumerate(raw.iloc[header_idx].tolist())
        ]
        df = raw.iloc[header_idx + 1 :].copy()
        df.columns = header
        df = df.dropna(how="all").dropna(axis=1, how="all")
        return df

    non_empty_cols = raw.columns[raw.notna().any()].tolist()
    if len(non_empty_cols) >= 2:
        df = raw[non_empty_cols[-2:]].copy()
        df.columns = ["metric", "value"]
        df = df.dropna(how="all")
        return df

    df = raw.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _metric_column(df, metric):
    metric_key = _norm_name(metric)
    for col in df.columns:
        col_key = _norm_name(col)
        if col_key == metric_key or col_key.endswith(f"_{metric_key}") or metric_key in col_key:
            return col
    return None


def _extract_metric_value(df, metric):
    metric_col = _metric_column(df, metric)
    if metric_col is not None:
        values = pd.to_numeric(df[metric_col], errors="coerce").dropna()
        if not values.empty:
            return float(values.iloc[0])

    label_col = _find_column(df.columns, ["metric", "metrics", "name", "indicator"], contains_any=["metric"])
    value_col = _find_column(df.columns, ["value", "amount", "eur", "percentage"])
    if label_col and value_col:
        mask = df[label_col].astype(str).str.upper().str.strip().eq(metric.upper())
        values = pd.to_numeric(df.loc[mask, value_col], errors="coerce").dropna()
        if not values.empty:
            return float(values.iloc[0])

    return 0.0


def _metrics_by_hazard(metrics_df):
    hazard_col = _find_column(metrics_df.columns, ["hazard"], contains_any=["hazard"])
    if hazard_col is None:
        hazard_col = metrics_df.columns[0]
    indicator_col = _find_column(metrics_df.columns, ["indicator"], contains_any=["indicator"])

    out = metrics_df.copy()
    out = out.rename(columns={hazard_col: "hazard"})
    out["hazard"] = _hazard_labels(metrics_df, hazard_col, indicator_col).values

    for metric in ["PEAR", "NEAR", "CEAR"]:
        col = _metric_column(out, metric)
        if col is None:
            out[metric] = 0.0
        else:
            out[metric] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    return (
        out.groupby("hazard", as_index=False)
        .agg({"PEAR": "max", "NEAR": "sum", "CEAR": "sum"})
        [["hazard", "PEAR", "NEAR", "CEAR"]]
    )


def _risk_scores_long(risk_df, portfolio_df):
    hazard_col = _find_column(risk_df.columns, ["hazard"], contains_any=["hazard"])
    indicator_col = _find_column(risk_df.columns, ["indicator"], contains_any=["indicator"])
    level_cols = {
        "Low": _find_column(risk_df.columns, ["Level 1 - Low risk"], contains_any=["low"]),
        "Medium": _find_column(risk_df.columns, ["Level 2 - Medium risk"], contains_any=["medium"]),
        "High": _find_column(risk_df.columns, ["Level 3 - High risk"], contains_any=["high"]),
    }
    score_col = _find_column(
        risk_df.columns,
        ["risk_score", "risk score", "score", "risk_level", "risk level"],
        contains_any=["risk_score", "risk_level", "score"],
    )
    amount_col = _find_column(
        risk_df.columns,
        ["gross_exposure", "exposure", "amount", "portfolio_amount"],
        contains_any=["exposure", "amount"],
    )

    if hazard_col is not None and any(level_cols.values()) and score_col is None:
        total_exposure = portfolio_df["gross_exposure"].sum()
        hazard_labels = _hazard_labels(risk_df, hazard_col, indicator_col)
        records = []
        for index, row in risk_df.iterrows():
            hazard = str(hazard_labels.loc[index]).strip()
            if not hazard or hazard.lower() == "nan":
                continue
            for level, col in level_cols.items():
                if col is None:
                    continue
                share_or_amount = _as_number(row[col])
                amount = share_or_amount * total_exposure if abs(share_or_amount) <= 1 else share_or_amount
                records.append({"hazard": hazard, "risk_score": level, "amount": amount})

        return (
            pd.DataFrame(records)
            .groupby(["hazard", "risk_score"], as_index=False)["amount"]
            .max()
        )

    if hazard_col is not None and score_col is not None:
        long_df = risk_df[[hazard_col, score_col] + ([amount_col] if amount_col else [])].copy()
        long_df = long_df.rename(columns={hazard_col: "hazard", score_col: "risk_score"})
        long_df["hazard"] = _hazard_labels(risk_df, hazard_col, indicator_col).values
        if amount_col:
            long_df = long_df.rename(columns={amount_col: "amount"})
        else:
            id_col = _find_column(risk_df.columns, ["asset_id", "id"], contains_any=["asset_id"])
            if id_col is None:
                raise ValueError("Risk score sheet needs an amount column or an asset_id column.")
            long_df["asset_id"] = risk_df[id_col].astype(str)
            long_df = long_df.merge(portfolio_df[["asset_id", "gross_exposure"]], on="asset_id", how="left")
            long_df = long_df.rename(columns={"gross_exposure": "amount"})
        return long_df[["hazard", "risk_score", "amount"]]

    id_col = _find_column(risk_df.columns, ["asset_id", "id"], contains_any=["asset_id"])
    amount_col = amount_col if amount_col in risk_df.columns else None
    metadata_cols = {col for col in [id_col, amount_col] if col is not None}
    hazard_cols = [col for col in risk_df.columns if col not in metadata_cols]

    long_df = risk_df.melt(
        id_vars=[col for col in [id_col, amount_col] if col is not None],
        value_vars=hazard_cols,
        var_name="hazard",
        value_name="risk_score",
    )
    if amount_col:
        long_df = long_df.rename(columns={amount_col: "amount"})
    elif id_col:
        long_df["asset_id"] = long_df[id_col].astype(str)
        long_df = long_df.merge(portfolio_df[["asset_id", "gross_exposure"]], on="asset_id", how="left")
        long_df = long_df.rename(columns={"gross_exposure": "amount"})
    else:
        raise ValueError("Could not identify asset ids or exposure amounts in the risk score sheet.")

    return long_df[["hazard", "risk_score", "amount"]]


def risk_score_distribution_by_hazard(
    risk_scores_df,
    hazard_metrics_df,
    portfolio_df,
    title="Risk Score distribution by hazard",
):
    long_df = _risk_scores_long(risk_scores_df, portfolio_df)
    long_df["hazard"] = long_df["hazard"].astype(str).str.strip()
    long_df["risk_score"] = long_df["risk_score"].map(_normalize_risk_score)
    long_df["amount"] = pd.to_numeric(long_df["amount"], errors="coerce").fillna(0.0)
    long_df = long_df[long_df["risk_score"].isin(RISK_LEVELS)]

    grouped = (
        long_df.groupby(["hazard", "risk_score"], as_index=False)["amount"]
        .sum()
        .pivot(index="hazard", columns="risk_score", values="amount")
        .fillna(0.0)
    )

    hazard_metrics = _metrics_by_hazard(hazard_metrics_df).set_index("hazard")
    hazards = hazard_metrics.index.tolist()
    hazards += [hazard for hazard in grouped.index.tolist() if hazard not in hazards]

    total_exposure = portfolio_df["gross_exposure"].sum()
    pear_amount_by_hazard = {
        hazard: (
            _metric_as_amount(hazard_metrics.loc[hazard, "PEAR"], total_exposure)
            if hazard in hazard_metrics.index
            else grouped.loc[hazard].sum()
        )
        for hazard in hazards
    }
    pear_pct_by_hazard = {
        hazard: (
            _metric_as_fraction(hazard_metrics.loc[hazard, "PEAR"], total_exposure)
            if hazard in hazard_metrics.index
            else pear_amount_by_hazard[hazard] / total_exposure if total_exposure else 0.0
        )
        for hazard in hazards
    }

    fig = go.Figure()
    for level in RISK_LEVELS:
        values = [float(grouped.loc[hazard, level]) if hazard in grouped.index and level in grouped.columns else 0.0 for hazard in hazards]
        fig.add_bar(
            name=level,
            x=hazards,
            y=values,
            marker_color=RISK_COLORS[level],
            customdata=[[value / total_exposure if total_exposure else 0.0] for value in values],
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"Risk Score: {level}<br>"
                "Exposure: %{y:,.0f} EUR<br>"
                "Portfolio share: %{customdata[0]:.1%}<extra></extra>"
            ),
        )

    # Position PEAR labels at the top of each stacked hazard bar
    bar_end_by_hazard = {
        hazard: sum(
            float(grouped.loc[hazard, level])
            if hazard in grouped.index and level in grouped.columns
            else 0.0
            for level in RISK_LEVELS
        )
        for hazard in hazards
    }

    for hazard in hazards:
        fig.add_annotation(
            x=hazard,
            y=bar_end_by_hazard[hazard],
            xref="x",
            yref="y",
            text=f"PEAR = {_percent_label(pear_pct_by_hazard[hazard])}",
            showarrow=False,
            font=dict(size=12, color="#343a40"),
            yanchor="bottom",
            yshift=6,
        )

    axis_max = max(total_exposure, max([pear_amount_by_hazard.get(hazard, 0.0) for hazard in hazards] + [1.0]))
    _add_axis_anchors(fig, hazards, axis_max)
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left"),
        barmode="stack",
        bargap=0.35,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=13, color="#212529"),
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=90, r=80, b=115, l=85),
        yaxis=dict(
            title="Exposure amount (EUR)",
            tickprefix="€",
            tickformat="~s",
            gridcolor="#e9ecef",
            range=[0, axis_max],
            showline=True,
            linecolor="#adb5bd",
        ),
        yaxis2=dict(
            title="Share of portfolio",
            overlaying="y",
            side="right",
            range=[0, 1],
            tickmode="auto",
            tickformat=".0%",
            scaleanchor="y",
            scaleratio=total_exposure if total_exposure else 1,
            showgrid=False,
            showline=True,
            linecolor="#adb5bd",
            ticks="outside",
        ),
    )
    return fig


def expected_loss_metrics_by_hazard(
    portfolio_metrics_df,
    hazard_metrics_df,
    portfolio_df,
    title="Expected loss metrics by hazard",
):
    hazard_metrics = _metrics_by_hazard(hazard_metrics_df)
    total_exposure = portfolio_df["gross_exposure"].sum()

    categories = hazard_metrics["hazard"].tolist() + ["Total portfolio"]
    near_raw_values = hazard_metrics["NEAR"].tolist() + [_extract_metric_value(portfolio_metrics_df, "NEAR")]
    cear_raw_values = hazard_metrics["CEAR"].tolist() + [_extract_metric_value(portfolio_metrics_df, "CEAR")]

    near_values = [_metric_as_amount(value, total_exposure) for value in near_raw_values]
    cear_values = [_metric_as_amount(value, total_exposure) for value in cear_raw_values]
    near_pct = [_metric_as_fraction(value, total_exposure) for value in near_raw_values]
    cear_pct = [_metric_as_fraction(value, total_exposure) for value in cear_raw_values]

    fig = go.Figure()
    fig.add_bar(
        name="NEAR",
        x=categories,
        y=near_values,
        width=0.58,
        offset=-0.13,
        marker=dict(color=METRIC_COLORS["NEAR"], opacity=0.72, line=dict(color="#364fc7", width=1)),
        customdata=[[pct, _compact_euro(value)] for value, pct in zip(near_values, near_pct)],
        hovertemplate=(
            "<b>%{x}</b><br>"
            "NEAR: %{customdata[1]}<br>"
            "Share of portfolio: %{customdata[0]:.2%}<extra></extra>"
        ),
    )
    fig.add_bar(
        name="CEAR",
        x=categories,
        y=cear_values,
        width=0.40,
        offset=0.13,
        marker=dict(color=METRIC_COLORS["CEAR"], opacity=0.9, line=dict(color="#c05621", width=1)),
        customdata=[[pct, _compact_euro(value)] for value, pct in zip(cear_values, cear_pct)],
        text=[_compact_euro(value) for value in cear_values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "CEAR: %{customdata[1]}<br>"
            "Share of portfolio: %{customdata[0]:.2%}<extra></extra>"
        ),
    )

    axis_max = max(total_exposure, max(near_values + cear_values + [1.0]))
    _add_axis_anchors(fig, categories, axis_max)
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left"),
        barmode="overlay",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=13, color="#212529"),
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=90, r=85, b=80, l=85),
        yaxis=dict(
            title="Expected loss (EUR)",
            tickprefix="€",
            tickformat="~s",
            gridcolor="#e9ecef",
            range=[0, axis_max],
            showline=True,
            linecolor="#adb5bd",
        ),
        yaxis2=dict(
            title="Share of portfolio",
            overlaying="y",
            side="right",
            range=[0, 1],
            tickmode="auto",
            tickformat=".0%",
            scaleanchor="y",
            scaleratio=total_exposure if total_exposure else 1,
            showgrid=False,
            showline=True,
            linecolor="#adb5bd",
            ticks="outside",
        ),
    )
    return fig


def build_figures(
    portfolio_asset,
    portfolio_metrics_path,
):
    portfolio_df = _portfolio_frame(portfolio_asset)

    risk_scores_df = _read_excel_sheet(portfolio_metrics_path, RISK_SCORES_SHEET)
    portfolio_metrics_df = _read_excel_sheet(portfolio_metrics_path, PORTFOLIO_METRICS_SHEET)
    hazard_metrics_df = _read_excel_sheet(portfolio_metrics_path, HAZARD_METRICS_SHEET)

    risk_fig = risk_score_distribution_by_hazard(risk_scores_df, hazard_metrics_df, portfolio_df)
    expected_loss_fig = expected_loss_metrics_by_hazard(
        portfolio_metrics_df,
        hazard_metrics_df,
        portfolio_df,
    )
    return risk_fig, expected_loss_fig


def show_all_portfolio_metric_charts(
        portfolio_asset,
        portfolio_metrics_path
    ):
    figures = build_figures(portfolio_asset, portfolio_metrics_path)
    for fig in figures:
        fig.show()
    return figures


if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_DIR = SCRIPT_DIR.parent
    DEFAULT_RESULTS_DIR = PROJECT_DIR / "downloaded_results" / "2026-05-18"
    PORTFOLIO_METRICS_PATH = DEFAULT_RESULTS_DIR / "portfolio_metrics_Arfima.xlsx"
    PORTFOLIO_ASSET_PATH = DEFAULT_RESULTS_DIR / "portfolio_asset.txt"


    def load_portfolio_asset(path):
        path = Path(path)
        if (not path.exists() or path.stat().st_size == 0):
            raise ValueError(f"Portfolio asset file not located: {path}")

        raw_text = path.read_text(encoding="utf-8").strip()
        if not raw_text:
            raise ValueError(f"Portfolio asset file is empty: {path}")

        if raw_text.startswith("portfolio_asset") and "=" in raw_text:
            raw_text = raw_text.split("=", 1)[1].strip()

        try:
            portfolio_text = ast.literal_eval(raw_text)
        except (SyntaxError, ValueError):
            portfolio_text = raw_text

        if not isinstance(portfolio_text, str):
            return portfolio_text

        return eval(
            portfolio_text,
            {"__builtins__": {}},
            {"Timestamp": pd.Timestamp, "nan": math.nan},
        )


    portfolio_asset = load_portfolio_asset(PORTFOLIO_ASSET_PATH)
    show_all_portfolio_metric_charts(portfolio_asset, PORTFOLIO_METRICS_PATH)
