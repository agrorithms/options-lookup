from dash import html
import dash_bootstrap_components as dbc
from components.table_utils import COLORS


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


def build_company_info_sidebar(profile_data, all_data):
    """Build a compact company info panel to sit to the left of the chart."""
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
                    html.Span(
                        value,
                        className=css_class,
                        style={"fontSize": "12px"} if "fs-4" not in css_class else {},
                    ),
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
