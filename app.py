import dash
import time
import json
import sys
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback, no_update, ctx
from components.layout import create_layout
from components.charts import build_candlestick_chart, build_analyst_recommendation_chart
from components.tables_options import (
    build_high_premium_options_section,
    build_filtered_options_section,
    build_unfiltered_options_section,
)
from components.tables_company import (
    build_company_description,
    build_full_company_profile,
    build_company_info_sidebar,
)
from components.tables_analyst import build_analyst_ratings_section
from components.tables_earnings import build_earnings_section
from components.tables_dividends import build_dividends_section
from components.tables_financials import build_financials_section
from components.tables_insider import build_insider_section
from data.fetchers import fetch_all_data, fetch_historical_data
import plotly.graph_objects as go

# Initialize the Dash app with DARKLY Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ],
)

server = app.server
app.title = "Stock Dashboard"
app.layout = create_layout()

# =============================================================================
# CLIENT-SIDE URL UPDATE
# Updates the browser URL bar without triggering server-side callbacks.
# This breaks the circular dependency because clientside callbacks
# don't feed back into the Dash callback graph.
# =============================================================================
app.clientside_callback(
    """
    function(data) {
        if (data && data.ticker) {
            var newPath = "/" + data.ticker;
            if (window.location.pathname !== newPath) {
                window.history.pushState({}, "", newPath);
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("url", "search"),  # Dummy output that won't trigger other callbacks
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)

# =============================================================================
# PERIOD/INTERVAL BUTTON ID MAPS
# =============================================================================
PERIOD_BUTTON_MAP = {
    "period-1d": "1d",
    "period-5d": "5d",
    "period-1mo": "1mo",
    "period-6mo": "6mo",
    "period-ytd": "ytd",
    "period-1y": "1y",
    "period-5y": "5y",
    "period-max": "max",
}

INTERVAL_BUTTON_MAP = {
    "interval-1m": "1m",
    "interval-5m": "5m",
    "interval-15m": "15m",
    "interval-30m": "30m",
    "interval-1h": "1h",
    "interval-1d": "1d",
    "interval-1wk": "1wk",
    "interval-1mo": "1mo",
}

ALL_PERIOD_IDS = list(PERIOD_BUTTON_MAP.keys())
ALL_INTERVAL_IDS = list(INTERVAL_BUTTON_MAP.keys())

# =============================================================================
# URL ROUTING: Read ticker from URL path and auto-populate + auto-fetch
# =============================================================================
@callback(
    Output("ticker-input", "value"),
    Output("url-trigger-store", "data"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)
def read_ticker_from_url(pathname):
    """
    Read the ticker symbol from the URL path.
    e.g., /AAPL -> sets ticker input to 'AAPL' and signals auto-fetch.
    """
    if not pathname or pathname == "/":
        return "", None

    # Strip leading slash and any trailing slashes
    ticker = pathname.strip("/").upper()

    # Basic validation: only letters, max 5 chars
    if ticker.isalpha() and 1 <= len(ticker) <= 5:
        return ticker, {"ticker": ticker, "auto_fetch": True}

    return "", None

# =============================================================================
# CHAIN LINK 1: MASTER DATA FETCH
# =============================================================================
@callback(
    Output("ticker-data-store", "data"),
    Output("error-store", "data"),
    Output("submit-button", "disabled"),
    Output("submit-button", "children"),
    Input("submit-button", "n_clicks"),
    Input("ticker-input", "n_submit"),
    Input("url-trigger-store", "data"),
    State("ticker-input", "value"),
    State("chart-period-store", "data"),
    State("chart-interval-store", "data"),
    prevent_initial_call=True,
)
def master_fetch_callback(n_clicks, n_submit, url_trigger, ticker_symbol, period, interval):
    """Chain Link 1: Master fetch — triggered by button, Enter key, or URL navigation."""
    triggered_id = ctx.triggered_id

    # If triggered by URL but no valid ticker in the trigger, do nothing
    if triggered_id == "url-trigger-store":
        if not url_trigger or not url_trigger.get("auto_fetch"):
            return no_update, no_update, no_update, no_update

    if not ticker_symbol or ticker_symbol.strip() == "":
        # Only show error if user explicitly clicked button or pressed Enter
        if triggered_id in ("submit-button", "ticker-input"):
            return no_update, {"error": "Please enter a ticker symbol."}, False, "Fetch Data"
        return no_update, no_update, no_update, no_update

    ticker_symbol = ticker_symbol.strip().upper()
    period = period or "5y"
    interval = interval or "1wk"

    all_data = fetch_all_data(ticker_symbol, period=period, interval=interval)

    if not all_data.get("success"):
        return (
            no_update,
            {"error": all_data.get("error", "Unknown error occurred.")},
            False,
            "Fetch Data",
        )

    # Measure payload size
    #payload_json = json.dumps(all_data)
    #payload_size_kb = len(payload_json.encode('utf-8')) / 1024
    #print(f"  dcc.Store payload: {payload_size_kb:.1f} KB")

    return all_data, None, False, "Fetch Data"

# =============================================================================
# CHART PERIOD BUTTON CALLBACK
# =============================================================================
@callback(
    Output("chart-period-store", "data"),
    *[Output(btn_id, "color") for btn_id in ALL_PERIOD_IDS],
    *[Input(btn_id, "n_clicks") for btn_id in ALL_PERIOD_IDS],
    State("chart-period-store", "data"),
    prevent_initial_call=True,
)
def update_period_selection(*args):
    """Update period store and highlight active period button."""
    current_period = args[-1]
    triggered_id = ctx.triggered_id

    if triggered_id and triggered_id in PERIOD_BUTTON_MAP:
        new_period = PERIOD_BUTTON_MAP[triggered_id]
    else:
        new_period = current_period or "5y"

    colors = []
    for btn_id in ALL_PERIOD_IDS:
        if PERIOD_BUTTON_MAP[btn_id] == new_period:
            colors.append("light")
        else:
            colors.append("outline-light")

    return (new_period, *colors)


# =============================================================================
# CHART INTERVAL BUTTON CALLBACK
# =============================================================================
@callback(
    Output("chart-interval-store", "data"),
    *[Output(btn_id, "color") for btn_id in ALL_INTERVAL_IDS],
    *[Input(btn_id, "n_clicks") for btn_id in ALL_INTERVAL_IDS],
    State("chart-interval-store", "data"),
    prevent_initial_call=True,
)
def update_interval_selection(*args):
    """Update interval store and highlight active interval button."""
    current_interval = args[-1]
    triggered_id = ctx.triggered_id

    if triggered_id and triggered_id in INTERVAL_BUTTON_MAP:
        new_interval = INTERVAL_BUTTON_MAP[triggered_id]
    else:
        new_interval = current_interval or "1wk"

    colors = []
    for btn_id in ALL_INTERVAL_IDS:
        if INTERVAL_BUTTON_MAP[btn_id] == new_interval:
            colors.append("secondary")
        else:
            colors.append("outline-secondary")

    return (new_interval, *colors)


# =============================================================================
# CHART UPDATE CALLBACK
# =============================================================================
@callback(
    Output("candlestick-chart", "figure"),
    Input("ticker-data-store", "data"),
    Input("chart-period-store", "data"),
    Input("chart-interval-store", "data"),
    prevent_initial_call=True,
)
def update_chart(all_data, period, interval):
    """Build the candlestick chart. Re-fetches historical data if period/interval changed."""
    #start = time.time()
    if not all_data:
        return _empty_chart()

    ticker = all_data.get("ticker", "")
    period = period or "5y"
    interval = interval or "1wk"

    triggered_id = ctx.triggered_id

    if triggered_id in ("chart-period-store", "chart-interval-store"):
        historical = fetch_historical_data(ticker, period=period, interval=interval)
    else:
        historical = all_data.get("historical", {})
        stored_period = historical.get("period", "5y")
        stored_interval = historical.get("interval", "1wk")
        if stored_period != period or stored_interval != interval:
            historical = fetch_historical_data(ticker, period=period, interval=interval)
    result = build_candlestick_chart(historical, ticker, period, interval)
    #print(f"Chart updated in {time.time() - start:.3f} seconds")
    return result


def _empty_chart():
    """Return an empty placeholder chart."""
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#222",
        plot_bgcolor="#222",
        height=400,
        margin=dict(l=50, r=20, t=35, b=25),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="Enter a ticker and click Fetch Data",
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=14, color="#888"),
                x=0.5, y=0.5,
            )
        ],
    )
    return fig


# =============================================================================
# CHAIN LINK 2: ERROR ALERT
# =============================================================================
@callback(
    Output("error-alert", "children"),
    Output("error-alert", "is_open"),
    Input("error-store", "data"),
    prevent_initial_call=True,
)
def display_error(error_data):
    """Display or clear error messages."""
    if error_data and error_data.get("error"):
        return error_data["error"], True
    return "", False


# =============================================================================
# CHAIN LINK 3: COMPANY INFO SIDEBAR (left of chart)
# =============================================================================
@callback(
    Output("company-sidebar-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_company_sidebar(all_data):
    """Update the company info sidebar to the left of the chart."""
    if not all_data:
        return no_update

    return build_company_info_sidebar(all_data.get("profile"), all_data)


# =============================================================================
# CHAIN LINK 4: ANALYST RECOMMENDATION CHART (right of chart)
# =============================================================================
@callback(
    Output("analyst-rec-chart", "figure"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_analyst_rec_chart(all_data):
    """Update the analyst recommendation stacked bar chart."""
    if not all_data:
        return _empty_small_chart()

    return build_analyst_recommendation_chart(all_data.get("analyst"))


def _empty_small_chart():
    """Return an empty small placeholder chart."""
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#222",
        plot_bgcolor="#222",
        height=340,
        margin=dict(l=10, r=10, t=30, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


# =============================================================================
# CHAIN LINK 5: HIGH PREMIUM OPTIONS (top of page)
# =============================================================================
@callback(
    Output("high-premium-options-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_high_premium_options(all_data):
    """Update the high premium options section at the top of the page."""
    if not all_data:
        return no_update

    return build_high_premium_options_section(all_data.get("options"))


# =============================================================================
# CHAIN LINK 6: COMPANY DESCRIPTION (always visible)
# =============================================================================
@callback(
    Output("company-description-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_company_description(all_data):
    """Update company description card."""
    if not all_data:
        return no_update

    return build_company_description(all_data.get("profile"))


# =============================================================================
# CHAIN LINK 7: ANALYST RATINGS (always visible)
# =============================================================================
@callback(
    Output("analyst-ratings-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_analyst_ratings(all_data):
    """Update analyst ratings section."""
    if not all_data:
        return no_update

    return build_analyst_ratings_section(all_data.get("analyst"))


# =============================================================================
# CHAIN LINK 8: FILTERED OPTIONS CHAIN (always visible)
# =============================================================================
@callback(
    Output("filtered-options-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_filtered_options(all_data):
    """Update filtered options chain section."""
    if not all_data:
        return no_update

    return build_filtered_options_section(all_data.get("options"))


# =============================================================================
# CHAIN LINK 9: FULL OPTIONS CHAIN (tabbed)
# =============================================================================
@callback(
    Output("full-options-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_full_options(all_data):
    """Update full unfiltered options chain tab."""
    if not all_data:
        return no_update

    return build_unfiltered_options_section(all_data.get("options"))


# =============================================================================
# CHAIN LINK 10: FULL COMPANY PROFILE (tabbed)
# =============================================================================
@callback(
    Output("full-profile-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_full_profile(all_data):
    """Update full company profile tab."""
    if not all_data:
        return no_update

    return build_full_company_profile(all_data.get("profile"))


# =============================================================================
# CHAIN LINK 11: EARNINGS (tabbed)
# =============================================================================
@callback(
    Output("earnings-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_earnings(all_data):
    """Update earnings tab."""
    if not all_data:
        return no_update

    return build_earnings_section(all_data.get("earnings"))


# =============================================================================
# CHAIN LINK 12: DIVIDENDS (tabbed)
# =============================================================================
@callback(
    Output("dividends-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_dividends(all_data):
    """Update dividends tab."""
    if not all_data:
        return no_update

    return build_dividends_section(all_data.get("dividends"))


# =============================================================================
# CHAIN LINK 13: FINANCIALS (tabbed)
# =============================================================================
@callback(
    Output("financials-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_financials(all_data):
    """Update financials tab."""
    if not all_data:
        return no_update

    return build_financials_section(all_data.get("financials"))


# =============================================================================
# CHAIN LINK 14: INSIDER TRANSACTIONS (tabbed)
# =============================================================================
@callback(
    Output("insider-content", "children"),
    Input("ticker-data-store", "data"),
    prevent_initial_call=True,
)
def update_insider(all_data):
    """Update insider transactions tab."""
    if not all_data:
        return no_update

    return build_insider_section(all_data.get("insider"))


# =============================================================================
# RUN THE APP
# =============================================================================
# Expose the Flask server for gunicorn
server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8050)
