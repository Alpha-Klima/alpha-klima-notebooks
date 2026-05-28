import ast
import logging
import math
from pathlib import Path
import json

import pandas as pd
import plotly.express as px


logger = logging.getLogger(__name__)

CNAE_SECTIONS = {
    "A": "Agricultura, ganadería, silvicultura y pesca",
    "B": "Industrias extractivas",
    "C": "Industria manufacturera",
    "D": "Suministro de energía eléctrica, gas, vapor y aire acondicionado",
    "E": "Suministro de agua, actividades de saneamiento, gestión de residuos y descontaminación",
    "F": "Construcción",
    "G": "Comercio al por mayor y al por menor; reparación de vehículos de motor y motocicletas",
    "H": "Transporte y almacenamiento",
    "I": "Hostelería",
    "J": "Información y comunicaciones",
    "K": "Actividades financieras y de seguros",
    "L": "Actividades inmobiliarias",
    "M": "Actividades profesionales, científicas y técnicas",
    "N": "Actividades administrativas y servicios auxiliares",
    "O": "Administración pública y defensa; seguridad social obligatoria",
    "P": "Educación",
    "Q": "Actividades sanitarias y de servicios sociales",
    "R": "Actividades artísticas, recreativas y de entretenimiento",
    "S": "Otros servicios",
    "T": "Actividades de los hogares como empleadores de personal doméstico; "
         "actividades de los hogares como productores de bienes y servicios para uso propio",
    "U": "Actividades de organizaciones y organismos extraterritoriales",
}


def load_portfolio_asset(path):
    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data

def _as_number(value):
    if value is None or pd.isna(value):
        return 0.0
    return float(value)


def _pie_figure(values_by_label, title, value_name):
    chart_data = pd.DataFrame(
        [
            {"category": label, value_name: value}
            for label, value in values_by_label.items()
            if value > 0
        ]
    )

    if chart_data.empty:
        raise ValueError(f"No positive values available to draw '{title}'.")

    fig = px.pie(
        chart_data,
        names="category",
        values=value_name,
        title=title,
        hole=0.0,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}<br>%{value:,.2f}<br>%{percent}<extra></extra>",
    )
    fig.update_layout(
        legend_title_text="",
        margin=dict(t=70, b=30, l=30, r=30),
    )
    return fig


def loan_volumes_by_collateral_type(portfolio_asset):
    collateral_types = {
        "Physical collateral": 0.0,
        "Financial collateral": 0.0,
        "Unsecured": 0.0,
    }

    for asset in portfolio_asset:
        physical_col = _as_number(asset.get("physical_collateral"))
        financial_col = _as_number(asset.get("financial_collateral"))
        gross_col = _as_number(asset.get("gross_exposure"))
        collateral_types["Physical collateral"] += physical_col
        collateral_types["Financial collateral"] += financial_col
        collateral_types["Unsecured"] += max(gross_col - physical_col - financial_col, 0.0)

    return _pie_figure(
        collateral_types,
        "Exposure volumes by type of collateral",
        "volume",
    )


def _physical_collateral_category(asset):
    asset_type = asset.get("physical_collateral_type")
    if asset_type is None:
        return "Physical collateral"
    else:
        return f"{asset_type} physical collateral"


def collateral_by_category(portfolio_asset):
    collateral_categories = {}

    for asset in portfolio_asset:
        physical_collateral = _as_number(asset.get("physical_collateral"))
        financial_collateral = _as_number(asset.get("financial_collateral"))

        if physical_collateral > 0:
            category = _physical_collateral_category(asset)
            collateral_categories[category] = collateral_categories.get(category, 0) + physical_collateral

        if financial_collateral > 0:
            
            collateral_categories["Financial collateral"] = collateral_categories.get("Financial collateral", 0) + financial_collateral

    if not collateral_categories:
        logger.warning("Skipping collateral by category chart: no collateral found.")
        return None

    return _pie_figure(
        collateral_categories,
        "Collateral by category",
        "collateral_amount",
    )


def asset_cnae_groups(portfolio_asset):
    cnae_groups = {}

    for asset in portfolio_asset:
        group = asset.get("group_cnae") or "Unknown"
        description = CNAE_SECTIONS.get(group, "Unknown")
        label = f"{group} - {description}" if group != "Unknown" else description
        cnae_groups[label] = cnae_groups.get(label, 0.0) + _as_number(
            asset.get("gross_exposure")
        )

    return _pie_figure(
        cnae_groups,
        "Asset CNAE groups by gross exposure",
        "gross_exposure",
    )


def show_all_portfolio_charts(portfolio_asset):
    figures = [
        loan_volumes_by_collateral_type(portfolio_asset),
        collateral_by_category(portfolio_asset),
        asset_cnae_groups(portfolio_asset),
    ]

    for fig in figures:
        if fig is not None:
            fig.show()

    return [fig for fig in figures if fig is not None]


if __name__ == "__main__":
    PORTFOLIO_ASSET_PATH = Path(__file__).with_name("portfolio_asset.txt")

    portfolio_asset = load_portfolio_asset()
    show_all_portfolio_charts(portfolio_asset)
