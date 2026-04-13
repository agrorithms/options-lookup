import pandas as pd
from data.fetchers import calculate_ivr_ivp
from dash import dash_table, html
import dash_bootstrap_components as dbc
from components.table_utils import COLORS

def add_ivr_ivp(records, ticker_symbol, iv_col="impliedVolatility"):
    """
    For each record, add IVR and IVP columns synchronously.
    Returns a new list of records with 'IVR' and 'IVP' keys.
    """
    new_records = [dict(r) for r in records]
    for rec in new_records:
        iv = rec.get(iv_col)
        # Try to convert IV to float if it's a string
        try:
            iv_val = float(iv)
        except (TypeError, ValueError):
            iv_val = None
        if iv_val is None or not ticker_symbol:
            rec["IVR"] = None
            rec["IVP"] = None
            continue
        try:
            ivr, ivp = calculate_ivr_ivp(ticker_symbol, iv_val)
            rec["IVR"] = ivr
            rec["IVP"] = ivp
        except Exception:
            rec["IVR"] = None
            rec["IVP"] = None
    return new_records


def build_high_premium_options_section(options_data):
    """
    Build the top-of-page options section showing only OTM options
    (or the first ITM) where Last/Strike % or MidAvg/Strike % >= 6%.
    """
    if not options_data or not options_data.get("success"):
        error_msg = (
            options_data.get("error", "No options data available.")
            if options_data
            else "No options data available."
        )
        return dbc.Card(
            dbc.CardBody(html.P(error_msg, className="text-danger")),
            className="mb-3",
        )

    data = options_data["data"]
    calls_records = data.get("calls", [])
    puts_records = data.get("puts", [])
    current_price = data.get("current_price", 0)
    exp_date = data.get("expiration_date", "N/A")
    days_to_exp = data.get("days_to_expiration", "N/A")

    filtered_calls = _filter_high_premium(calls_records, threshold=0.06)
    filtered_puts = _filter_high_premium(puts_records, threshold=0.06)

    header = dbc.Row(
        [
            dbc.Col(
                html.H5(
                    f"High Premium Options (≥6%) — Exp: {exp_date} ({days_to_exp}d)",
                    className="mb-0",
                ),
                md=8,
            ),
            dbc.Col(
                html.Span(
                    f"Stock: ${current_price:.2f}",
                    className="text-success fw-bold fs-5",
                ),
                md=4,
                className="text-end",
            ),
        ],
        className="mb-2 align-items-center",
    )

    ticker_symbol = options_data.get("ticker") if options_data else None
    calls_section = _build_options_datatable(
        filtered_calls,
        table_id="high-premium-calls-table",
        title=f"CALLS ({len(filtered_calls)} matches)",
        current_price=current_price,
        option_type="call",
        ticker_symbol=ticker_symbol,
        highlight_threshold=0.07,
    )

    puts_section = _build_options_datatable(
        filtered_puts,
        table_id="high-premium-puts-table",
        title=f"PUTS ({len(filtered_puts)} matches)",
        current_price=current_price,
        option_type="put",
        ticker_symbol=ticker_symbol,
        highlight_threshold=0.07,
    )

    return dbc.Card(
        dbc.CardBody(
            [
                header,
                dbc.Row(
                    [
                        dbc.Col(calls_section, lg=6, className="mb-3 mb-lg-0"),
                        dbc.Col(puts_section, lg=6),
                    ]
                ),
            ]
        ),
        className="mb-3",
    )


def _filter_high_premium(records, threshold=0.06):
    """Filter option records to only those with Last/Strike or MidAvg/Strike >= threshold."""
    if not records:
        return []

    filtered = []
    for record in records:
        last_strike = record.get("Last/Strike %", 0) or 0
        mid_strike = record.get("MidAvg/Strike %", 0) or 0
        if last_strike >= threshold or mid_strike >= threshold:
            filtered.append(record)

    return filtered


