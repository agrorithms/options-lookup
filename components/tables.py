import pandas as pd
from dash import dash_table, html
import dash_bootstrap_components as dbc


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


# =============================================================================
# HIGH-PREMIUM OPTIONS (top of page — >=6% filter)
# =============================================================================
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

    # Filter calls: keep rows where Last/Strike % >= 0.06 or MidAvg/Strike % >= 0.06
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

    calls_section = _build_options_datatable(
        filtered_calls,
        table_id="high-premium-calls-table",
        title=f"CALLS ({len(filtered_calls)} matches)",
        current_price=current_price,
        option_type="call",
        highlight_threshold=0.07,
    )

    puts_section = _build_options_datatable(
        filtered_puts,
        table_id="high-premium-puts-table",
        title=f"PUTS ({len(filtered_puts)} matches)",
        current_price=current_price,
        option_type="put",
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


# =============================================================================
# FILTERED OPTIONS CHAIN (always visible below chart)
# =============================================================================
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

    calls_table = _build_options_datatable(
        calls_records,
        table_id="filtered-calls-table",
        title=f"CALLS (1 ITM + {num_otm_calls} OTM)",
        current_price=current_price,
        option_type="call",
        highlight_threshold=0.07,
    )

    puts_table = _build_options_datatable(
        puts_records,
        table_id="filtered-puts-table",
        title=f"PUTS ({num_otm_puts} OTM + 1 ITM)",
        current_price=current_price,
        option_type="put",
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


def _build_options_datatable(records, table_id, title, current_price, option_type, highlight_threshold=0.07):
    """
    Build a single Dash DataTable for an options chain.
    highlight_threshold: decimal threshold for highlighting Last/Strike and MidAvg/Strike (e.g., 0.07 = 7%)
    """
    if not records:
        return html.Div(
            [
                html.H6(title, className="text-muted mb-2"),
                html.P("No matching options found.", className="text-muted"),
            ]
        )

    df = pd.DataFrame(records)

    columns = []
    col_config = {
        "strike": {"name": "Strike", "type": "numeric",
                    "format": dash_table.FormatTemplate.money(2)},
        "lastPrice": {"name": "Last", "type": "numeric",
                      "format": dash_table.FormatTemplate.money(2)},
        "bid": {"name": "Bid", "type": "numeric",
                "format": dash_table.FormatTemplate.money(2)},
        "ask": {"name": "Ask", "type": "numeric",
                "format": dash_table.FormatTemplate.money(2)},
        "Last/Strike %": {"name": "Last/Str%", "type": "numeric",
                          "format": dash_table.FormatTemplate.percentage(2)},
        "MidAvg/Strike %": {"name": "Mid/Str%", "type": "numeric",
                            "format": dash_table.FormatTemplate.percentage(2)},
        "volume": {"name": "Vol", "type": "numeric"},
        "openInterest": {"name": "OI", "type": "numeric"},
        "impliedVolatility": {"name": "IV%", "type": "numeric"},
        "delta": {"name": "Δ", "type": "numeric"},
        "gamma": {"name": "Γ", "type": "numeric"},
        "theta": {"name": "Θ", "type": "numeric"},
        "vega": {"name": "V", "type": "numeric"},
        "rho": {"name": "ρ", "type": "numeric"},
        "inTheMoney": {"name": "ITM", "type": "text"},
    }

    for col_id, config in col_config.items():
        if col_id in df.columns:
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
                sort_action="native",
                fixed_rows={"headers": True},
                page_action="none",
            ),
        ]
    )


