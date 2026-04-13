import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def build_candlestick_chart(historical_data, ticker_symbol, period, interval):
    """
    Build an interactive Plotly candlestick chart with Bollinger Bands overlay
    and a volume bar chart subplot underneath.
    """
    if not historical_data or not historical_data.get("success"):
        return _build_error_figure(
            historical_data.get("error", "No historical data available.")
            if historical_data
            else "No historical data available."
        )

    records = historical_data.get("data", [])
    if not records:
        return _build_error_figure("No historical data records found.")

    df = pd.DataFrame(records)
    # Ensure Date is datetime
    df["Date"] = pd.to_datetime(df["Date"])

    # Helper: convert period string to pandas DateOffset (approximate)
    def _period_to_offset(p):
        if p == "1d":
            return pd.DateOffset(days=1)
        if p == "5d":
            return pd.DateOffset(days=5)
        if p == "1mo":
            return pd.DateOffset(months=1)
        if p == "3mo":
            return pd.DateOffset(months=3)
        if p == "6mo":
            return pd.DateOffset(months=6)
        if p == "1y":
            return pd.DateOffset(years=1)
        if p == "2y":
            return pd.DateOffset(years=2)
        if p == "5y":
            return pd.DateOffset(years=5)
        if p == "10y":
            return pd.DateOffset(years=10)
        return None

    visible_end = df["Date"].max()
    period_offset = _period_to_offset(period)
    if period_offset is not None:
        visible_start = visible_end - period_offset
    else:
        visible_start = df["Date"].min()

    visible_mask = df["Date"] >= visible_start
    df_visible = df.loc[visible_mask].copy()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
        subplot_titles=None,
    )

    # Vertical wick overlay drawn as separate thin grey lines (use None separators)
    wick_x = []
    wick_y = []
    for _, r in df_visible.iterrows():
        wick_x.extend([r["Date"], r["Date"], None])
        wick_y.extend([r["Low"], r["High"], None])

    # Build wick segments only where wick extends beyond the candle body
    wick_x = []
    wick_y = []
    for _, r in df_visible.iterrows():
        top_body = max(r["Open"], r["Close"])
        bottom_body = min(r["Open"], r["Close"])
        # upper wick (top of body -> high)
        if r["High"] > top_body:
            wick_x.extend([r["Date"], r["Date"], None])
            wick_y.extend([top_body, r["High"], None])
        # lower wick (low -> bottom of body)
        if r["Low"] < bottom_body:
            wick_x.extend([r["Date"], r["Date"], None])
            wick_y.extend([r["Low"], bottom_body, None])

    # Draw wick lines (only the portions outside the candle body)
    fig.add_trace(
        go.Scatter(
            x=wick_x,
            y=wick_y,
            mode="lines",
            line=dict(color="#bdbdbd", width=1),
            showlegend=False,
            hoverinfo="skip",
        ),
        row=1,
        col=1,
    )

    # Draw candlestick bodies with transparent line color so they don't draw their own wicks
    fig.add_trace(
        go.Candlestick(
            x=df_visible["Date"],
            open=df_visible["Open"],
            high=df_visible["High"],
            low=df_visible["Low"],
            close=df_visible["Close"],
            name="OHLC",
            increasing_line_color="rgba(0,0,0,0)",
            increasing_fillcolor="#26a69a",
            decreasing_line_color="rgba(0,0,0,0)",
            decreasing_fillcolor="#ef5350",
            whiskerwidth=0,
        ),
        row=1,
        col=1,
    )

    bb_df = df.dropna(subset=["SMA", "Upper_BB", "Lower_BB"])
    # Only plot BB lines for the visible range but compute using padded data (bb_df is from full df)
    if not bb_df.empty:
        bb_visible = bb_df.loc[bb_df["Date"] >= visible_start]
        if not bb_visible.empty:
            fig.add_trace(
                go.Scatter(
                    x=bb_visible["Date"],
                    y=bb_visible["SMA"],
                    name="SMA (20)",
                    line=dict(color="#2196F3", width=1.2),
                    hovertemplate="SMA: %{y:.2f}<extra></extra>",
                ),
                row=1,
                col=1,
            )

            fig.add_trace(
                go.Scatter(
                    x=bb_visible["Date"],
                    y=bb_visible["Upper_BB"],
                    name="Upper BB (+2σ)",
                    line=dict(color="#FF9800", width=1),
                    hovertemplate="Upper BB: %{y:.2f}<extra></extra>",
                ),
                row=1,
                col=1,
            )

            fig.add_trace(
                go.Scatter(
                    x=bb_visible["Date"],
                    y=bb_visible["Lower_BB"],
                    name="Lower BB (−2σ)",
                    line=dict(color="#FF9800", width=1),
                    fill="tonexty",
                    fillcolor="rgba(255, 152, 0, 0.08)",
                    hovertemplate="Lower BB: %{y:.2f}<extra></extra>",
                ),
                row=1,
                col=1,
            )

    volume_colors = [
        "#26a69a" if row["Close"] >= row["Open"] else "#ef5350"
        for _, row in df_visible.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=df_visible["Date"],
            y=df_visible["Volume"],
            name="Volume",
            marker_color=volume_colors,
            opacity=0.7,
            hovertemplate="Volume: %{y:,.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Earnings markers: use earnings_dates from the historical payload if available
    earnings = historical_data.get("earnings_dates") or []

    def _extract_date(rec):
        # Try common keys or parse any value that looks like a date
        for k, v in rec.items():
            try:
                dt = pd.to_datetime(v, errors="coerce")
                if not pd.isna(dt):
                    return dt
            except Exception:
                continue
        return None

    if earnings:
        # Compute placement: slightly below visible low
        try:
            vis_low = df_visible["Low"].min()
            vis_high = df_visible["High"].max()
            price_range = max(1e-6, vis_high - vis_low)
            marker_y = vis_low - 0.02 * price_range
        except Exception:
            marker_y = None

        for rec in earnings:
            ed = _extract_date(rec)
            if ed is None:
                continue
            # if ed is within visible range, add marker
            if ed >= visible_start and ed <= visible_end:
                hover = []
                for k, v in rec.items():
                    hover.append(f"{k}: {v}")
                hovertext = "<br>".join(hover)
                y_val = marker_y if marker_y is not None else df_visible["Low"].min()
                fig.add_trace(
                    go.Scatter(
                        x=[ed],
                        y=[y_val],
                        mode="markers",
                        marker=dict(symbol="triangle-down", size=10, color="#ffb74d"),
                        name="Earnings",
                        hoverinfo="text",
                        hovertext=hovertext,
                        showlegend=False,
                    ),
                    row=1,
                    col=1,
                )

    interval_labels = {
        "1m": "1 Min", "2m": "2 Min", "5m": "5 Min", "15m": "15 Min",
        "30m": "30 Min", "60m": "1 Hour", "1h": "1 Hour", "90m": "90 Min",
        "1d": "Daily", "5d": "5 Day", "1wk": "Weekly", "1mo": "Monthly", "3mo": "Quarterly",
    }
    period_labels = {
        "1d": "1 Day", "5d": "5 Days", "1mo": "1 Month", "3mo": "3 Months",
        "6mo": "6 Months", "1y": "1 Year", "2y": "2 Years", "5y": "5 Years",
        "10y": "10 Years", "ytd": "YTD", "max": "Max",
    }

    interval_label = interval_labels.get(interval, interval)
    period_label = period_labels.get(period, period)

    fig.update_layout(
        title=dict(
            text=f"{ticker_symbol} · {interval_label} · {period_label} · BB(20,2)",
            font=dict(size=12),
            x=0.5,
            xanchor="center",
            y=0.98,
        ),
        template="plotly_dark",
        paper_bgcolor="#222",
        plot_bgcolor="#222",
        height=380,
        margin=dict(l=45, r=10, t=30, b=20),
        showlegend=False,
        hovermode="closest",
        xaxis_rangeslider_visible=False,
    )

    # Enable solid spikes for crosshair (both axes)
    fig.update_yaxes(title_text="Price", title_font_size=10, tickfont_size=9, row=1, col=1, gridcolor="#333", showspikes=True, spikecolor="#888", spikethickness=1, spikedash="solid", spikemode="across", spikesnap='cursor')
    fig.update_yaxes(title_text="Vol", title_font_size=9, tickfont_size=8, row=2, col=1, gridcolor="#333", showspikes=True, spikecolor="#888", spikethickness=1, spikedash="solid", spikemode="across", spikesnap='cursor')
    fig.update_xaxes(gridcolor="#333", tickfont_size=9, row=1, col=1, showspikes=True, spikecolor="#888", spikethickness=1, spikedash="solid", spikemode="across", spikesnap='cursor')
    fig.update_xaxes(gridcolor="#333", tickfont_size=9, row=2, col=1, showspikes=True, spikecolor="#888", spikethickness=1, spikedash="solid", spikemode="across", spikesnap='cursor')

    return fig


def build_analyst_recommendation_chart(analyst_data):
    """
    Build a stacked bar chart showing analyst recommendations for the last 3 months.
    Similar to Yahoo Finance's recommendation trends chart.
    Returns a Plotly figure.
    """
    if not analyst_data or not analyst_data.get("success"):
        return _build_small_error_figure("No analyst data")

    data = analyst_data.get("data", {})
    recs = data.get("recommendations")

    if not recs or len(recs) == 0:
        return _build_small_error_figure("No recommendations")

    rec_df = pd.DataFrame(recs)

    # yfinance recommendations typically have columns:
    # period, strongBuy, buy, hold, sell, strongSell
    expected_cols = ["strongBuy", "buy", "hold", "sell", "strongSell"]
    if not all(col in rec_df.columns for col in expected_cols):
        return _build_small_error_figure("Unexpected data format")

    # Take last 3 months of data
    rec_df = rec_df.head(3).iloc[::-1]  # Reverse so oldest is on left

    # Build period labels
    if "period" in rec_df.columns:
        labels = rec_df["period"].tolist()
    else:
        labels = [f"Month {i+1}" for i in range(len(rec_df))]

    fig = go.Figure()

    # Stacked bars: Strong Buy (bottom) → Strong Sell (top)
    bar_config = [
        ("strongBuy", "Strong Buy", "#00897b"),
        ("buy", "Buy", "#26a69a"),
        ("hold", "Hold", "#ffa726"),
        ("sell", "Sell", "#ef5350"),
        ("strongSell", "Strong Sell", "#b71c1c"),
    ]

    for col, name, color in bar_config:
        values = rec_df[col].tolist()
        fig.add_trace(
            go.Bar(
                x=labels,
                y=values,
                name=name,
                marker_color=color,
                text=values,
                textposition="inside",
                textfont_size=10,
                hovertemplate=f"{name}: %{{y}}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        template="plotly_dark",
        paper_bgcolor="#222",
        plot_bgcolor="#222",
        height=340,
        margin=dict(l=10, r=10, t=30, b=20),
        title=dict(
            text="Analyst Recs (3M)",
            font=dict(size=11),
            x=0.5,
            xanchor="center",
            y=0.97,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=8),
        ),
        xaxis=dict(tickfont_size=9),
        yaxis=dict(visible=False),
    )

    return fig


def _build_error_figure(error_message):
    """Build a placeholder figure displaying an error message."""
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#222",
        plot_bgcolor="#222",
        height=380,
        margin=dict(l=45, r=10, t=30, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=error_message,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14, color="#ef5350"),
                x=0.5,
                y=0.5,
            )
        ],
    )
    return fig


def _build_small_error_figure(error_message):
    """Build a small placeholder figure for the analyst chart."""
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#222",
        plot_bgcolor="#222",
        height=340,
        margin=dict(l=10, r=10, t=30, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=error_message,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=12, color="#888"),
                x=0.5,
                y=0.5,
            )
        ],
    )
    return fig
