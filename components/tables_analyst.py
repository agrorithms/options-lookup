import pandas as pd
from dash import dash_table, html
import dash_bootstrap_components as dbc
from components.table_utils import COLORS


def build_analyst_ratings_section(analyst_data):
    """Build the always-visible analyst ratings section."""
    if not analyst_data or not analyst_data.get("success"):
        error_msg = (
            analyst_data.get("error", "No analyst data available.")
            if analyst_data
            else "No analyst data available."
        )
        return html.P(error_msg, className="text-danger")

    data = analyst_data.get("data", {})
    children = []

    recs = data.get("recommendations")
    if recs and len(recs) > 0:
        rec_df = pd.DataFrame(recs)
        children.append(_build_recommendation_badges(rec_df))
    else:
        children.append(
            html.P("No recommendation summary available.", className="text-muted")
        )

    uds = data.get("upgrades_downgrades")
    if uds and len(uds) > 0:
        children.append(html.H6("Recent Upgrades / Downgrades", className="mt-3 mb-2"))
        children.append(_build_upgrades_downgrades_table(uds))
    else:
        children.append(
            html.P("No recent upgrades/downgrades available.", className="text-muted mt-2")
        )

    return dbc.Card(
        dbc.CardBody(
            [html.H5("Analyst Ratings", className="mb-3")] + children
        ),
        className="mb-3",
    )


def _build_recommendation_badges(rec_df):
    """Build visual badge row from recommendations summary."""
    badge_map = {
        "strongBuy": {"label": "Strong Buy", "color": "success"},
        "buy": {"label": "Buy", "color": "info"},
        "hold": {"label": "Hold", "color": "warning"},
        "sell": {"label": "Sell", "color": "danger"},
        "strongSell": {"label": "Strong Sell", "color": "dark"},
    }

    badges = []

    if all(col in rec_df.columns for col in badge_map.keys()):
        latest = rec_df.iloc[0] if len(rec_df) > 0 else None
        if latest is not None:
            for key, config in badge_map.items():
                count = latest.get(key, 0)
                try:
                    count = int(count)
                except (TypeError, ValueError):
                    count = 0
                badges.append(
                    dbc.Badge(
                        f"{config['label']}: {count}",
                        color=config["color"],
                        className="me-2 fs-6 px-3 py-2",
                    )
                )
    else:
        for col in rec_df.columns:
            if rec_df[col].dtype in ("int64", "float64"):
                latest_val = rec_df.iloc[0].get(col, 0) if len(rec_df) > 0 else 0
                badges.append(
                    dbc.Badge(
                        f"{col}: {latest_val}",
                        color="secondary",
                        className="me-2 fs-6 px-3 py-2",
                    )
                )

    if not badges:
        return html.P("No recommendation counts available.", className="text-muted")

    return html.Div(badges, className="d-flex flex-wrap mb-2")


def _build_upgrades_downgrades_table(ud_records):
    """Build a DataTable for upgrades/downgrades."""
    df = pd.DataFrame(ud_records)

    columns = []
    col_names = {
        "GradeDate": "Date",
        "Firm": "Firm",
        "ToGrade": "To Grade",
        "FromGrade": "From Grade",
        "Action": "Action",
    }

    for col_id, display_name in col_names.items():
        if col_id in df.columns:
            columns.append({"name": display_name, "id": col_id})

    style_conditions = [
        {
            "if": {"filter_query": '{Action} = "up"'},
            "color": COLORS["text_green"],
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": '{Action} = "down"'},
            "color": COLORS["text_red"],
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": '{Action} = "init"'},
            "color": "#64b5f6",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": '{Action} = "main"'},
            "color": COLORS["text_muted"],
        },
    ]

    return dash_table.DataTable(
        columns=columns,
        data=ud_records,
        style_table={
            "overflowX": "auto",
            "maxHeight": "300px",
            "overflowY": "auto",
        },
        style_header={
            "backgroundColor": COLORS["bg_header"],
            "color": COLORS["text_white"],
            "fontWeight": "bold",
            "border": f"1px solid {COLORS['border']}",
            "fontSize": "13px",
        },
        style_cell={
            "backgroundColor": COLORS["bg_cell"],
            "color": COLORS["text_white"],
            "border": f"1px solid {COLORS['border']}",
            "fontSize": "13px",
            "padding": "8px",
            "textAlign": "left",
        },
        style_data_conditional=style_conditions,  # type: ignore
        sort_action="native",
        fixed_rows={"headers": True},
        page_action="none",
    )