def _build_options_conditional_styles(df, current_price, option_type, highlight_threshold=0.07):
    """Build conditional style rules for options DataTable."""
    styles = []

    # Highlight ITM rows
    if "inTheMoney" in df.columns:
        styles.append(
            {
                "if": {
                    "filter_query": "{inTheMoney} = true || {inTheMoney} = True",
                },
                "backgroundColor": COLORS["bg_itm"],
                "fontWeight": "bold",
            }
        )

    # Highlight >= threshold Last/Strike for OTM options
    if "Last/Strike %" in df.columns and "inTheMoney" in df.columns:
        styles.append(
            {
                "if": {
                    "filter_query": (
                        f"{{Last/Strike %}} >= {highlight_threshold}"
                        f" && ({{inTheMoney}} = false || {{inTheMoney}} = False)"
                    ),
                    "column_id": "Last/Strike %",
                },
                "backgroundColor": COLORS["bg_highlight_yellow"],
                "color": COLORS["text_yellow"],
                "fontWeight": "bold",
            }
        )

    # Highlight >= threshold MidAvg/Strike for OTM options
    if "MidAvg/Strike %" in df.columns and "inTheMoney" in df.columns:
        styles.append(
            {
                "if": {
                    "filter_query": (
                        f"{{MidAvg/Strike %}} >= {highlight_threshold}"
                        f" && ({{inTheMoney}} = false || {{inTheMoney}} = False)"
                    ),
                    "column_id": "MidAvg/Strike %",
                },
                "backgroundColor": COLORS["bg_highlight_yellow"],
                "color": COLORS["text_yellow"],
                "fontWeight": "bold",
            }
        )

    # Color-code delta
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

    # Color-code theta
    if "theta" in df.columns:
        styles.append(
            {
                "if": {"filter_query": "{theta} < 0", "column_id": "theta"},
                "color": COLORS["text_red"],
            }
        )

    # Highlight high IV (>50%)
    if "impliedVolatility" in df.columns:
        styles.append(
            {
                "if": {
                    "filter_query": "{impliedVolatility} > 50",
                    "column_id": "impliedVolatility",
                },
                "backgroundColor": COLORS["bg_highlight_yellow"],
                "color": COLORS["text_yellow"],
                "fontWeight": "bold",
            }
        )

    return styles


# =============================================================================
# UNFILTERED OPTIONS
# =============================================================================
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
                            highlight_threshold=0.07,
                        ),
                        lg=6,
                    ),
                ]
            ),
        ]
    )


# =============================================================================
# COMPANY DESCRIPTION CARD
# =============================================================================
def build_company_description(profile_data):
    """Build a scrollable card showing the company business description."""
    if not profile_data or not profile_data.get("success"):
        error_msg = (
            profile_data.get("error", "No profile data available.")
            if profile_data
            else "No profile data available."
        )
        return html.P(error_msg, className="text-danger")

    data = profile_data["data"]
    description = data.get("longBusinessSummary", "No description available.")
    name = data.get("longName", "Company")

    return dbc.Card(
        dbc.CardBody(
            [
                html.H5(f"About {name}", className="mb-2"),
                html.Div(
                    html.P(description, className="mb-0", style={"lineHeight": "1.6"}),
                    style={
                        "maxHeight": "150px",
                        "overflowY": "auto",
                        "paddingRight": "10px",
                    },
                ),
            ]
        ),
        className="mb-3",
    )


# =============================================================================
# FULL COMPANY PROFILE TABLE
# =============================================================================
def build_full_company_profile(profile_data):
    """Build a detailed company profile display for the tabbed section."""
    if not profile_data or not profile_data.get("success"):
        error_msg = (
            profile_data.get("error", "No profile data available.")
            if profile_data
            else "No profile data available."
        )
        return html.P(error_msg, className="text-danger")

    data = profile_data["data"]

    def fmt_market_cap(val):
        if val in ("N/A", None):
            return "N/A"
        if val >= 1_000_000_000_000:
            return f"${val / 1_000_000_000_000:.2f}T"
        elif val >= 1_000_000_000:
            return f"${val / 1_000_000_000:.2f}B"
        elif val >= 1_000_000:
            return f"${val / 1_000_000:.2f}M"
        return f"${val:,.0f}"

    def fmt_number(val):
        if val in ("N/A", None):
            return "N/A"
        try:
            return f"{val:,.0f}"
        except (TypeError, ValueError):
            return str(val)

    rows = [
        ("Company Name", data.get("longName", "N/A")),
        ("Sector", data.get("sector", "N/A")),
        ("Industry", data.get("industry", "N/A")),
        ("Exchange", data.get("exchange", "N/A")),
        ("Currency", data.get("currency", "N/A")),
        ("Country", data.get("country", "N/A")),
        ("City / State", f"{data.get('city', 'N/A')}, {data.get('state', 'N/A')}"),
        ("Website", data.get("website", "N/A")),
        ("Full-Time Employees", fmt_number(data.get("fullTimeEmployees", "N/A"))),
        ("Market Cap", fmt_market_cap(data.get("marketCap", "N/A"))),
        ("Current Price", f"${data.get('regularMarketPrice', 'N/A')}"),
        ("Previous Close", f"${data.get('previousClose', 'N/A')}"),
        ("52-Week High", f"${data.get('fiftyTwoWeekHigh', 'N/A')}"),
        ("52-Week Low", f"${data.get('fiftyTwoWeekLow', 'N/A')}"),
        ("Average Volume", fmt_number(data.get("averageVolume", "N/A"))),
        ("Trailing P/E", data.get("trailingPE", "N/A")),
        ("Forward P/E", data.get("forwardPE", "N/A")),
        ("Beta", data.get("beta", "N/A")),
    ]

    table_rows = []
    for label, value in rows:
        table_rows.append(
            html.Tr(
                [
                    html.Td(label, className="fw-bold", style={"width": "40%"}),
                    html.Td(str(value)),
                ]
            )
        )

    description = data.get("longBusinessSummary", "N/A")

    return html.Div(
        [
            dbc.Table(
                [html.Tbody(table_rows)],
                bordered=True,
                hover=True,
                striped=True,
                color="dark",
                className="mb-3",
            ),
            html.H6("Business Description", className="mt-3 mb-2"),
            html.Div(
                html.P(description, style={"lineHeight": "1.6"}),
                style={
                    "maxHeight": "300px",
                    "overflowY": "auto",
                    "paddingRight": "10px",
                },
            ),
        ]
    )


