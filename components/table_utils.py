import pandas as pd
from dash import dash_table, html

# =============================================================================
# COLOR CONSTANTS
# =============================================================================
COLORS = {
    "bg_dark": "#222",
    "bg_cell": "#303030",
    "bg_header": "#1a1a2e",
    "bg_itm": "#2c3e50",
    "bg_highlight_green": "#1b4332",
    "bg_highlight_red": "#4a1a1a",
    "bg_highlight_yellow": "#4a3f1a",
    "text_white": "#fff",
    "text_green": "#26a69a",
    "text_red": "#ef5350",
    "text_yellow": "#ffd54f",
    "text_muted": "#888",
    "border": "#444",
}


def build_generic_datatable(records, table_id):
    """Build a generic styled DataTable from a list of records."""
    if not records:
        return html.P("No data available.", className="text-muted")

    df = pd.DataFrame(records)

    # Create columns with explicit type to satisfy dash table typing
    columns = []
    for col in df.columns:
        col_def = {"name": str(col), "id": str(col), "type": "text"}
        columns.append(col_def)

    # Build style_data_conditional separately to avoid literal typing complaints
    style_data_conditional = [
        {
            "if": {"row_index": "odd"},
            "backgroundColor": "#383838",
        }
    ]

    return dash_table.DataTable(
        id=table_id,
        columns=columns,
        data=records,
        style_table={
            "overflowX": "auto",
            "maxHeight": "500px",
            "overflowY": "auto",
        },
        style_header={
            "backgroundColor": COLORS["bg_header"],
            "color": COLORS["text_white"],
            "fontWeight": "bold",
            "border": f"1px solid {COLORS['border']}",
            "fontSize": "13px",
            "textAlign": "center",
        },
        style_cell={
            "backgroundColor": COLORS["bg_cell"],
            "color": COLORS["text_white"],
            "border": f"1px solid {COLORS['border']}",
            "fontSize": "13px",
            "padding": "8px",
            "textAlign": "right",
            "minWidth": "80px",
            "maxWidth": "200px",
            "whiteSpace": "normal",
        },
        style_data_conditional=style_data_conditional,  # type: ignore
        sort_action="native",
        fixed_rows={"headers": True},
        page_action="none",
    )