def build_filtered_options_section(options_data):
    """
    Build the always-visible filtered options section.
    Calls and puts displayed side by side on desktop, stacked on mobile.
    """
    if not options_data or not options_data.get("success"):
        error_msg = (
            options_data.get("error", "No options data available.")
            if options_data
            else "No options data available."
        )
        return html.Div(
            html.P(error_msg, className="text-danger"),
            className="mb-3",
        )

    data = options_data["data"]
    calls_records = data.get("calls", [])
    puts_records = data.get("puts", [])
    current_price = data.get("current_price", 0)
    exp_date = data.get("expiration_date", "N/A")
    days_to_exp = data.get("days_to_expiration", "N/A")
    num_otm_calls = data.get("num_otm_calls", 0)
    num_otm_puts = data.get("num_otm_puts", 0)

    header = dbc.Row(
        [
            dbc.Col(
                html.H5(
                    f"Options Chain — Exp: {exp_date} ({days_to_exp}d)",
                    className="mb-0",
                ),
                md=8,
            ),
            dbc.Col(
                html.Span(
                    f"Stock: ${current_price:.2f}",
                    className="text-success fw-bold fs-5",
                ),
                md=4,
                className="text-end",
            ),
        ],
        className="mb-2 align-items-center",
    )

    ticker_symbol = options_data.get("ticker") if options_data else None
    calls_table = _build_options_datatable(
        calls_records,
        table_id="filtered-calls-table",
        title=f"CALLS (1 ITM + {num_otm_calls} OTM)",
        current_price=current_price,
        option_type="call",
        ticker_symbol=ticker_symbol,
        highlight_threshold=0.07,
    )

    puts_table = _build_options_datatable(
        puts_records,
        table_id="filtered-puts-table",
        title=f"PUTS ({num_otm_puts} OTM + 1 ITM)",
        current_price=current_price,
        option_type="put",
        ticker_symbol=ticker_symbol,
        highlight_threshold=0.07,
    )

    return dbc.Card(
        dbc.CardBody(
            [
                header,
                dbc.Row(
                    [
                        dbc.Col(calls_table, lg=6, className="mb-3 mb-lg-0"),
                        dbc.Col(puts_table, lg=6),
                    ]
                ),
            ]
        ),
        className="mb-3",
    )


def build_unfiltered_options_section(options_data):
    """Build the full unfiltered options chain for the tabbed section."""
    if not options_data or not options_data.get("success"):
        error_msg = (
            options_data.get("error", "No options data available.")
            if options_data
            else "No options data available."
        )
        return html.P(error_msg, className="text-danger")

    data = options_data["data"]

    ticker_symbol = options_data.get("ticker") if options_data else None
    return html.Div(
        [
            html.P(
                "Showing filtered options (1 ITM + OTM). "
                "Full unfiltered chain can be added as a future enhancement.",
                className="text-muted mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        _build_options_datatable(
                            data.get("calls", []),
                            table_id="unfiltered-calls-table",
                            title="ALL CALLS",
                            current_price=data.get("current_price", 0),
                            option_type="call",
                            ticker_symbol=ticker_symbol,
                            highlight_threshold=0.07,
                        ),
                        lg=6,
                        className="mb-3 mb-lg-0",
                    ),
                    dbc.Col(
                        _build_options_datatable(
                            data.get("puts", []),
                            table_id="unfiltered-puts-table",
                            title="ALL PUTS",
                            current_price=data.get("current_price", 0),
                            option_type="put",
                            ticker_symbol=ticker_symbol,
                            highlight_threshold=0.07,
                        ),
                        lg=6,
                    ),
                ]
            ),
        ]
    )


