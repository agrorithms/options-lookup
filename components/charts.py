import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


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
    df["Date"] = pd.to_datetime(df["Date"])

    # -----------------------------------------------------------------
    # Compute visible date range
    # -----------------------------------------------------------------
    def _period_to_offset(p):
        offsets = {
            "1d": pd.DateOffset(days=1),
            "5d": pd.DateOffset(days=5),
            "1mo": pd.DateOffset(months=1),
            "3mo": pd.DateOffset(months=3),
            "6mo": pd.DateOffset(months=6),
            "1y": pd.DateOffset(years=1),
            "2y": pd.DateOffset(years=2),
            "5y": pd.DateOffset(years=5),
            "10y": pd.DateOffset(years=10),
        }
        return offsets.get(p)

    visible_end = df["Date"].max()
    period_offset = _period_to_offset(period)
    visible_start = (visible_end - period_offset) if period_offset else df["Date"].min()

    df_visible = df.loc[df["Date"] >= visible_start].copy()

    # -----------------------------------------------------------------
    # Downsampling: only for very large datasets, and more generous limit
    # 1260 candles (5Y daily) renders fine; only cap extreme cases
    # -----------------------------------------------------------------
    max_candles = 1500
    if len(df_visible) > max_candles:
        step = len(df_visible) // max_candles + 1
        df_visible = df_visible.iloc[::step].reset_index(drop=True)

    # -----------------------------------------------------------------
    # Extract numpy arrays once
    # -----------------------------------------------------------------
    dates = df_visible["Date"].values
    opens = df_visible["Open"].values
    highs = df_visible["High"].values
    lows = df_visible["Low"].values
    closes = df_visible["Close"].values
    volumes = df_visible["Volume"].values

    # -----------------------------------------------------------------
    # Vectorized volume colors
    # -----------------------------------------------------------------
    volume_colors = np.where(closes >= opens, "#26a69a", "#ef5350").tolist()

    # -----------------------------------------------------------------
    # Build figure
    # -----------------------------------------------------------------
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.85, 0.15],
    )

    # -----------------------------------------------------------------
    # Candlestick bodies FIRST (transparent wicks)
    # Drawing this first establishes the x-position for each date.
    # -----------------------------------------------------------------
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
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

    # -----------------------------------------------------------------
    # Grey wick lines AFTER candlestick, using the SAME date values
    # This ensures perfect x-alignment since both traces share
    # identical x-coordinates from the same numpy array.
    # -----------------------------------------------------------------
    top_body = np.maximum(opens, closes)
    bottom_body = np.minimum(opens, closes)

    # Build all wick segments in one pass using numpy
    # Each wick needs: [date, date, None] for x and [start, end, None] for y
    upper_mask = highs > top_body
    lower_mask = lows < bottom_body

    wick_x = []
    wick_y = []

    # Upper wicks
    if upper_mask.any():
        u_dates = dates[upper_mask]
        u_tops = top_body[upper_mask]
        u_highs = highs[upper_mask]
        for i in range(len(u_dates)):
            wick_x.extend([u_dates[i], u_dates[i], None])
            wick_y.extend([u_tops[i], u_highs[i], None])

    # Lower wicks
    if lower_mask.any():
        l_dates = dates[lower_mask]
        l_bottoms = bottom_body[lower_mask]
        l_lows = lows[lower_mask]
        for i in range(len(l_dates)):
            wick_x.extend([l_dates[i], l_dates[i], None])
            wick_y.extend([l_lows[i], l_bottoms[i], None])

    if wick_x:
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

    # -----------------------------------------------------------------
    # Bollinger Bands — go.Scatter (SVG) for rangebreaks compatibility
    # -----------------------------------------------------------------
    bb_mask = df["SMA"].notna() & df["Upper_BB"].notna() & df["Lower_BB"].notna()
    bb_mask = bb_mask & (df["Date"] >= visible_start)
    if bb_mask.any():
        bb_dates = df.loc[bb_mask, "Date"].values
        bb_sma = df.loc[bb_mask, "SMA"].values
        bb_upper = df.loc[bb_mask, "Upper_BB"].values
        bb_lower = df.loc[bb_mask, "Lower_BB"].values

        fig.add_trace(
            go.Scatter(
                x=bb_dates, y=bb_upper,
                name="Upper BB",
                mode="lines",
                line=dict(color="#FF9800", width=1),
                hovertemplate="Upper BB: %{y:$.2f}<extra></extra>",
            ),
            row=1, col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=bb_dates, y=bb_lower,
                name="Lower BB",
                mode="lines",
                line=dict(color="#FF9800", width=1),
                fill="tonexty",
                fillcolor="rgba(255, 152, 0, 0.08)",
                hovertemplate="Lower BB: %{y:$.2f}<extra></extra>",
            ),
            row=1, col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=bb_dates, y=bb_sma,
                name="SMA (20)",
                mode="lines",
                line=dict(color="#2196F3", width=1.2),
                hovertemplate="SMA(20): %{y:$.2f}<extra></extra>",
            ),
            row=1, col=1,
        )

    # -----------------------------------------------------------------
    # Volume bars
    # -----------------------------------------------------------------
    fig.add_trace(
        go.Bar(
            x=dates,
            y=volumes,
            name="Volume",
            marker_color=volume_colors,
            opacity=0.7,
            hovertemplate="Vol: %{y:,.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # -----------------------------------------------------------------
    # Earnings markers — batched into single trace
    # -----------------------------------------------------------------
    earnings = historical_data.get("earnings_dates") or []
    if earnings:
        vis_low = lows.min()
        vis_high = highs.max()
        price_range = max(1e-6, vis_high - vis_low)
        marker_y_val = vis_low - 0.02 * price_range

        earnings_x = []
        earnings_y = []
        earnings_hover = []

        for rec in earnings:
            ed = _extract_earnings_date(rec)
            if ed is None:
                continue
            if ed >= visible_start and ed <= visible_end:
                earnings_x.append(ed)
                earnings_y.append(marker_y_val)
                hover_parts = [f"{k}: {v}" for k, v in rec.items()]
                earnings_hover.append("<br>".join(hover_parts))

        if earnings_x:
            fig.add_trace(
                go.Scatter(
                    x=earnings_x,
                    y=earnings_y,
                    mode="markers",
                    marker=dict(symbol="triangle-down", size=10, color="#ffb74d"),
                    name="Earnings",
                    hoverinfo="text",
                    hovertext=earnings_hover,
                    showlegend=False,
                ),
                row=1,
                col=1,
            )

    # -----------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------
    interval_labels = {
        "1m": "1 Min", "2m": "2 Min", "5m": "5 Min", "15m": "15 Min",
        "30m": "30 Min", "60m": "1 Hour", "1h": "1 Hour", "90m": "90 Min",
        "1d": "Daily", "5d": "5 Day", "1wk": "Weekly", "1mo": "Monthly",
        "3mo": "Quarterly",
    }
    period_labels = {
        "1d": "1 Day", "5d": "5 Days", "1mo": "1 Month", "3mo": "3 Months",
        "6mo": "6 Months", "1y": "1 Year", "2y": "2 Years", "5y": "5 Years",
        "10y": "10 Years", "ytd": "YTD", "max": "Max",
    }

    fig.update_layout(
        title=dict(
            text=f"{ticker_symbol} · {interval_labels.get(interval, interval)} · {period_labels.get(period, period)} · BB(20,2)",
            font=dict(size=12),
            x=0.5, xanchor="center", y=0.98,
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

    # Spike crosshair config
    spike_config = dict(
        showspikes=True, spikecolor="#888", spikethickness=1,
        spikedash="solid", spikemode="across", spikesnap="cursor",
    )

    # Weekend breaks — only apply for daily or sub-daily intervals
    # Weekly and monthly candles don't have weekend gaps
    intraday_or_daily = interval in ("1m", "2m", "5m", "15m", "30m", "60m", "1h", "90m", "1d")
    weekend_breaks = {}
    if intraday_or_daily:
        weekend_breaks = dict(
            rangebreaks=[
                dict(bounds=["sat", "mon"]),
            ]
        )

    fig.update_yaxes(
        title_text="Price", title_font_size=10, tickfont_size=9,
        gridcolor="#333", row=1, col=1, **spike_config,
    )
    fig.update_yaxes(
        title_text="Vol", title_font_size=9, tickfont_size=8,
        gridcolor="#333", row=2, col=1, **spike_config,
    )
    fig.update_xaxes(
        gridcolor="#333", tickfont_size=9,
        row=1, col=1, **spike_config, **weekend_breaks,
    )
    fig.update_xaxes(
        gridcolor="#333", tickfont_size=9,
        row=2, col=1, **spike_config, **weekend_breaks,
    )

    return fig



def _extract_earnings_date(rec):
    """Extract a datetime from an earnings record by trying all values."""
    for k, v in rec.items():
        try:
            dt = pd.to_datetime(v, errors="coerce")
            if not pd.isna(dt):
                return dt
        except Exception:
            continue
    return None


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
