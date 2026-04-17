from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import lru_cache
import time
import os

DEBUG_TIMING = os.environ.get("DEBUG_TIMING", "false").lower() == "true"

@lru_cache(maxsize=16)
def _get_ticker_object(ticker_symbol):
    """
    Cache the yf.Ticker object to avoid re-instantiation.
    Cache holds up to 16 tickers (most recent).
    """
    return yf.Ticker(ticker_symbol)


@lru_cache(maxsize=16)
def _get_ticker_info(ticker_symbol):
    """
    Cache ticker.info since multiple functions need it.
    This avoids redundant API calls for the same data.
    Cache expires naturally when maxsize is exceeded.
    """
    ticker = _get_ticker_object(ticker_symbol)
    return ticker.info


def fetch_all_data(ticker_symbol, period="5y", interval="1wk"):
    """
    Master function that fetches ALL data for a given ticker.
    Uses ThreadPoolExecutor to run API calls in parallel.
    """
    start_total = time.time()

    # Validate first (must be sequential — no point parallelizing if invalid)
    validation = validate_ticker(ticker_symbol)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    # Define all fetch tasks
    tasks = {
        "profile": lambda: fetch_company_profile(ticker_symbol),
        "historical": lambda: fetch_historical_data(ticker_symbol, period=period, interval=interval),
        "options": lambda: fetch_option_chain(ticker_symbol),
        "analyst": lambda: fetch_analyst_ratings(ticker_symbol),
        "earnings": lambda: fetch_earnings_data(ticker_symbol),
        "dividends": lambda: fetch_dividend_data(ticker_symbol),
        "financials": lambda: fetch_financials(ticker_symbol),
        "insider": lambda: fetch_insider_transactions(ticker_symbol),
    }

    results = {}
    timings = {}

    # Run all fetches in parallel (max 8 threads for 8 API calls)
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_key = {}
        for key, func in tasks.items():
            future_to_key[executor.submit(func)] = (key, time.time())

        for future in as_completed(future_to_key):
            key, task_start = future_to_key[future]
            try:
                results[key] = future.result()
                timings[key] = round(time.time() - task_start, 3)
            except Exception as e:
                results[key] = {"success": False, "error": str(e)}
                timings[key] = round(time.time() - task_start, 3)

    total_time = round(time.time() - start_total, 3)
    timings["TOTAL"] = total_time
    if DEBUG_TIMING:
        # Print timing report to console
        print(f"\n{'='*50}")
        print(f"  PARALLEL FETCH TIMINGS FOR {ticker_symbol}")
        print(f"{'='*50}")
        for key, val in sorted(timings.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(val * 10)
            print(f"  {key:<15} {val:>6.3f}s  {bar}")
        print(f"{'='*50}\n")

    all_data = {
        "success": True,
        "ticker": ticker_symbol.upper(),
        "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "timings": timings,
        "profile": results.get("profile", {"success": False, "error": "Not fetched"}),
        "historical": results.get("historical", {"success": False, "error": "Not fetched"}),
        "options": results.get("options", {"success": False, "error": "Not fetched"}),
        "analyst": results.get("analyst", {"success": False, "error": "Not fetched"}),
        "earnings": results.get("earnings", {"success": False, "error": "Not fetched"}),
        "dividends": results.get("dividends", {"success": False, "error": "Not fetched"}),
        "financials": results.get("financials", {"success": False, "error": "Not fetched"}),
        "insider": results.get("insider", {"success": False, "error": "Not fetched"}),
    }

    return all_data

def calculate_ivr_ivp(ticker_symbol, current_iv):
    """
    Calculate IV Rank (IVR) and IV Percentile (IVP) for a ticker, given today's IV.
    Uses cached HV30 data. Returns (ivr, ivp) as floats, or (None, None) if insufficient data.
    """
    hv30_df = get_hv30_series(ticker_symbol)
    if hv30_df is None or current_iv is None:
        return None, None
    if "HV30" not in hv30_df.columns:
        return None, None
    hv30_values = hv30_df["HV30"].dropna().tail(252).values
    if len(hv30_values) < 30:
        return None, None
    # IVR: where does today's IV sit in 52-week HV30 range
    min_hv = float(np.nanmin(hv30_values))
    max_hv = float(np.nanmax(hv30_values))
    if max_hv == min_hv:
        ivr = 100.0 if current_iv >= max_hv else 0.0
    else:
        ivr = ((current_iv - min_hv) / (max_hv - min_hv)) * 100
    # IVP: percent of days HV30 was below today's IV
    ivp = 100.0 * np.sum(hv30_values < current_iv) / len(hv30_values)
    return round(ivr, 2), round(ivp, 2)
import os
import pickle

def get_hv30_cache_path(ticker_symbol):
    """Return the cache file path for a ticker's HV30 data."""
    cache_dir = os.path.join(os.path.dirname(__file__), "hv30_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{ticker_symbol.upper()}_hv30.pkl")

def calculate_and_cache_hv30(ticker_symbol, force_refresh=False):
    """
    Fetch 1-year daily close prices, calculate HV30 (30-day rolling std of log returns, annualized),
    and cache the result. Returns a DataFrame with Date and HV30 columns.
    """
    cache_path = get_hv30_cache_path(ticker_symbol)
    if not force_refresh and os.path.exists(cache_path):
        # Check cache age (1 day expiry)
        mtime = os.path.getmtime(cache_path)
        if (datetime.now() - datetime.fromtimestamp(mtime)).days < 1:
            try:
                with open(cache_path, "rb") as f:
                    hv30_df = pickle.load(f)
                return hv30_df
            except Exception:
                pass  # Fallback to recalc if cache is corrupt

    # Fetch 1 year of daily close prices
    ticker = _get_ticker_object(ticker_symbol)
    hist = ticker.history(period="1y", interval="1d")
    if hist is None or hist.empty or "Close" not in hist:
        return None
    hist = hist.reset_index()
    hist = hist.dropna(subset=["Close"])
    if len(hist) < 40:
        return None  # Not enough data

    # Calculate log returns
    hist["log_return"] = np.log(hist["Close"] / hist["Close"].shift(1))
    # 30-day rolling std
    hist["rolling_std"] = hist["log_return"].rolling(window=30).std()
    # Annualize
    hist["HV30"] = hist["rolling_std"] * np.sqrt(252)
    hv30_df = hist[["Date", "HV30"]].dropna().copy()
    # Save to cache
    with open(cache_path, "wb") as f:
        pickle.dump(hv30_df, f)
    return hv30_df

def get_hv30_series(ticker_symbol):
    """
    Load HV30 series for a ticker from cache, or calculate and cache if not available.
    Returns a DataFrame with Date and HV30 columns, or None if unavailable.
    """
    return calculate_and_cache_hv30(ticker_symbol)
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _to_date(value):
    """Convert a calendar/earnings value into a Python date, if possible."""
    if value is None:
        return None

    try:
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return None
        if isinstance(ts, pd.Timestamp):
            return ts.tz_localize(None).date() if ts.tzinfo else ts.date()
        if hasattr(ts, "date"):
            return ts.date()
    except Exception:
        return None

    return None


def _extract_date_candidates(value):
    """Collect any date-like values from scalars, iterables, or DataFrames."""
    candidates = []

    if value is None:
        return candidates

    if isinstance(value, pd.DataFrame):
        if isinstance(value.index, pd.DatetimeIndex):
            for idx in value.index:
                candidates.append(idx.tz_localize(None).date() if idx.tz is not None else idx.date())

        for col in value.columns:
            series = value[col]
            if pd.api.types.is_datetime64_any_dtype(series):
                for item in series.dropna():
                    dt = _to_date(item)
                    if dt is not None:
                        candidates.append(dt)
            elif "date" in str(col).lower() or "earnings" in str(col).lower():
                converted = pd.to_datetime(series, errors="coerce")
                for item in converted.dropna():
                    dt = _to_date(item)
                    if dt is not None:
                        candidates.append(dt)
        return candidates

    if isinstance(value, (list, tuple, set, pd.Index)):
        iterable = value
    else:
        iterable = [value]

    for item in iterable:
        if isinstance(item, (list, tuple, set, pd.Index)):
            candidates.extend(_extract_date_candidates(item))
            continue
        dt = _to_date(item)
        if dt is not None:
            candidates.append(dt)

    return candidates


def get_next_earnings_info(ticker, today=None):
    """
    Find the next upcoming earnings date for a ticker.
    Prefers ticker.calendar and falls back to ticker.earnings_dates.
    Returns a dict with a date object, formatted string, and source name.
    """
    today = today or datetime.utcnow().date()

    def _first_future_date(raw_value):
        candidates = sorted({d for d in _extract_date_candidates(raw_value) if d >= today})
        return candidates[0] if candidates else None

    try:
        calendar = ticker.calendar or {}
        next_date = _first_future_date(calendar.get("Earnings Date"))
        if next_date is not None:
            return {
                "date": next_date,
                "date_str": next_date.strftime("%Y-%m-%d"),
                "source": "calendar",
            }
    except Exception:
        pass

    try:
        earnings_dates = ticker.earnings_dates
        next_date = _first_future_date(earnings_dates)
        if next_date is not None:
            return {
                "date": next_date,
                "date_str": next_date.strftime("%Y-%m-%d"),
                "source": "earnings_dates",
            }
    except Exception:
        pass

    return {"date": None, "date_str": None, "source": None}


def validate_ticker(ticker_symbol):
    """
    Validate a ticker symbol by attempting to fetch basic info.
    Returns a dict with validation status and current price, or an error message.
    """
    try:
        ticker = _get_ticker_object(ticker_symbol)
        info = _get_ticker_info(ticker_symbol)

        if not info or info.get("regularMarketPrice") is None:
            return {
                "valid": False,
                "error": f"'{ticker_symbol}' does not appear to be a valid ticker symbol.",
            }

        return {
            "valid": True,
            "currentPrice": info.get("regularMarketPrice"),
            "ticker": ticker_symbol.upper(),
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Error validating ticker '{ticker_symbol}': {str(e)}",
        }


def fetch_company_profile(ticker_symbol):
    """
    Fetch company profile and description.
    Returns a dict of company info fields.
    """
    try:
        ticker = _get_ticker_object(ticker_symbol)
        info = _get_ticker_info(ticker_symbol)
        next_earnings = get_next_earnings_info(ticker)

        profile = {
            "longName": info.get("longName", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "website": info.get("website", "N/A"),
            "marketCap": info.get("marketCap", "N/A"),
            "currency": info.get("currency", "N/A"),
            "exchange": info.get("exchange", "N/A"),
            "country": info.get("country", "N/A"),
            "city": info.get("city", "N/A"),
            "state": info.get("state", "N/A"),
            "fullTimeEmployees": info.get("fullTimeEmployees", "N/A"),
            "longBusinessSummary": info.get("longBusinessSummary", "N/A"),
            "regularMarketPrice": info.get("regularMarketPrice", "N/A"),
            "previousClose": info.get("previousClose", "N/A"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh", "N/A"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow", "N/A"),
            "averageVolume": info.get("averageVolume", "N/A"),
            "trailingPE": info.get("trailingPE", "N/A"),
            "forwardPE": info.get("forwardPE", "N/A"),
            "beta": info.get("beta", "N/A"),
            "nextEarningsDate": next_earnings.get("date_str") or "N/A",
        }

        return {"success": True, "data": profile}
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_historical_data(ticker_symbol, period="1y", interval="1wk", bb_window=20):
    """
    Fetch historical OHLCV data and calculate Bollinger Bands.
    Returns a dict containing the DataFrame as JSON (for dcc.Store serialization).
    """
    try:
        ticker = _get_ticker_object(ticker_symbol)

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
            # Fallback: None (use yfinance period directly)
            return None

        # Helper: convert interval to pandas DateOffset for padding calculation
        def _interval_to_offset(itv):
            if itv.endswith("m") and itv[:-1].isdigit():
                return pd.DateOffset(minutes=int(itv[:-1]))
            if itv.endswith("h") and itv[:-1].isdigit():
                return pd.DateOffset(hours=int(itv[:-1]))
            if itv == "1d" or itv == "1d":
                return pd.DateOffset(days=1)
            if itv == "1wk":
                return pd.DateOffset(weeks=1)
            if itv == "1mo":
                return pd.DateOffset(months=1)
            # Default to 1 day
            return pd.DateOffset(days=1)

        # Try to compute an explicit start/end with padding rows so BB can be computed
        use_start_end = False
        try:
            period_offset = _period_to_offset(period)
            interval_offset = _interval_to_offset(interval)
            if period_offset is not None and interval_offset is not None:
                visible_end = pd.Timestamp.now()
                visible_start = visible_end - period_offset

                padding_rows = max(0, bb_window - 1)
                padded_start = visible_start - (padding_rows * interval_offset)

                # Use explicit start/end to request padding
                df = ticker.history(start=padded_start.strftime("%Y-%m-%d"), end=visible_end.strftime("%Y-%m-%d"), interval=interval)
                use_start_end = True
            else:
                # Fall back to period string
                df = ticker.history(period=period, interval=interval)
        except Exception:
            # If anything goes wrong, fallback to period string
            df = ticker.history(period=period, interval=interval)

        if df is None or df.empty:
            return {"success": False, "error": "No historical data available."}

        df = df.reset_index()

        # Handle timezone-aware datetime
        if df["Date"].dt.tz is not None:
            df["Date"] = df["Date"].dt.tz_localize(None)

        # Calculate Bollinger Bands (configurable window, default: 20-period SMA, 2 standard deviations)
        df["SMA"] = df["Close"].rolling(window=bb_window).mean()
        df["STD"] = df["Close"].rolling(window=bb_window).std()
        df["Upper_BB"] = df["SMA"] + (2 * df["STD"])
        df["Lower_BB"] = df["SMA"] - (2 * df["STD"])

        # Convert Date to string for JSON serialization
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

        # Include earnings dates (if available) so charts can annotate them without extra fetch
        earnings_dates_payload = None
        try:
            ed = ticker.earnings_dates
            if ed is not None and not ed.empty:
                # Convert to simple list of dicts with date and any available columns
                ed_df = ed.reset_index()
                # Normalize datetimes
                for col in ed_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(ed_df[col]):
                        ed_df[col] = ed_df[col].dt.strftime("%Y-%m-%d")
                earnings_dates_payload = ed_df.to_dict("records")
        except Exception:
            earnings_dates_payload = None

        return {
            "success": True,
            "data": df.to_dict("records"),
            "period": period,
            "interval": interval,
            "padded_using_start_end": use_start_end,
            "earnings_dates": earnings_dates_payload,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_option_chain(ticker_symbol):
    """
    Fetch the option chain for the nearest expiration >30 days away.
    Filters to 1 ITM strike + all OTM strikes.
    Adds custom columns: Last/Strike %, MidAvg/Strike %, and Greeks.
    Returns a dict with calls and puts DataFrames as JSON.
    """
    try:
        ticker = _get_ticker_object(ticker_symbol)
        today = datetime.utcnow()
        today_date = today.date()
        expirations = ticker.options

        if not expirations:
            return {"success": False, "error": "No options data available for this ticker."}

        # Get current stock price
        info = _get_ticker_info(ticker_symbol)
        current_price = info.get("regularMarketPrice", None)
        if current_price is None:
            hist = ticker.history(period="1d")
            if hist.empty:
                return {"success": False, "error": "Could not determine current stock price."}
            current_price = hist["Close"].iloc[-1]

        # Find nearest expiration >30 days away
        selected_exp = None
        for exp_date in expirations:
            exp_datetime = datetime.strptime(exp_date, "%Y-%m-%d")
            if exp_datetime > today + timedelta(days=30):
                selected_exp = exp_date
                break

        if selected_exp is None:
            return {"success": False, "error": "No options with expiration >30 days away found."}

        option_chain = ticker.option_chain(selected_exp)
        exp_datetime = datetime.strptime(selected_exp, "%Y-%m-%d")
        days_to_exp = (exp_datetime - today).days
        next_earnings = get_next_earnings_info(ticker, today=today_date)
        next_earnings_date = next_earnings.get("date")
        next_earnings_date_str = next_earnings.get("date_str") or "N/A"
        earnings_before_expiration = bool(
            next_earnings_date is not None
            and next_earnings_date <= exp_datetime.date()
        )
        if next_earnings_date is None:
            next_earnings_status = "N/A"
        elif earnings_before_expiration:
            next_earnings_status = "before expiry"
        else:
            next_earnings_status = "after expiry"

        def enrich_options_df(df):
            """Add custom percentage columns and ensure Greek columns exist."""
            df = df.copy()

            # Custom column 1: lastPrice / strike as %
            # Already a ratio, multiply by 100 to get percentage
            df["Last/Strike %"] = (df["lastPrice"] / df["strike"]).round(4)

            # Custom column 2: ((bid + ask) / 2) / strike as %
            df["MidAvg/Strike %"] = (
                ((df["bid"] + df["ask"]) / 2) / df["strike"]
            ).round(4)

            # Ensure Greek columns exist
            greek_cols = ["delta", "gamma", "theta", "vega", "rho"]
            for col in greek_cols:
                if col not in df.columns:
                    df[col] = np.nan

            # Keep implied volatility as a decimal (e.g., 0.25 for 25%)
            # so IVR/IVP calculations use the same scale as HV30.
            if "impliedVolatility" in df.columns:
                df["impliedVolatility"] = df["impliedVolatility"].round(4)

            return df


        # --- CALLS ---
        calls = enrich_options_df(option_chain.calls)
        itm_calls = calls[calls["strike"] < current_price].sort_values("strike", ascending=False)
        otm_calls = calls[calls["strike"] >= current_price].sort_values("strike", ascending=True)
        filtered_calls = pd.concat([itm_calls.head(1), otm_calls]).sort_values("strike")

        # --- PUTS ---
        puts = enrich_options_df(option_chain.puts)
        itm_puts = puts[puts["strike"] > current_price].sort_values("strike", ascending=True)
        otm_puts = puts[puts["strike"] <= current_price].sort_values("strike", ascending=True)
        filtered_puts = pd.concat([otm_puts, itm_puts.head(1)]).sort_values("strike")

        # Select display columns
        display_cols = [
            "strike", "lastPrice", "bid", "ask",
            "Last/Strike %", "MidAvg/Strike %",
            "volume", "openInterest", "impliedVolatility",
            "delta", "gamma", "theta", "vega", "rho",
            "inTheMoney",
        ]

        calls_cols = [c for c in display_cols if c in filtered_calls.columns]
        puts_cols = [c for c in display_cols if c in filtered_puts.columns]

        return {
            "success": True,
            "ticker": ticker_symbol.upper(),
            "data": {
                "calls": filtered_calls[calls_cols].to_dict("records"),
                "puts": filtered_puts[puts_cols].to_dict("records"),
                "expiration_date": selected_exp,
                "days_to_expiration": days_to_exp,
                "current_price": current_price,
                "num_otm_calls": len(otm_calls),
                "num_otm_puts": len(otm_puts),
                "next_earnings_date": next_earnings_date_str,
                "next_earnings_days": (
                    (next_earnings_date - today_date).days if next_earnings_date is not None else None
                ),
                "earnings_before_expiration": earnings_before_expiration,
                "next_earnings_status": next_earnings_status,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_analyst_ratings(ticker_symbol):
    """
    Fetch analyst ratings, recommendations, and upgrade/downgrade history.
    Returns a dict with recommendations and upgrades/downgrades as JSON.
    """
    try:
        ticker = _get_ticker_object(ticker_symbol)
        result = {"success": True, "data": {}}

        # Recommendations summary
        recommendations = ticker.recommendations
        if recommendations is not None and isinstance(recommendations, pd.DataFrame) and not recommendations.empty:
            rec_df = recommendations.reset_index() if not isinstance(recommendations.index, pd.RangeIndex) else recommendations
            result["data"]["recommendations"] = rec_df.to_dict("records")
        else:
            result["data"]["recommendations"] = None

        # Upgrades / Downgrades
        upgrades_downgrades = ticker.upgrades_downgrades
        if upgrades_downgrades is not None and isinstance(upgrades_downgrades, pd.DataFrame) and not upgrades_downgrades.empty:
            ud_df = upgrades_downgrades.tail(20).reset_index()
            # Convert any datetime index to string for serialization
            for col in ud_df.columns:
                if pd.api.types.is_datetime64_any_dtype(ud_df[col]):
                    ud_df[col] = ud_df[col].dt.strftime("%Y-%m-%d %H:%M")
            result["data"]["upgrades_downgrades"] = ud_df.to_dict("records")
        else:
            result["data"]["upgrades_downgrades"] = None

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_earnings_data(ticker_symbol):
    """
    Fetch EPS vs. estimated earnings for the prior 4 quarters.
    Uses earnings_dates (still supported) and quarterly_income_stmt for net income.
    """
    try:
        ticker = _get_ticker_object(ticker_symbol)
        result = {"success": True, "data": {}}

        # Earnings dates (contains actual vs. estimate EPS)
        try:
            earnings_dates = ticker.earnings_dates
            if earnings_dates is not None and not earnings_dates.empty:
                # Safely handle index timezone information
                if isinstance(earnings_dates.index, pd.DatetimeIndex):
                    past_earnings = earnings_dates[
                        earnings_dates.index <= pd.Timestamp.now(tz=earnings_dates.index.tz)
                    ]
                else:
                    past_earnings = earnings_dates

                if not past_earnings.empty:
                    ed_df = past_earnings.head(4).reset_index()
                    for col in ed_df.columns:
                        if pd.api.types.is_datetime64_any_dtype(ed_df[col]):
                            ed_df[col] = ed_df[col].dt.strftime("%Y-%m-%d")
                    result["data"]["earnings_dates"] = ed_df.to_dict("records")
                else:
                    result["data"]["earnings_dates"] = None
            else:
                result["data"]["earnings_dates"] = None
        except Exception:
            result["data"]["earnings_dates"] = None

        # Quarterly income statement (replacement for deprecated quarterly_earnings)
        try:
            quarterly_income = ticker.quarterly_income_stmt
            if quarterly_income is not None and not quarterly_income.empty:
                # Extract key earnings rows
                key_rows = ["Net Income", "Total Revenue", "Operating Income", "Basic EPS", "Diluted EPS"]
                available_rows = [r for r in key_rows if r in quarterly_income.index]

                if available_rows:
                    filtered = quarterly_income.loc[available_rows]
                    qi_df = filtered.reset_index()
                    qi_df.columns = [
                        col.strftime("%Y-%m-%d") if isinstance(col, pd.Timestamp) else str(col)
                        for col in qi_df.columns
                    ]
                    result["data"]["quarterly_income"] = qi_df.to_dict("records")
                else:
                    result["data"]["quarterly_income"] = None
            else:
                result["data"]["quarterly_income"] = None
        except Exception:
            result["data"]["quarterly_income"] = None

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}



def fetch_dividend_data(ticker_symbol):
    """
    Fetch dividend data including yield, payout ratio, and history.
    Returns a dict with dividend info and history as JSON.
    """
    try:
        ticker = _get_ticker_object(ticker_symbol)
        info = _get_ticker_info(ticker_symbol)

        dividend_info = {
            "dividendRate": info.get("dividendRate", "N/A"),
            "dividendYield": info.get("dividendYield", "N/A"),
            "exDividendDate": info.get("exDividendDate", "N/A"),
            "payoutRatio": info.get("payoutRatio", "N/A"),
            "fiveYearAvgDividendYield": info.get("fiveYearAvgDividendYield", "N/A"),
            "trailingAnnualDividendRate": info.get("trailingAnnualDividendRate", "N/A"),
            "trailingAnnualDividendYield": info.get("trailingAnnualDividendYield", "N/A"),
        }

        # Convert ex-dividend date from timestamp
        if dividend_info["exDividendDate"] not in ("N/A", None):
            try:
                dividend_info["exDividendDate"] = datetime.fromtimestamp(
                    dividend_info["exDividendDate"]
                ).strftime("%Y-%m-%d")
            except (TypeError, OSError, ValueError):
                pass

        # Format percentages
        for key in ("dividendYield", "payoutRatio", "trailingAnnualDividendYield"):
            val = dividend_info.get(key)
            if val not in ("N/A", None):
                try:
                    dividend_info[key] = round(val * 100, 2)
                except (TypeError, ValueError):
                    pass

        # Dividend history
        dividends = ticker.dividends
        dividend_history = None
        if dividends is not None and not dividends.empty:
            div_df = dividends.tail(12).reset_index()
            if div_df["Date"].dt.tz is not None:
                div_df["Date"] = div_df["Date"].dt.tz_localize(None)
            div_df["Date"] = div_df["Date"].dt.strftime("%Y-%m-%d")
            dividend_history = div_df.to_dict("records")

        return {
            "success": True,
            "data": {
                "info": dividend_info,
                "history": dividend_history,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_financials(ticker_symbol):
    """
    Fetch income statement, balance sheet, and cash flow.
    Returns a dict with each financial statement as JSON.
    """
    try:
        ticker = _get_ticker_object(ticker_symbol)
        result = {"success": True, "data": {}}

        # Income Statement
        try:
            income_stmt = ticker.income_stmt
            if income_stmt is not None and not income_stmt.empty:
                inc_df = income_stmt.reset_index()
                # Convert column headers (dates) to strings
                inc_df.columns = [
                    col.strftime("%Y-%m-%d") if isinstance(col, pd.Timestamp) else str(col)
                    for col in inc_df.columns
                ]
                result["data"]["income_statement"] = inc_df.to_dict("records")
            else:
                result["data"]["income_statement"] = None
        except Exception:
            result["data"]["income_statement"] = None

        # Balance Sheet
        try:
            balance_sheet = ticker.balance_sheet
            if balance_sheet is not None and not balance_sheet.empty:
                bs_df = balance_sheet.reset_index()
                bs_df.columns = [
                    col.strftime("%Y-%m-%d") if isinstance(col, pd.Timestamp) else str(col)
                    for col in bs_df.columns
                ]
                result["data"]["balance_sheet"] = bs_df.to_dict("records")
            else:
                result["data"]["balance_sheet"] = None
        except Exception:
            result["data"]["balance_sheet"] = None

        # Cash Flow
        try:
            cashflow = ticker.cashflow
            if cashflow is not None and not cashflow.empty:
                cf_df = cashflow.reset_index()
                cf_df.columns = [
                    col.strftime("%Y-%m-%d") if isinstance(col, pd.Timestamp) else str(col)
                    for col in cf_df.columns
                ]
                result["data"]["cash_flow"] = cf_df.to_dict("records")
            else:
                result["data"]["cash_flow"] = None
        except Exception:
            result["data"]["cash_flow"] = None

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_insider_transactions(ticker_symbol):
    """
    Fetch insider transactions, insider purchases summary, and institutional holders.
    Returns a dict with each dataset as JSON.
    """
    try:
        ticker = _get_ticker_object(ticker_symbol)
        result = {"success": True, "data": {}}

        # Insider Transactions
        try:
            insider_transactions = ticker.insider_transactions
            if insider_transactions is not None and not insider_transactions.empty:
                it_df = insider_transactions.reset_index(drop=True)
                # Convert datetime columns to strings
                for col in it_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(it_df[col]):
                        it_df[col] = it_df[col].dt.strftime("%Y-%m-%d")
                result["data"]["insider_transactions"] = it_df.to_dict("records")
            else:
                result["data"]["insider_transactions"] = None
        except Exception:
            result["data"]["insider_transactions"] = None

        # Insider Purchases Summary
        try:
            insider_purchases = ticker.insider_purchases
            if insider_purchases is not None and not insider_purchases.empty:
                ip_df = insider_purchases.reset_index(drop=True)
                result["data"]["insider_purchases"] = ip_df.to_dict("records")
            else:
                result["data"]["insider_purchases"] = None
        except Exception:
            result["data"]["insider_purchases"] = None

        # Institutional Holders
        try:
            institutional_holders = ticker.institutional_holders
            if institutional_holders is not None and not institutional_holders.empty:
                ih_df = institutional_holders.reset_index(drop=True)
                for col in ih_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(ih_df[col]):
                        ih_df[col] = ih_df[col].dt.strftime("%Y-%m-%d")
                result["data"]["institutional_holders"] = ih_df.to_dict("records")
            else:
                result["data"]["institutional_holders"] = None
        except Exception:
            result["data"]["institutional_holders"] = None

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

'''
def fetch_all_data(ticker_symbol, period="1y", interval="1wk"):
    """
    Master function that fetches ALL data for a given ticker.
    Returns a single dict containing all data sections.
    This is what gets stored in dcc.Store for sharing across callbacks.
    """
    # Validate first
    validation = validate_ticker(ticker_symbol)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    # Fetch all data sections
    all_data = {
        "success": True,
        "ticker": ticker_symbol.upper(),
        "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "profile": fetch_company_profile(ticker_symbol),
        "historical": fetch_historical_data(ticker_symbol, period=period, interval=interval),
        "options": fetch_option_chain(ticker_symbol),
        "analyst": fetch_analyst_ratings(ticker_symbol),
        "earnings": fetch_earnings_data(ticker_symbol),
        "dividends": fetch_dividend_data(ticker_symbol),
        "financials": fetch_financials(ticker_symbol),
        "insider": fetch_insider_transactions(ticker_symbol),
    }

    return all_data
'''