def _build_options_datatable(records, table_id, title, current_price, option_type, ticker_symbol=None, highlight_threshold=0.07):
    """Build a single Dash DataTable for an options chain."""
    if not records:
        return html.Div(
            [
                html.H6(title, className="text-muted mb-2"),
                html.P("No matching options found.", className="text-muted"),
            ]
        )

    resolved_ticker = ticker_symbol
    if not resolved_ticker and records:
        if "underlyingSymbol" in records[0]:
            resolved_ticker = records[0]["underlyingSymbol"]
        elif "symbol" in records[0]:
            resolved_ticker = records[0]["symbol"]
    if isinstance(resolved_ticker, str):
        resolved_ticker = resolved_ticker.upper()

    records = add_ivr_ivp(records, resolved_ticker)

    df = pd.DataFrame(records)


    # Define column order: IV, IVR, IVP together.
    col_config = {
        "strike": {"name": "Strike", "type": "numeric", "format": dash_table.FormatTemplate.money(2)},
        "lastPrice": {"name": "Last", "type": "numeric", "format": dash_table.FormatTemplate.money(2)},
        "bid": {"name": "Bid", "type": "numeric", "format": dash_table.FormatTemplate.money(2)},
        "ask": {"name": "Ask", "type": "numeric", "format": dash_table.FormatTemplate.money(2)},
        "Last/Strike %": {"name": "Last/Str%", "type": "numeric", "format": dash_table.FormatTemplate.percentage(2)},
        "MidAvg/Strike %": {"name": "Mid/Str%", "type": "numeric", "format": dash_table.FormatTemplate.percentage(2)},
        "volume": {"name": "Vol", "type": "numeric"},
        "openInterest": {"name": "OI", "type": "numeric"},
        "impliedVolatility": {"name": "IV%", "type": "numeric", "format": dash_table.FormatTemplate.percentage(2)},
        "IVR": {"name": "IVR", "type": "numeric"},
        "IVP": {"name": "IVP", "type": "numeric"},
        "delta": {"name": "Δ", "type": "numeric"},
        "gamma": {"name": "Γ", "type": "numeric"},
        "theta": {"name": "Θ", "type": "numeric"},
        "vega": {"name": "V", "type": "numeric"},
        "rho": {"name": "ρ", "type": "numeric"},
    }

    # Desired column order: ... IV, IVR, IVP ...
    desired_order = [
        "strike", "lastPrice", "bid", "ask",
        "Last/Strike %", "MidAvg/Strike %", "volume", "openInterest",
        "impliedVolatility", "IVR", "IVP",
        "delta", "gamma", "theta", "vega", "rho"
    ]
    columns = []
    for col_id in desired_order:
        if col_id in df.columns and col_id in col_config:
            config = col_config[col_id]
            col_def = {
                "name": config["name"],
                "id": col_id,
                "type": config.get("type", "text"),
            }
            if "format" in config:
                col_def["format"] = config["format"]
            columns.append(col_def)

    style_conditions = _build_options_conditional_styles(
        df, current_price, option_type, highlight_threshold
    )

    return html.Div(
        [
            html.H6(title, className="mb-2"),
            dash_table.DataTable(
                id=table_id,
                columns=columns,
                data=records,
                style_table={
                    "overflowX": "auto",
                    "maxHeight": "400px",
                    "overflowY": "auto",
                },
                style_header={
                    "backgroundColor": COLORS["bg_header"],
                    "color": COLORS["text_white"],
                    "fontWeight": "bold",
                    "border": f"1px solid {COLORS['border']}",
                    "fontSize": "12px",
                    "textAlign": "center",
                },
                style_cell={
                    "backgroundColor": COLORS["bg_cell"],
                    "color": COLORS["text_white"],
                    "border": f"1px solid {COLORS['border']}",
                    "fontSize": "12px",
                    "padding": "6px 8px",
                    "textAlign": "right",
                    "minWidth": "55px",
                    "maxWidth": "100px",
                },
                style_data_conditional=style_conditions,
                css=[
                    {
                        "selector": "tr:hover td",
                        "rule": "background-color: #2f3640 !important; color: #f8f9fa !important;",
                    }
                ],
                sort_action="native",
                fixed_rows={"headers": True},
                page_action="none",
            ),
        ]
    )


def _build_options_conditional_styles(df, current_price, option_type, highlight_threshold=0.07):
    """Build conditional style rules for options DataTable."""
    styles = []
    itm_query = None

    if "strike" in df.columns and current_price is not None:
        try:
            price = float(current_price)
            if option_type == "call":
                itm_query = f"{{strike}} < {price}"
            elif option_type == "put":
                itm_query = f"{{strike}} > {price}"
        except (TypeError, ValueError):
            itm_query = None

    if itm_query:
        styles.append(
            {
                "if": {
                    "filter_query": itm_query,
                },
                "backgroundColor": "#3a2f0b",
                "color": COLORS["text_white"],
                "fontWeight": "bold",
                "borderLeft": "3px solid #ffc107",
            }
        )

    if "Last/Strike %" in df.columns:
        styles.append(
            {
                "if": {
                    "filter_query": f"{{Last/Strike %}} >= {highlight_threshold}",
                    "column_id": "Last/Strike %",
                },
                "color": COLORS["text_green"],
                "fontWeight": "bold",
            }
        )

    if "MidAvg/Strike %" in df.columns:
        styles.append(
            {
                "if": {
                    "filter_query": f"{{MidAvg/Strike %}} >= {highlight_threshold}",
                    "column_id": "MidAvg/Strike %",
                },
                "color": COLORS["text_green"],
                "fontWeight": "bold",
            }
        )

    if "delta" in df.columns:
        styles.extend(
            [
                {
                    "if": {"filter_query": "{delta} > 0", "column_id": "delta"},
                    "color": COLORS["text_green"],
                },
                {
                    "if": {"filter_query": "{delta} < 0", "column_id": "delta"},
                    "color": COLORS["text_red"],
                },
            ]
        )

    if "theta" in df.columns:
        styles.append(
            {
                "if": {"filter_query": "{theta} < 0", "column_id": "theta"},
                "color": COLORS["text_red"],
            }
        )

    if "impliedVolatility" in df.columns:
        styles.append(
            {
                "if": {
                    "filter_query": "{impliedVolatility} > 0.5",
                    "column_id": "impliedVolatility",
                },
                "backgroundColor": COLORS["bg_highlight_yellow"],
                "color": COLORS["text_yellow"],
                "fontWeight": "bold",
            }
        )

    return styles
