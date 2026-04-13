from dash import html
import dash_bootstrap_components as dbc
from components.table_utils import build_generic_datatable


def build_financials_section(financials_data):
    """Build the financials display with sub-tabs for each statement."""
    if not financials_data or not financials_data.get("success"):
        error_msg = (
            financials_data.get("error", "No financial data available.")
            if financials_data
            else "No financial data available."
        )
        return html.P(error_msg, className="text-danger")

    data = financials_data.get("data", {})

    tabs = []
    for statement_name, key in [
        ("Income Statement", "income_statement"),
        ("Balance Sheet", "balance_sheet"),
        ("Cash Flow", "cash_flow"),
    ]:
        records = data.get(key)
        if records and len(records) > 0:
            content = build_generic_datatable(records, f"{key}-table")
        else:
            content = html.P(
                f"No {statement_name.lower()} data available.",
                className="text-muted",
            )

        tabs.append(
            dbc.Tab(content, label=statement_name, tab_id=f"fin-tab-{key}")
        )

    return dbc.Tabs(tabs, active_tab="fin-tab-income_statement")
