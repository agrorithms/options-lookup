from dash import html
from components.table_utils import build_generic_datatable


def build_insider_section(insider_data):
    """Build the insider transactions display."""
    if not insider_data or not insider_data.get("success"):
        error_msg = (
            insider_data.get("error", "No insider data available.")
            if insider_data
            else "No insider data available."
        )
        return html.P(error_msg, className="text-danger")

    data = insider_data.get("data", {})
    children = []

    it = data.get("insider_transactions")
    if it and len(it) > 0:
        children.append(html.H6("Insider Transactions", className="mb-2"))
        children.append(build_generic_datatable(it, "insider-transactions-table"))
    else:
        children.append(
            html.P("No insider transactions available.", className="text-muted")
        )

    ip = data.get("insider_purchases")
    if ip and len(ip) > 0:
        children.append(
            html.H6("Insider Purchases Summary", className="mt-3 mb-2")
        )
        children.append(build_generic_datatable(ip, "insider-purchases-table"))

    ih = data.get("institutional_holders")
    if ih and len(ih) > 0:
        children.append(
            html.H6("Top Institutional Holders", className="mt-3 mb-2")
        )
        children.append(build_generic_datatable(ih, "institutional-holders-table"))

    return html.Div(children)
