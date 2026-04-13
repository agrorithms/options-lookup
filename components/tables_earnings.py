from dash import html
from components.table_utils import build_generic_datatable


def build_earnings_section(earnings_data):
    """Build the earnings display for the tabbed section."""
    if not earnings_data or not earnings_data.get("success"):
        error_msg = (
            earnings_data.get("error", "No earnings data available.")
            if earnings_data
            else "No earnings data available."
        )
        return html.P(error_msg, className="text-danger")

    data = earnings_data.get("data", {})
    children = []

    ed = data.get("earnings_dates")
    if ed and len(ed) > 0:
        children.append(
            html.H6("EPS: Actual vs. Estimated (Last 4 Quarters)", className="mb-2")
        )
        children.append(build_generic_datatable(ed, "earnings-dates-table"))
    else:
        children.append(
            html.P("No earnings dates data available.", className="text-muted")
        )

    qi = data.get("quarterly_income")
    if qi and len(qi) > 0:
        children.append(
            html.H6("Quarterly Income Highlights", className="mt-3 mb-2")
        )
        children.append(build_generic_datatable(qi, "quarterly-income-table"))
    else:
        children.append(
            html.P("No quarterly income data available.", className="text-muted")
        )

    return html.Div(children)