# =============================================================================
# COMPANY INFO SIDEBAR (left of chart)
# =============================================================================
def build_company_info_sidebar(profile_data, all_data):
    """
    Build a compact company info panel to sit to the left of the chart.
    Shows ticker, price, market cap, 52W range, P/E, beta.
    """
    if not profile_data or not profile_data.get("success"):
        return html.Div(
            html.P("No data", className="text-muted small"),
            className="p-2",
        )

    p = profile_data["data"]
    ticker = all_data.get("ticker", "")

    market_cap = p.get("marketCap", "N/A")
    if market_cap not in ("N/A", None):
        if market_cap >= 1_000_000_000_000:
            market_cap_str = f"${market_cap / 1_000_000_000_000:.2f}T"
        elif market_cap >= 1_000_000_000:
            market_cap_str = f"${market_cap / 1_000_000_000:.2f}B"
        elif market_cap >= 1_000_000:
            market_cap_str = f"${market_cap / 1_000_000:.2f}M"
        else:
            market_cap_str = f"${market_cap:,.0f}"
    else:
        market_cap_str = "N/A"

    price = p.get("regularMarketPrice", "N/A")
    prev_close = p.get("previousClose", None)

    # Calculate price change
    change_str = ""
    change_class = "text-muted"
    if price not in ("N/A", None) and prev_close not in ("N/A", None) and prev_close:
        change = price - prev_close
        change_pct = (change / prev_close) * 100
        if change >= 0:
            change_str = f"+${change:.2f} (+{change_pct:.2f}%)"
            change_class = "text-success"
        else:
            change_str = f"-${abs(change):.2f} ({change_pct:.2f}%)"
            change_class = "text-danger"

    info_items = [
        ("Price", f"${price}" if price != "N/A" else "N/A", "fs-4 fw-bold text-success"),
        ("Change", change_str or "N/A", f"small {change_class}"),
        ("Mkt Cap", market_cap_str, "small"),
        ("52W High", f"${p.get('fiftyTwoWeekHigh', 'N/A')}", "small"),
        ("52W Low", f"${p.get('fiftyTwoWeekLow', 'N/A')}", "small"),
        ("P/E (TTM)", str(p.get("trailingPE", "N/A")), "small"),
        ("Fwd P/E", str(p.get("forwardPE", "N/A")), "small"),
        ("Beta", str(p.get("beta", "N/A")), "small"),
        ("Avg Vol", _fmt_volume(p.get("averageVolume", "N/A")), "small"),
    ]

    children = [
        html.H5(f"{p.get('longName', ticker)}", className="mb-0", style={"fontSize": "14px"}),
        html.Span(ticker, className="text-muted small d-block mb-2"),
        html.Span(
            f"{p.get('sector', 'N/A')}",
            className="text-muted d-block mb-2",
            style={"fontSize": "11px"},
        ),
    ]

    for label, value, css_class in info_items:
        children.append(
            html.Div(
                [
                    html.Span(f"{label}: ", className="text-muted", style={"fontSize": "11px"}),
                    html.Span(value, className=css_class, style={"fontSize": "12px"} if "fs-4" not in css_class else {}),
                ],
                className="mb-1",
            )
        )

    children.append(
        html.Div(
            html.Span(
                f"Fetched: {all_data.get('fetched_at', '')}",
                className="text-muted",
                style={"fontSize": "10px"},
            ),
            className="mt-2 pt-2",
            style={"borderTop": "1px solid #444"},
        )
    )

    return html.Div(children, className="p-2")


