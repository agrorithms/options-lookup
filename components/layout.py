import dash_bootstrap_components as dbc
from dash import html, dcc
from typing import Literal


def _loading_wrapper(
    component_id: str,
    children,
    spinner_type: Literal["graph", "cube", "circle", "dot", "default"] = "circle",
    color: str = "#375a7f",
):
    """Wrap a component in a dcc.Loading spinner."""
    return dcc.Loading(
        id=f"{component_id}-loading",
        type=spinner_type,
        color=color,
        children=children,
        overlay_style={"visibility": "visible", "opacity": 0.3},
        custom_spinner=None,
    )


def create_layout():
    """Build the full page layout."""

    # --- HEADER ---
    header = dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("📈 Stock Dashboard", className="fs-3 fw-bold"),
                html.Span("Powered by Yahoo Finance & Plotly", className="text-muted small"),
            ],
            fluid=True,
            className="d-flex justify-content-between align-items-center",
        ),
        color="dark",
        dark=True,
        className="mb-3",
    )

    # --- INPUT CONTROLS ---
    input_controls = dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Ticker Symbol", className="fw-bold"),
                            dbc.Input(
                                id="ticker-input",
                                type="text",
                                placeholder="e.g. AAPL",
                                value="",
                                className="text-uppercase",
                            ),
                        ],
                        md=9,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("\u00A0", className="fw-bold"),
                            dbc.Button(
                                "Fetch Data",
                                id="submit-button",
                                color="primary",
                                className="w-100",
                                n_clicks=0,
                            ),
                        ],
                        md=3,
                        className="d-flex flex-column",
                    ),
                ],
                className="g-3",
            )
        ),
        className="mb-3",
    )

    # --- ERROR ALERT ---
    error_alert = dbc.Alert(
        id="error-alert",
        is_open=False,
        dismissable=True,
        color="danger",
        className="mb-3",
    )

    # --- HIGH PREMIUM OPTIONS (top of page) ---
    high_premium_options = _loading_wrapper(
        "high-premium-options",
        html.Div(id="high-premium-options-content"),
        spinner_type="circle",
        color="#ff9800",
    )

    # --- CHART PERIOD/INTERVAL BUTTONS ---
    chart_period_buttons = dbc.ButtonGroup(
        [
            dbc.Button("1D", id="period-1d", color="outline-light", size="sm", n_clicks=0),
            dbc.Button("5D", id="period-5d", color="outline-light", size="sm", n_clicks=0),
            dbc.Button("1M", id="period-1mo", color="outline-light", size="sm", n_clicks=0),
            dbc.Button("6M", id="period-6mo", color="outline-light", size="sm", n_clicks=0),
            dbc.Button("YTD", id="period-ytd", color="outline-light", size="sm", n_clicks=0),
            dbc.Button("1Y", id="period-1y", color="outline-light", size="sm", n_clicks=0),
            dbc.Button("5Y", id="period-5y", color="light", size="sm", n_clicks=0),
            dbc.Button("MAX", id="period-max", color="outline-light", size="sm", n_clicks=0),
        ],
        className="me-3",
    )

    chart_interval_buttons = dbc.ButtonGroup(
        [
            dbc.Button("1m", id="interval-1m", color="outline-secondary", size="sm", n_clicks=0),
            dbc.Button("5m", id="interval-5m", color="outline-secondary", size="sm", n_clicks=0),
            dbc.Button("15m", id="interval-15m", color="outline-secondary", size="sm", n_clicks=0),
            dbc.Button("30m", id="interval-30m", color="outline-secondary", size="sm", n_clicks=0),
            dbc.Button("1h", id="interval-1h", color="outline-secondary", size="sm", n_clicks=0),
            dbc.Button("1D", id="interval-1d", color="outline-secondary", size="sm", n_clicks=0),
            dbc.Button("1W", id="interval-1wk", color="secondary", size="sm", n_clicks=0),
            dbc.Button("1M", id="interval-1mo", color="outline-secondary", size="sm", n_clicks=0),
        ],
    )

    chart_controls = html.Div(
        [
            html.Div(
                [
                    html.Span("Period: ", className="text-muted small me-1"),
                    chart_period_buttons,
                ],
                className="d-flex align-items-center me-3 mb-1",
            ),
            html.Div(
                [
                    html.Span("Interval: ", className="text-muted small me-1"),
                    chart_interval_buttons,
                ],
                className="d-flex align-items-center mb-1",
            ),
        ],
        className="d-flex flex-wrap mb-2",
    )

    chart_state_stores = html.Div(
        [
            dcc.Store(id="chart-period-store", data="5y", storage_type="memory"),
            dcc.Store(id="chart-interval-store", data="1wk", storage_type="memory"),
        ]
    )

    # --- THREE-COLUMN CHART ROW: Info Sidebar | Chart | Analyst Recs ---
    chart_row = dbc.Card(
        dbc.CardBody(
            [
                chart_controls,
                chart_state_stores,
                dbc.Row(
                    [
                        # LEFT: Company info sidebar
                        dbc.Col(
                            _loading_wrapper(
                                "company-sidebar",
                                html.Div(
                                    id="company-sidebar-content",
                                    style={
                                        "maxHeight": "400px",
                                        "overflowY": "auto",
                                    },
                                ),
                                spinner_type="dot",
                                color="#26a69a",
                            ),
                            lg=2,
                            md=12,
                            className="border-end border-secondary",
                        ),
                        # CENTER: Candlestick chart
                        dbc.Col(
                            _loading_wrapper(
                                "chart",
                                dcc.Graph(
                                    id="candlestick-chart",
                                    config={"displayModeBar": True, "scrollZoom": True},
                                    style={"height": "400px"},
                                ),
                                spinner_type="graph",
                                color="#375a7f",
                            ),
                            lg=7,
                            md=12,
                        ),
                        # RIGHT: Analyst recommendation stacked bar chart
                        dbc.Col(
                            _loading_wrapper(
                                "analyst-chart",
                                dcc.Graph(
                                    id="analyst-rec-chart",
                                    config={"displayModeBar": False},
                                    style={"height": "400px"},
                                ),
                                spinner_type="circle",
                                color="#ffd54f",
                            ),
                            lg=3,
                            md=12,
                        ),
                    ],
                    className="g-0",
                ),
            ]
        ),
        className="mb-3",
    )

        # --- COMPANY DESCRIPTION (always visible) ---
    company_description = _loading_wrapper(
        "description",
        html.Div(id="company-description-content"),
        spinner_type="dot",
        color="#26a69a",
    )

    # --- ANALYST RATINGS (always visible) ---
    analyst_section = _loading_wrapper(
        "analyst",
        html.Div(id="analyst-ratings-content"),
        spinner_type="circle",
        color="#ffd54f",
    )

    # --- FILTERED OPTIONS CHAIN (always visible) ---
    filtered_options = _loading_wrapper(
        "filtered-options",
        html.Div(id="filtered-options-content"),
        spinner_type="circle",
        color="#ff9800",
    )

    # --- TABBED DETAIL SECTIONS ---
    detail_tabs = dbc.Card(
        dbc.CardBody(
            dbc.Tabs(
                [
                    dbc.Tab(
                        _loading_wrapper(
                            "full-options",
                            html.Div(id="full-options-content"),
                            spinner_type="circle",
                            color="#ff9800",
                        ),
                        label="Full Options Chain",
                        tab_id="tab-full-options",
                    ),
                    dbc.Tab(
                        _loading_wrapper(
                            "full-profile",
                            html.Div(id="full-profile-content"),
                            spinner_type="dot",
                            color="#26a69a",
                        ),
                        label="Full Company Profile",
                        tab_id="tab-full-profile",
                    ),
                    dbc.Tab(
                        _loading_wrapper(
                            "earnings",
                            html.Div(id="earnings-content"),
                            spinner_type="circle",
                            color="#64b5f6",
                        ),
                        label="Earnings",
                        tab_id="tab-earnings",
                    ),
                    dbc.Tab(
                        _loading_wrapper(
                            "dividends",
                            html.Div(id="dividends-content"),
                            spinner_type="circle",
                            color="#81c784",
                        ),
                        label="Dividends",
                        tab_id="tab-dividends",
                    ),
                    dbc.Tab(
                        _loading_wrapper(
                            "financials",
                            html.Div(id="financials-content"),
                            spinner_type="circle",
                            color="#ce93d8",
                        ),
                        label="Financials",
                        tab_id="tab-financials",
                    ),
                    dbc.Tab(
                        _loading_wrapper(
                            "insider",
                            html.Div(id="insider-content"),
                            spinner_type="circle",
                            color="#ef5350",
                        ),
                        label="Insider Transactions",
                        tab_id="tab-insider",
                    ),
                ],
                id="detail-tabs",
                active_tab="tab-full-options",
            )
        ),
        className="mb-3",
    )

      # --- DATA STORES ---
    data_stores = html.Div(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="ticker-data-store", storage_type="memory"),
            dcc.Store(id="error-store", storage_type="memory"),
            dcc.Store(id="url-trigger-store", storage_type="memory"),
        ]
    )

    # --- ASSEMBLE FULL LAYOUT ---
    layout = dbc.Container(
        [
            header,
            input_controls,
            error_alert,
            high_premium_options,
            chart_row,
            company_description,
            analyst_section,
            filtered_options,
            detail_tabs,
            data_stores,
        ],
        fluid=True,
        className="px-4 pb-4",
    )

    return layout
