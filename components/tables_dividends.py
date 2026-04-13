from dash import html
import dash_bootstrap_components as dbc
from components.table_utils import build_generic_datatable


def build_dividends_section(dividends_data):
    """Build the dividends display for the tabbed section."""
    if not dividends_data or not dividends_data.get("success"):
        error_msg = (
            dividends_data.get("error", "No dividend data available.")
            if dividends_data
            else "No dividend data available."
        )
        return html.P(error_msg, className="text-danger")

    data = dividends_data.get("data", {})
    info = data.get("info", {})
    history = data.get("history")

    children = []

    info_items = [
        ("Annual Rate", info.get("dividendRate", "N/A"), "primary"),
        ("Yield", f"{info.get('dividendYield', 'N/A')}%", "success"),
        ("Payout Ratio", f"{info.get('payoutRatio', 'N/A')}%", "info"),
        ("Ex-Dividend Date", info.get("exDividendDate", "N/A"), "secondary"),
        ("5Y Avg Yield", f"{info.get('fiveYearAvgDividendYield', 'N/A')}%", "warning"),
    ]

    badges = []
    for label, value, color in info_items:
        if value not in ("N/A", "N/A%", "None%", None):
            badges.append(
                dbc.Badge(
                    f"{label}: {value}",
                    color=color,
                    className="me-2 mb-2 fs-6 px-3 py-2",
                )
            )

    if badges:
        children.append(html.Div(badges, className="d-flex flex-wrap mb-3"))
    else:
        children.append(
            html.P("This stock may not pay dividends.", className="text-muted")
        )

    if history and len(history) > 0:
        children.append(
            html.H6("Dividend History (Last 12 Payments)", className="mb-2")
        )
        children.append(build_generic_datatable(history, "dividend-history-table"))
    else:
        children.append(
            html.P("No dividend history available.", className="text-muted")
        )

    return html.Div(children)