def _fmt_volume(val):
    """Format volume number to human-readable string."""
    if val in ("N/A", None):
        return "N/A"
    try:
        val = float(val)
        if val >= 1_000_000_000:
            return f"{val / 1_000_000_000:.1f}B"
        elif val >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        elif val >= 1_000:
            return f"{val / 1_000:.1f}K"
        return f"{val:,.0f}"
    except (TypeError, ValueError):
        return str(val)


# =============================================================================
# ANALYST RATINGS SECTION (always visible)
# =============================================================================
def build_analyst_ratings_section(analyst_data):
    """
    Build the always-visible analyst ratings section.
    Shows recommendation summary badges on top and upgrades/downgrades table below.
    """
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
            html.P(
                "No recent upgrades/downgrades available.",
                className="text-muted mt-2",
            )
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
        style_data_conditional=style_conditions,
        sort_action="native",
        fixed_rows={"headers": True},
        page_action="none",
    )


# =============================================================================
# EARNINGS TABLE
# =============================================================================
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

    # Earnings dates (EPS actual vs estimate)
    ed = data.get("earnings_dates")
    if ed and len(ed) > 0:
        children.append(
            html.H6("EPS: Actual vs. Estimated (Last 4 Quarters)", className="mb-2")
        )
        children.append(_build_generic_datatable(ed, "earnings-dates-table"))
    else:
        children.append(
            html.P("No earnings dates data available.", className="text-muted")
        )

    # Quarterly income statement (replaces deprecated quarterly_earnings)
    qi = data.get("quarterly_income")
    if qi and len(qi) > 0:
        children.append(
            html.H6("Quarterly Income Highlights", className="mt-3 mb-2")
        )
        children.append(_build_generic_datatable(qi, "quarterly-income-table"))
    else:
        children.append(
            html.P("No quarterly income data available.", className="text-muted")
        )

    return html.Div(children)



# =============================================================================
# DIVIDENDS TABLE
# =============================================================================
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
        children.append(_build_generic_datatable(history, "dividend-history-table"))
    else:
        children.append(
            html.P("No dividend history available.", className="text-muted")
        )

    return html.Div(children)


# =============================================================================
# FINANCIALS TABLES
# =============================================================================
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
            content = _build_generic_datatable(records, f"{key}-table")
        else:
            content = html.P(
                f"No {statement_name.lower()} data available.",
                className="text-muted",
            )

        tabs.append(
            dbc.Tab(content, label=statement_name, tab_id=f"fin-tab-{key}")
        )

    return dbc.Tabs(tabs, active_tab="fin-tab-income_statement")


# =============================================================================
# INSIDER TRANSACTIONS TABLE
# =============================================================================
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
        children.append(_build_generic_datatable(it, "insider-transactions-table"))
    else:
        children.append(
            html.P("No insider transactions available.", className="text-muted")
        )

    ip = data.get("insider_purchases")
    if ip and len(ip) > 0:
        children.append(
            html.H6("Insider Purchases Summary", className="mt-3 mb-2")
        )
        children.append(_build_generic_datatable(ip, "insider-purchases-table"))

    ih = data.get("institutional_holders")
    if ih and len(ih) > 0:
        children.append(
            html.H6("Top Institutional Holders", className="mt-3 mb-2")
        )
        children.append(_build_generic_datatable(ih, "institutional-holders-table"))

    return html.Div(children)


# =============================================================================
# GENERIC DATATABLE BUILDER
# =============================================================================
def _build_generic_datatable(records, table_id):
    """Build a generic styled DataTable from a list of records."""
    if not records:
        return html.P("No data available.", className="text-muted")

    df = pd.DataFrame(records)

    columns = [{"name": str(col), "id": str(col)} for col in df.columns]

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
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#383838",
            }
        ],
        sort_action="native",
        fixed_rows={"headers": True},
        page_action="none",
    )
