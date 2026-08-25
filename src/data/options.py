"""Options data for the fixed-income ETF universe.

Two independent workflows share this module:

1. ATM IV time-series (``fetch_atm_iv_30d``)
   Fetches the near-30-day ATM call IV for a single ticker across a date range
   on a weekly (Friday) cadence.  Used to build the IV panel for the
   subsumption regression.

2. Full-chain liquidity screen (``run_screen`` / ``concat_results``)
   Fetches every listed call contract for all core-panel tickers on one or more
   snapshot dates, computes BSM Greeks for each contract, and applies
   dollar-normalised filters to identify tickers with liquid options.

Native Greeks & IV:
   Fetched directly from ThetaData's native endpoints (no BSM solver required).

Caches
------
- ATM IV  : ``data/raw/options_screen/{ticker}/{date}.json``          (one per Friday)
- Full chain: ``data/raw/options_screen/{ticker}/{date}_chain.json`` (one per snap)

Usage
-----
    from src.data.options import fetch_atm_iv_30d, run_screen, concat_results
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

# gRPC's built-in resolver fails on networks where the system DNS is a
# link-local IPv6 address; "native" delegates to the OS resolver instead.
# Must be set before the grpc module is first imported.
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf
from src import config
from src.data.options_universe import LIQUIDITY_SCORE_MIN

logger = logging.getLogger(__name__)

_IV_SEARCH_BOUNDS   = (1e-4, 20.0)
_MIN_OPTION_PRICE   = 0.01
_IV_CACHE_DIR       = config.RAW_DIR / "options_screen"
_SCREEN_CACHE_DIR   = config.RAW_DIR / "options_screen"

_THETADATA_USERNAME = os.getenv("THETADATA_USERNAME")
_THETADATA_PASSWORD = os.getenv("THETADATA_PASSWORD")

_ANNUALISE_FACTOR: float = config.ANNUALISE_FACTOR


# ---------------------------------------------------------------------------
# Underlying price / RF / dividend helpers
# ---------------------------------------------------------------------------

def _download_prices(ticker: str, start: str, end: str) -> dict[date, float]:
    hist = yf.Ticker(ticker).history(start=start, end=end, interval="1d", auto_adjust=False)
    if hist.empty:
        return {}
    hist.index = pd.to_datetime(hist.index, utc=True).tz_convert(None)
    return {d.date(): float(p) for d, p in hist["Close"].items()}


def _historical_div_yield_map(
    ticker: str,
    start:  str,
    end:    str,
    prices: dict,
) -> dict:
    """Return {snap_date: trailing_12m_div_yield} for each Friday in [start, end].

    Trailing yield = sum(dividends paid in prior 12 months) / price on snap date.
    Falls back to 0.0 for dates with no price or no dividend history.
    """
    try:
        divs = yf.Ticker(ticker).dividends
    except Exception:
        return {}
    if divs is None or divs.empty:
        return {}

    divs = divs.copy()
    divs.index = pd.to_datetime(divs.index).tz_localize(None)
    divs = divs.sort_index()

    out: dict = {}
    for snap in _friday_dates_in_range(start, end):
        px = prices.get(snap)
        if not px:
            continue
        window_start = pd.Timestamp(snap) - pd.DateOffset(years=1)
        window_end   = pd.Timestamp(snap)
        trailing_div = float(
            divs[(divs.index >= window_start) & (divs.index <= window_end)].sum()
        )
        out[snap] = trailing_div / px if trailing_div > 0 else 0.0
    return out


def _rf_map(start: str, end: str) -> dict[date, float]:
    """Return {date: annualised_rf} from FRED DTB3."""
    api_key = os.getenv("FRED_API_KEY") or config.FRED_API_KEY
    if not api_key:
        logger.warning("FRED_API_KEY not set; using rf=0.05 for all dates.")
        return {}
    try:
        from src.data.macro import fred_series, make_fred_session
        df = fred_series("DTB3", api_key=api_key, session=make_fred_session())
        df["date_"] = pd.to_datetime(df["Date"]).dt.date
        df = df[
            (df["date_"] >= date.fromisoformat(start)) &
            (df["date_"] <= date.fromisoformat(end))
        ]
        return {row.date_: float(row.DTB3) / 100.0 for row in df.itertuples()}
    except Exception as exc:
        logger.warning("Could not fetch DTB3: %s. Using rf=0.05.", exc)
        return {}


def _nearest_rf(rf: dict[date, float], snap: date, default: float = 0.05) -> float:
    if not rf:
        return default
    for lag in range(0, 11):
        v = rf.get(snap - timedelta(days=lag))
        if v is not None:
            return v
    return default


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _friday_dates_in_range(start: str, end: str) -> list[date]:
    d0, d1   = date.fromisoformat(start), date.fromisoformat(end)
    days_fri = (4 - d0.weekday()) % 7
    d        = d0 + timedelta(days=days_fri)
    out: list[date] = []
    while d <= d1:
        out.append(d)
        d += timedelta(weeks=1)
    return out


# ---------------------------------------------------------------------------
# ThetaData helpers
# ---------------------------------------------------------------------------

def _make_client(username: str, password: str):
    if not username or not password:
        raise RuntimeError(
            "ThetaData credentials not set. Export THETADATA_USERNAME and "
            "THETADATA_PASSWORD in your environment before fetching."
        )
    from thetadata import ThetaClient
    return ThetaClient(email=username, password=password, dataframe_type="pandas")


def _theta_call(fn, *args, max_retries: int = 5, **kwargs):
    """Call a ThetaData API function with exponential-backoff retry on rate-limit errors."""
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if "RESOURCE_EXHAUSTED" in str(exc) and attempt < max_retries - 1:
                wait = 2 ** attempt   # 1, 2, 4, 8 seconds
                logger.debug("ThetaData rate-limited — retrying in %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
                continue
            raise



def _get_expirations(client, ticker: str) -> list[date]:
    try:
        df = _theta_call(client.option_list_expirations, ticker)
    except Exception as exc:
        logger.warning("_get_expirations: no options data for %s (%s)", ticker, exc)
        return []
    if df is None or df.empty:
        return []
    col = "expiration" if "expiration" in df.columns else df.columns[-1]
    return sorted(pd.to_datetime(df[col]).dt.date.tolist())


def _get_strikes(client, ticker: str, exp: date) -> list[float]:
    try:
        df = _theta_call(client.option_list_strikes, ticker, exp)
    except Exception:
        return []
    if df is None or df.empty:
        return []
    col = "strike" if "strike" in df.columns else df.columns[-1]
    return sorted(df[col].astype(float).tolist())


# ---------------------------------------------------------------------------
# ATM IV cache helpers
# ---------------------------------------------------------------------------

def _iv_cache_path(cache_dir: Path, ticker: str, snap: date) -> Path:
    return cache_dir / ticker / f"{snap.isoformat()}.json"


def _call_put_iv_cache_path(cache_dir: Path, ticker: str, snap: date) -> Path:
    return cache_dir / ticker / f"{snap.isoformat()}_call_put_iv.json"


def _load_iv_cache(path: Path) -> dict | None:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_iv_cache(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, default=str))


# ---------------------------------------------------------------------------
# EOD quote helpers
# ---------------------------------------------------------------------------

_OI_RIGHT_MAP: dict[str, str] = {"CALL": "C", "PUT": "P", "C": "C", "P": "P"}


def _eod_detail_from_row(row: pd.Series) -> dict | None:
    """Normalize one ThetaData EOD row to the chain cache's price fields."""
    bid   = float(row.get("bid",   0) or 0)
    ask   = float(row.get("ask",   0) or 0)
    close = float(row.get("close", 0) or 0)

    detail = None
    if bid > 0 and ask > 0:
        detail = {
            "bid": bid, "ask": ask, "close": close,
            "option_price": (bid + ask) / 2.0, "price_type": "mid",
        }
    elif close >= _MIN_OPTION_PRICE:
        detail = {
            "bid": bid, "ask": ask, "close": close,
            "option_price": close, "price_type": "close",
        }

    if detail is not None:
        detail["iv"] = float(row.get("implied_vol", float("nan")))
        detail["delta"] = float(row.get("delta", float("nan")))
        detail["gamma"] = float(row.get("gamma", float("nan")))
        detail["vega"] = float(row.get("vega", float("nan")))
        detail["theta_daily"] = float(row.get("theta", float("nan")))
        return detail
    return None


def _fetch_bulk_eod(
    client,
    ticker: str,
    exp: date,
    snap: date,
    rights: tuple[str, ...],
) -> dict[tuple[float, str], dict] | None:
    """Return EOD price details for all requested contracts in one API call.

    ``None`` means the bulk request failed and tells the caller to use the
    legacy per-contract fallback.  An empty dict is a successful response with
    no usable EOD prices.
    """
    requested = {r.upper() for r in rights}
    api_right = (
        "both" if requested == {"C", "P"}
        else "call" if requested == {"C"}
        else "put"
    )
    try:
        df = _theta_call(
            client.option_history_greeks_eod,
            start_date=snap,
            end_date=snap,
            symbol=ticker,
            expiration=exp,
            strike="*",
            right=api_right,
        )
    except Exception as exc:
        logger.warning(
            "%s %s exp=%s: bulk EOD pull failed; using contract fallback — %s",
            ticker, snap, exp, exc,
        )
        return None

    if df is None or df.empty:
        return {}

    result: dict[tuple[float, str], dict] = {}
    for _, row in df.iterrows():
        right = _OI_RIGHT_MAP.get(str(row.get("right", "")).upper())
        if right not in requested:
            continue
        try:
            strike = float(row["strike"])
        except (KeyError, ValueError, TypeError):
            continue
        detail = _eod_detail_from_row(row)
        if detail is not None:
            result[(strike, right)] = detail
    return result


def _fetch_bulk_oi(
    client,
    ticker: str,
    exp:    date,
    snap:   date,
) -> dict[tuple[float, str], int]:
    """Return ``{(strike, right): open_interest}`` for all contracts on *snap*.

    Uses bulk ``option_history_open_interest`` (strike='*', right='both') — one
    API call per expiry.  Returns an empty dict on any failure so the caller
    can continue without OI.  *right* values are normalised to ``'C'`` / ``'P'``.
    """
    try:
        df = _theta_call(
            client.option_history_open_interest,
            symbol=ticker,
            expiration=exp,
            start_date=snap,
            end_date=snap,
            strike="*",
            right="both",
        )
    except Exception as exc:
        logger.warning(
            "%s %s exp=%s: bulk OI pull failed — %s", ticker, snap, exp, exc
        )
        return {}

    if df is None or df.empty:
        return {}

    result: dict[tuple[float, str], int] = {}
    for _, row in df.iterrows():
        r = _OI_RIGHT_MAP.get(str(row.get("right", "")).upper())
        if r is None:
            continue
        try:
            result[(float(row["strike"]), r)] = int(row["open_interest"])
        except (KeyError, ValueError, TypeError):
            continue
    return result


def _get_eod_detail(
    client, ticker: str, exp: date, strike: float, snap: date,
    right: str = "C",
) -> dict | None:
    """Return raw EOD fields for an option contract: bid, ask, close, price_type, option_price."""
    try:
        df = _theta_call(
            client.option_history_greeks_eod,
            start_date=snap, end_date=snap,
            symbol=ticker, expiration=exp,
            strike=str(strike), right=right,
        )
    except Exception:
        return None
    if df is None or df.empty:
        return None
    return _eod_detail_from_row(df.iloc[0])


# ---------------------------------------------------------------------------
# Public: ATM IV time-series
# ---------------------------------------------------------------------------

def _fetch_atm_iv_series(
    ticker:        str,
    start_date:    str,
    end_date:      str,
    cache_dir:     str | Path,
    username:      str,
    password:      str,
    *,
    cache_path_fn,
    record_fn,
    numeric_cols:  tuple[str, ...],
) -> pd.DataFrame:
    """Shared weekly ATM-IV pipeline for the call-only and call/put series.

    For each Friday in [start_date, end_date]:
    1. Identify the listed expiry closest to 30 calendar days out.
    2. Find near-ATM candidate strikes (closest to underlying EOD close).
    3. Delegate quote retrieval + IV computation to *record_fn*, which returns
       the full cache record for that snap date.

    Results are cached per (ticker, date) via *cache_path_fn* so the two
    series keep independent cache files.
    """
    cache_dir = Path(cache_dir)

    snap_dates = _friday_dates_in_range(start_date, end_date)
    if not snap_dates:
        return pd.DataFrame()

    missing = [
        d for d in snap_dates
        if _load_iv_cache(cache_path_fn(cache_dir, ticker, d)) is None
    ]

    if missing:
        prices = _download_prices(
            ticker,
            str(missing[0] - timedelta(days=7)),
            str(missing[-1] + timedelta(days=1)),
        )
        div_yield_map = _historical_div_yield_map(ticker, start_date, end_date, prices)
        rf            = _rf_map(start_date, end_date)

        client      = _make_client(username, password)
        expirations = _get_expirations(client, ticker)
        if not expirations:
            logger.error("No expirations returned for %s.", ticker)

        for snap in missing:
            cache_p = cache_path_fn(cache_dir, ticker, snap)

            underlying = prices.get(snap)
            if underlying is None:
                for lag in range(1, 8):
                    underlying = prices.get(snap - timedelta(days=lag))
                    if underlying is not None:
                        break
            if underlying is None:
                logger.warning("%s %s: no underlying price; skipping.", ticker, snap)
                _save_iv_cache(cache_p, {"date": snap.isoformat(), "ticker": ticker,
                                         "iv_30d": None, "reason": "no_underlying_price"})
                continue

            valid_exps = [e for e in expirations if e > snap]
            if not valid_exps:
                _save_iv_cache(cache_p, {"date": snap.isoformat(), "ticker": ticker,
                                         "iv_30d": None, "reason": "no_expirations"})
                continue

            target = snap + timedelta(days=30)
            expiry = min(valid_exps, key=lambda e: abs((e - target).days))
            dte    = (expiry - snap).days

            strikes = _get_strikes(client, ticker, expiry)
            if not strikes:
                _save_iv_cache(cache_p, {"date": snap.isoformat(), "ticker": ticker,
                                         "iv_30d": None, "reason": "no_strikes"})
                continue

            atm_idx    = min(range(len(strikes)), key=lambda i: abs(strikes[i] - underlying))
            candidates = sorted(
                strikes[max(0, atm_idx - 2): atm_idx + 3],
                key=lambda s: abs(s - underlying),
            )

            record = record_fn(
                client=client, ticker=ticker, snap=snap, expiry=expiry, dte=dte,
                candidates=candidates, underlying=underlying,
                r=_nearest_rf(rf, snap), q=div_yield_map.get(snap, 0.0),
            )
            _save_iv_cache(cache_p, record)

    records = []
    for snap in snap_dates:
        rec = _load_iv_cache(cache_path_fn(cache_dir, ticker, snap))
        records.append(rec if rec is not None else {
            "date": snap.isoformat(), "ticker": ticker, "iv_30d": None
        })

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values("date").reset_index(drop=True)


def _atm_call_record(
    *, client, ticker: str, snap: date, expiry: date, dte: int,
    candidates: list[float], underlying: float, r: float, q: float,
) -> dict:
    """Legacy call-only quote: mid if both sides quoted, else EOD close."""
    option_price = None
    used_strike  = None
    price_type   = None
    iv = float("nan")
    for s in candidates:
        try:
            df_eod = _theta_call(
                client.option_history_greeks_eod,
                start_date=snap, end_date=snap,
                symbol=ticker, expiration=expiry,
                strike=str(s), right="C",
            )
        except Exception:
            continue
        if df_eod is None or df_eod.empty:
            continue
        row   = df_eod.iloc[0]
        bid   = float(row.get("bid",   0) or 0)
        ask   = float(row.get("ask",   0) or 0)
        close = float(row.get("close", 0) or 0)
        if bid > 0 and ask > 0:
            option_price = (bid + ask) / 2.0
            price_type   = "mid"
        elif close >= _MIN_OPTION_PRICE:
            option_price = close
            price_type   = "close"
        if option_price is not None:
            used_strike = s
            iv = float(row.get("implied_vol", float("nan")))
            break

    if math.isnan(iv):
        logger.warning("%s %s exp=%s: no valid price near ATM.", ticker, snap, expiry)

    return {
        "date":             snap.isoformat(),
        "ticker":           ticker,
        "expiry":           expiry.isoformat(),
        "strike":           used_strike,
        "underlying_close": underlying,
        "option_price":     option_price,
        "price_type":       price_type,
        "days_to_expiry":   dte,
        "rf_annual":        r,
        "div_yield":        q,
        "iv_30d":           None if math.isnan(iv) else iv,
    }


def fetch_atm_iv_30d(
    ticker:         str,
    start_date:     str,
    end_date:       str,
    cache_dir:      str | Path = _IV_CACHE_DIR,
    theta_username: str | None = None,
    theta_password: str | None = None,
) -> pd.DataFrame:
    """Fetch 30-day ATM call IV for *ticker* over [start_date, end_date].

    Legacy call-only series (mid-price, close fallback, no spread filter).
    See ``fetch_atm_call_put_iv_30d`` for the quality-controlled combined
    series used by the main IV panel.

    Returns
    -------
    pd.DataFrame
        Columns: ``date, ticker, expiry, strike, underlying_close,
        option_price, price_type, days_to_expiry, rf_annual, div_yield, iv_30d``.
        Dates with no data or computation failures have ``iv_30d = NaN``.
    """
    return _fetch_atm_iv_series(
        ticker, start_date, end_date, cache_dir,
        theta_username or _THETADATA_USERNAME,
        theta_password or _THETADATA_PASSWORD,
        cache_path_fn=_iv_cache_path,
        record_fn=_atm_call_record,
        numeric_cols=("strike", "underlying_close", "option_price",
                      "days_to_expiry", "rf_annual", "div_yield", "iv_30d"),
    )


def _atm_call_put_record(
    *, client, ticker: str, snap: date, expiry: date, dte: int,
    candidates: list[float], underlying: float, r: float, q: float,
    max_rel_spread: float,
) -> dict:
    """Quality-controlled call/put quote at a common near-ATM strike.

    Both sides must have positive bid/ask and relative spread within
    *max_rel_spread*; the record's ``iv_30d`` is the median of the valid
    sides, with single-side fallback.
    """
    best: dict | None = None
    for strike in candidates:
        side_values: dict[str, dict] = {}
        for right, label in (("C", "call"), ("P", "put")):
            detail = _get_eod_detail(
                client, ticker, expiry, strike, snap, right=right
            )
            if detail is None or detail["bid"] <= 0 or detail["ask"] <= 0:
                continue
            mid = (detail["bid"] + detail["ask"]) / 2.0
            rel_spread = (detail["ask"] - detail["bid"]) / mid
            if rel_spread < 0 or rel_spread > max_rel_spread:
                continue
            iv = detail.get("iv", float("nan"))
            if math.isfinite(iv):
                side_values[label] = {
                    "iv": iv,
                    "price": mid,
                    "rel_spread": rel_spread,
                }

        if not side_values:
            continue
        candidate = {"strike": strike, "sides": side_values}
        if best is None:
            best = candidate
        if len(side_values) == 2:
            best = candidate
            break

    if best is None:
        return {
            "date": snap.isoformat(), "ticker": ticker,
            "expiry": expiry.isoformat(), "iv_30d": None,
            "reason": "no_quality_atm_quote",
        }

    sides      = best["sides"]
    call_iv    = sides.get("call", {}).get("iv", float("nan"))
    put_iv     = sides.get("put", {}).get("iv", float("nan"))
    side_ivs   = [iv for iv in (call_iv, put_iv) if math.isfinite(iv)]
    side_count = len(side_ivs)
    gap        = put_iv - call_iv if side_count == 2 else float("nan")
    return {
        "date": snap.isoformat(),
        "ticker": ticker,
        "expiry": expiry.isoformat(),
        "strike": best["strike"],
        "underlying_close": underlying,
        "days_to_expiry": dte,
        "rf_annual": r,
        "div_yield": q,
        "call_iv": call_iv if math.isfinite(call_iv) else None,
        "put_iv": put_iv if math.isfinite(put_iv) else None,
        "iv_30d": float(pd.Series(side_ivs).median()),
        "iv_side_count": side_count,
        "call_put_iv_gap": gap if math.isfinite(gap) else None,
        "abs_call_put_iv_gap": abs(gap) if math.isfinite(gap) else None,
        "call_rel_spread": sides.get("call", {}).get("rel_spread"),
        "put_rel_spread": sides.get("put", {}).get("rel_spread"),
        "iv_source": (
            "call_put_median" if side_count == 2
            else "call_only" if math.isfinite(call_iv)
            else "put_only"
        ),
    }


def fetch_atm_call_put_iv_30d(
    ticker:         str,
    start_date:     str,
    end_date:       str,
    cache_dir:      str | Path = _IV_CACHE_DIR,
    theta_username: str | None = None,
    theta_password: str | None = None,
    max_rel_spread: float = config.MAX_REL_SPREAD,
) -> pd.DataFrame:
    """Fetch weekly near-30-day ATM IV using quality-controlled calls and puts.

    A common near-ATM strike is used. The output IV is the median of valid call
    and put IVs, with a single-side fallback. Separate cache files keep this
    series independent from the legacy call-only cache.
    """
    return _fetch_atm_iv_series(
        ticker, start_date, end_date, cache_dir,
        theta_username or _THETADATA_USERNAME,
        theta_password or _THETADATA_PASSWORD,
        cache_path_fn=_call_put_iv_cache_path,
        record_fn=partial(_atm_call_put_record, max_rel_spread=max_rel_spread),
        numeric_cols=("strike", "underlying_close", "days_to_expiry", "rf_annual",
                      "div_yield", "call_iv", "put_iv", "iv_30d", "iv_side_count",
                      "call_put_iv_gap", "abs_call_put_iv_gap", "call_rel_spread",
                      "put_rel_spread"),
    )


# ---------------------------------------------------------------------------
# Chain cache helpers
# ---------------------------------------------------------------------------

def _chain_cache_path(cache_dir: Path, ticker: str, snap: date) -> Path:
    return cache_dir / ticker / f"{snap.isoformat()}_chain.json"


def _load_chain_cache(path: Path) -> list[dict] | None:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_chain_cache(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, default=str))


# ---------------------------------------------------------------------------
# Price loading helpers (batch, for run_screen)
# ---------------------------------------------------------------------------

def _load_prices_from_csv(
    tickers:  list[str],
    start:    str,
    end:      str,
    csv_path: Path = config.RAW_PRICES_CSV,
) -> dict[str, dict[date, float]]:
    """Read unadjusted EOD close prices from data/raw/prices.csv (wide format)."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Price CSV not found at {csv_path}. "
            "Run: python scripts/01_download_prices.py"
        )
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
    df = df[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))]

    result: dict[str, dict[date, float]] = {}
    for t in tickers:
        if t not in df.columns:
            logger.warning("%s not found in price CSV.", t)
            result[t] = {}
            continue
        col = df[t].dropna()
        result[t] = {d.date(): float(p) for d, p in col.items()}
    return result


# ---------------------------------------------------------------------------
# Public: full chain fetch
# ---------------------------------------------------------------------------

_LEAN_SCHEMA_COLS = (
    "ticker", "snap_date", "right", "expiry", "strike", "dte", "underlying",
    "bid", "ask", "close", "option_price", "price_type", "rf_annual", "div_yield",
    "iv", "delta", "gamma", "vega", "theta_daily",
    "dollar_delta", "dollar_gamma", "dollar_vega",
)


def fetch_full_chain(
    ticker:    str,
    snap:      date,
    client,
    underlying: float,
    rf_annual:  float,
    div_yield:  float,
    dte_min:    int       = 7,
    dte_max:    int       = 90,
    rights:      tuple[str, ...] = ("C",),
    cache_dir:   Path            = _SCREEN_CACHE_DIR,
    expirations: list[date] | None = None,
) -> pd.DataFrame:
    """Fetch every listed option for *ticker* on *snap* within [dte_min, dte_max].

    Parameters
    ----------
    rights : tuple of ``"C"`` and/or ``"P"``.  Default ``("C",)`` preserves
        backward compatibility with call-only caches.  Pass ``("C", "P")``
        for the full re-pull that includes puts.

    Caching
    -------
    Results are cached to ``cache_dir/{ticker}/{snap}_chain.json`` using a lean
    schema: ``ticker, snap_date, right, expiry, strike, dte, underlying, bid,
    ask, close, option_price, price_type, rf_annual, div_yield, iv, delta,
    gamma, vega, theta_daily, dollar_delta, dollar_gamma, dollar_vega,
    open_interest`` (open_interest absent from old caches; absent → NaN in
    downstream joins).
    Old caches lacking the ``right`` field are treated as calls-only and returned
    as-is (backward compatible read).

    EOD prices and OI are each fetched once per expiry using ThetaData's bulk
    endpoints (strike='*').  EOD falls back to per-contract calls when bulk
    retrieval is unavailable.  If bulk OI fails, open_interest is omitted from
    affected rows and ``compute_chain_capacity`` falls back to unweighted
    aggregation.

    Returns
    -------
    pd.DataFrame  — one row per (right, expiry, strike) with BSM greeks and,
    where available, open_interest.
    """
    cache_path   = _chain_cache_path(cache_dir, ticker, snap)
    cached       = _load_chain_cache(cache_path)
    supplement   = None   # cached rows to merge with freshly-fetched rows

    if cached is not None:
        if not cached:
            return pd.DataFrame()
        df = pd.DataFrame(cached)
        if "right" not in df.columns:
            df["right"] = "C"   # old pre-right-column cache → treat as calls
        cached_rights  = set(df["right"].unique())
        missing_rights = tuple(r for r in rights if r not in cached_rights)
        if not missing_rights:
            # All requested rights already cached — return immediately.
            df["snap_date"] = pd.to_datetime(df["snap_date"])
            df["expiry"]    = pd.to_datetime(df["expiry"]).dt.date
            return df
        # Partial cache: keep what we have, only fetch the missing rights.
        logger.info("%s %s: cache has %s; supplementing with %s.",
                    ticker, snap, sorted(cached_rights), sorted(missing_rights))
        supplement = df
        rights     = missing_rights   # narrow the upcoming fetch

    if expirations is None:
        expirations = _get_expirations(client, ticker)
    valid_exps = [e for e in expirations if dte_min <= (e - snap).days <= dte_max]

    if not valid_exps:
        logger.warning(
            "%s %s: no expirations in [%d, %d] DTE window.", ticker, snap, dte_min, dte_max
        )
        if supplement is not None:
            supplement["snap_date"] = pd.to_datetime(supplement["snap_date"])
            supplement["expiry"]    = pd.to_datetime(supplement["expiry"]).dt.date
            return supplement
        _save_chain_cache(cache_path, [])
        return pd.DataFrame()

    records: list[dict] = []

    for exp in valid_exps:
        dte = (exp - snap).days
        eod_map = _fetch_bulk_eod(client, ticker, exp, snap, rights)

        # One bulk OI call per expiry (all strikes × all rights).
        oi_map = _fetch_bulk_oi(client, ticker, exp, snap)

        if eod_map is None:
            # Compatibility path for older SDKs/subscriptions without bulk EOD.
            contract_details = []
            for strike in _get_strikes(client, ticker, exp):
                for right in rights:
                    detail = _get_eod_detail(
                        client, ticker, exp, strike, snap, right=right
                    )
                    if detail is not None:
                        contract_details.append((strike, right, detail))
        else:
            contract_details = [
                (strike, right, detail)
                for (strike, right), detail in eod_map.items()
            ]

        for strike, right, detail in contract_details:
            iv = detail.get("iv", float("nan"))
            if math.isnan(iv):
                continue

            delta = detail.get("delta", float("nan"))
            gamma = detail.get("gamma", float("nan"))
            vega = detail.get("vega", float("nan"))
            theta_daily = detail.get("theta_daily", float("nan"))

            dollar_delta = delta * underlying
            dollar_gamma = 0.5 * gamma * (underlying ** 2) * (0.01 ** 2)
            dollar_vega  = vega * 0.01

            record: dict = {
                "ticker":     ticker,
                "snap_date":  snap.isoformat(),
                "right":      right,
                "expiry":     exp.isoformat(),
                "strike":     strike,
                "dte":        dte,
                "underlying": underlying,
                **detail,
                "rf_annual":  rf_annual,
                "div_yield":  div_yield,
                "dollar_delta": dollar_delta,
                "dollar_gamma": dollar_gamma,
                "dollar_vega":  dollar_vega,
            }

            oi = oi_map.get((float(strike), right))
            if oi is not None:
                record["open_interest"] = oi

            records.append(record)

    if not records:
        if supplement is not None:
            # Partial cache hit: supplement fetch returned nothing (puts unavailable).
            # Return what we already had rather than caching an empty result.
            supplement["snap_date"] = pd.to_datetime(supplement["snap_date"])
            supplement["expiry"]    = pd.to_datetime(supplement["expiry"]).dt.date
            return supplement
        _save_chain_cache(cache_path, [])
        return pd.DataFrame()

    new_df = pd.DataFrame(records)
    new_df["snap_date"] = pd.to_datetime(new_df["snap_date"])
    new_df["expiry"]    = pd.to_datetime(new_df["expiry"]).dt.date

    if supplement is not None:
        supplement["snap_date"] = pd.to_datetime(supplement["snap_date"])
        supplement["expiry"]    = pd.to_datetime(supplement["expiry"]).dt.date
        combined = pd.concat([supplement, new_df], ignore_index=True)
        _save_chain_cache(cache_path, combined.to_dict("records"))
        return combined

    _save_chain_cache(cache_path, records)
    return new_df


# ---------------------------------------------------------------------------
# Public: screen_chain
# ---------------------------------------------------------------------------

def screen_chain(
    chain_df:         pd.DataFrame,
    max_rel_spread:   float = 0.25,
    dte_min:          int   = 14,
    dte_max:          int   = 90,
    delta_lo:         float = 0.10,
    delta_hi:         float = 0.90,
    min_dollar_delta: float = 5.0,
    min_dollar_gamma: float = 0.001,
    min_dollar_vega:  float = 0.01,
) -> dict:
    """Apply tradeability + economic-significance filters to a raw chain DataFrame.

    Filter criteria (all must hold):
      bid > 0 AND ask > 0 AND mid > 0
      (ask - bid) / mid  <= max_rel_spread
      dte                in [dte_min, dte_max]
      abs(delta)         in [delta_lo, delta_hi]
      dollar_delta       >= min_dollar_delta
      dollar_gamma       >= min_dollar_gamma
      dollar_vega        >= min_dollar_vega

    Thresholds held constant across the sample (calibrated 2020-Q1–2025-Q2).
    See src/config.py for the canonical constant values.

    Returns
    -------
    dict with keys:
        ``"passing"``  — contracts surviving all filters; includes a
                         ``quality`` bool column and ``rel_spread``.
        ``"summary"``  — one row per (ticker, snap_date) with total/passing
                         counts, pass_rate, and median Greeks on passing rows.
    """
    if chain_df.empty:
        return {"passing": pd.DataFrame(), "summary": pd.DataFrame()}

    work = chain_df.copy()

    # Compute mid and rel_spread (required even when bid=0 so the mask is clean)
    bid = work["bid"].fillna(0)
    ask = work["ask"].fillna(0)
    mid = (bid + ask) / 2.0
    work["mid"]        = mid
    work["rel_spread"] = (ask - bid) / mid.replace(0.0, float("nan"))
    work["abs_delta"]  = work["delta"].abs()

    mask = (
        (bid > 0) & (ask > 0) & (mid > 0)
        & (work["rel_spread"] <= max_rel_spread)
        & (work["dte"].between(dte_min, dte_max))
        & (work["abs_delta"].between(delta_lo, delta_hi))
        & (work["dollar_delta"].abs() >= min_dollar_delta)
        & (work["dollar_gamma"] >= min_dollar_gamma)
        & (work["dollar_vega"]  >= min_dollar_vega)
    )
    work["quality"] = mask
    passing = work[mask].copy()

    group_keys = ["ticker", "snap_date"]
    total  = work.groupby(group_keys).size().rename("total_contracts")
    n_pass = passing.groupby(group_keys).size().rename("passing_contracts")

    greek_cols = ["dollar_vega", "dollar_gamma", "dollar_delta", "iv"]
    available  = [c for c in greek_cols if c in passing.columns]
    greek_medians = (
        passing.groupby(group_keys)[available]
        .median()
        .rename(columns={c: f"median_{c}" for c in available})
    )

    # ── Liquidity screeners: each of the form √N × g(quality), g ∈ (0, 1] ────
    # N = quality OI premium notional. Every screener is therefore monotone
    # increasing in √N; g encodes a depth-free quality dimension.
    if "open_interest" in passing.columns:
        oi = passing["open_interest"].fillna(0).clip(lower=0)
    else:
        oi = pd.Series(0.0, index=passing.index)
    passing["oi_premium_notional"] = oi * 100.0 * passing["mid"]

    if "theta_daily" in passing.columns:
        passing["theta_notional"] = oi * 100.0 * passing["theta_daily"].abs()
    else:
        passing["theta_notional"] = 0.0

    notional      = passing.groupby(group_keys)["oi_premium_notional"].sum()
    theta_not     = passing.groupby(group_keys)["theta_notional"].sum()
    side_notional = (
        passing.groupby(group_keys + ["right"])["oi_premium_notional"].sum()
        .unstack("right")
        .reindex(columns=["C", "P"])
        .fillna(0.0)
    )
    both  = side_notional["C"] + side_notional["P"]
    balance = (2.0 * side_notional[["C", "P"]].min(axis=1)
               / both.replace(0.0, float("nan"))).fillna(0.0)
    spread_med = passing.groupby(group_keys)["rel_spread"].median()

    liq = pd.DataFrame({
        "quality_oi_notional": notional,
        "sqrt_oi_notional":    notional.pow(0.5),
        "theta_notional":      theta_not,
        "sqrt_theta_notional": theta_not.pow(0.5),
        "book_balance":        balance,
        "median_quality_spread": spread_med,
    })
    liq["cost_adj_depth"] = liq["sqrt_oi_notional"] * (1.0 - liq["median_quality_spread"]).clip(lower=0.0)
    liq["balanced_depth"] = liq["sqrt_oi_notional"] * liq["book_balance"]
    liq["liq_score"] = (
        liq["sqrt_oi_notional"]
        * (1.0 - liq["median_quality_spread"]).clip(lower=0.0)
        * liq["book_balance"]
    )

    summary = (
        pd.concat([total, n_pass], axis=1)
        .fillna({"passing_contracts": 0})
        .join(greek_medians, how="left")
        .join(liq, how="left")
        .reset_index()
    )
    summary["pass_rate"] = (
        summary["passing_contracts"] / summary["total_contracts"]
    ).round(4)

    return {"passing": passing, "summary": summary}


# ---------------------------------------------------------------------------
# Public: run_screen
# ---------------------------------------------------------------------------

def run_screen(
    tickers:          list[str],
    snap_dates:       list[str],
    dte_min:          int             = config.DTE_MIN,
    dte_max:          int             = config.DTE_MAX,
    rights:           tuple[str, ...] = ("C",),
    max_rel_spread:   float           = config.MAX_REL_SPREAD,
    delta_lo:         float           = config.DELTA_LO,
    delta_hi:         float           = config.DELTA_HI,
    min_dollar_delta: float           = config.MIN_DOLLAR_DELTA,
    min_dollar_gamma: float           = config.MIN_DOLLAR_GAMMA,
    min_dollar_vega:  float           = config.MIN_DOLLAR_VEGA,
    cache_dir:        Path            = _SCREEN_CACHE_DIR,
    theta_username:   str | None      = None,
    theta_password:   str | None      = None,
    max_workers:      int             = 1,
) -> dict:
    """Run the full option liquidity screen for *tickers* on *snap_dates*.

    Parameters
    ----------
    rights : which rights to pull; ``("C",)`` for calls-only (backward compat),
        ``("C", "P")`` for the full hedge-capacity re-pull.
    max_workers : fetch workers (default 1).  ThetaData enforces a single
        session per account and rejects concurrent gRPC requests with
        RESOURCE_EXHAUSTED, so serial is the only reliable setting.  Cache
        hits skip the API entirely, so a warm cache benefits from higher
        values if your subscription allows it.

    Returns
    -------
    dict with keys ``"chains"``, ``"passing"``, ``"summary"``, ``"ticker_summary"``.
    ``"ticker_summary"`` has a ``liquid`` flag (``median_liq_score >= LIQUIDITY_SCORE_MIN``).
    """
    username = theta_username or _THETADATA_USERNAME
    password = theta_password or _THETADATA_PASSWORD
    snaps    = [date.fromisoformat(d) for d in snap_dates]

    all_start = str(min(snaps) - timedelta(days=7))
    all_end   = str(max(snaps) + timedelta(days=1))

    logger.info("Loading prices for %d tickers from CSV ...", len(tickers))
    prices_all = _load_prices_from_csv(tickers, all_start, all_end)

    rf = _rf_map(all_start, all_end)

    # ── Serial pre-fetch: expirations + div yields (one call per ticker) ──────
    setup_client   = _make_client(username, password)
    work_items: list[tuple] = []

    for ticker in tickers:
        logger.info("Pre-fetching %s …", ticker)
        prices        = prices_all.get(ticker, {})
        div_yield_map = _historical_div_yield_map(ticker, all_start, all_end, prices)
        expirations   = _get_expirations(setup_client, ticker)
        time.sleep(0.5)   # pace expirations pre-fetch to avoid RESOURCE_EXHAUSTED

        for snap in snaps:
            underlying = prices.get(snap)
            if underlying is None:
                for lag in range(1, 8):
                    underlying = prices.get(snap - timedelta(days=lag))
                    if underlying is not None:
                        break
            if underlying is None:
                logger.warning("%s %s: no underlying price; skipping.", ticker, snap)
                continue
            work_items.append((
                ticker, snap,
                underlying, _nearest_rf(rf, snap), div_yield_map.get(snap, 0.0),
                expirations,
            ))

    # ── Parallel chain fetch ───────────────────────────────────────────────────
    logger.info(
        "Fetching %d (ticker, snap) chains with %d workers …",
        len(work_items), max_workers,
    )

    def _fetch_one(args: tuple) -> pd.DataFrame:
        t, snap, ul, rf_ann, dv, exps = args
        return fetch_full_chain(
            t, snap, setup_client,
            underlying=ul, rf_annual=rf_ann, div_yield=dv,
            dte_min=dte_min, dte_max=dte_max, rights=rights,
            cache_dir=cache_dir, expirations=exps,
        )

    all_chains: list[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, item): item for item in work_items}
        for fut in as_completed(futures):
            try:
                df = fut.result()
                if not df.empty:
                    all_chains.append(df)
            except Exception as exc:
                item = futures[fut]
                logger.warning(
                    "Chain fetch failed for %s %s: %s", item[0], item[1], exc
                )

    if not all_chains:
        return {k: pd.DataFrame() for k in ("chains", "passing", "summary", "ticker_summary")}

    chains_df = pd.concat(all_chains, ignore_index=True)
    screen    = screen_chain(
        chains_df,
        max_rel_spread=max_rel_spread,
        dte_min=dte_min,
        dte_max=dte_max,
        delta_lo=delta_lo,
        delta_hi=delta_hi,
        min_dollar_delta=min_dollar_delta,
        min_dollar_gamma=min_dollar_gamma,
        min_dollar_vega=min_dollar_vega,
    )

    summary = screen["summary"]
    ticker_summary = _build_ticker_summary(summary)

    return {
        "chains":         chains_df,
        "passing":        screen["passing"],
        "summary":        summary,
        "ticker_summary": ticker_summary,
    }


def _build_ticker_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the per-(ticker, snap) screen summary to one row per ticker.

    The ``liquid`` gate thresholds the median composite liquidity score
    (``liq_score`` = √N × (1 − spread) × book balance, N = quality OI premium
    notional) — monotone increasing in √N by construction.
    """
    if summary.empty:
        return pd.DataFrame()

    agg_cols: dict = {
        "dates_screened": ("snap_date", "count"),
        "mean_pass_rate": ("pass_rate", "mean"),
        "median_iv":      ("median_iv", "median"),
    }
    for mc in ("median_dollar_vega", "median_dollar_gamma", "median_dollar_delta"):
        if mc in summary.columns:
            agg_cols[mc] = (mc, "median")
    for lc in ("sqrt_oi_notional", "sqrt_theta_notional", "cost_adj_depth", "balanced_depth", "liq_score"):
        if lc in summary.columns:
            agg_cols[f"median_{lc}"] = (lc, "median")

    ticker_summary = summary.groupby("ticker").agg(**agg_cols).reset_index()
    if "median_liq_score" in ticker_summary.columns:
        ticker_summary["liquid"] = (
            ticker_summary["median_liq_score"].fillna(0.0) >= LIQUIDITY_SCORE_MIN
        )
    else:
        ticker_summary["liquid"] = False
    return ticker_summary


# ---------------------------------------------------------------------------
# Public: concat_results
# ---------------------------------------------------------------------------

def concat_results(
    cache_dir:        Path  = _SCREEN_CACHE_DIR,
    out_dir:          Path  = config.PROCESSED_DIR / "options_screen",
    max_rel_spread:   float = config.MAX_REL_SPREAD,
    dte_min:          int   = config.DTE_MIN,
    dte_max:          int   = config.DTE_MAX,
    delta_lo:         float = config.DELTA_LO,
    delta_hi:         float = config.DELTA_HI,
    min_dollar_delta: float = config.MIN_DOLLAR_DELTA,
    min_dollar_gamma: float = config.MIN_DOLLAR_GAMMA,
    min_dollar_vega:  float = config.MIN_DOLLAR_VEGA,
) -> dict:
    """Combine all cached chain JSONs into CSVs.

    Walks every ``{ticker}/*_chain.json`` under *cache_dir*, concatenates
    records, applies the tradeability+economic-significance filter, and writes:

    - ``chains.csv``         — full raw chain (lean schema)
    - ``summary.csv``        — one row per (ticker, snap_date)
    - ``ticker_summary.csv`` — one row per ticker aggregated across dates

    Returns
    -------
    dict with keys ``"chains"``, ``"passing"``, ``"summary"``, ``"ticker_summary"``.
    """
    all_records: list[dict] = []
    for json_path in sorted(cache_dir.rglob("*_chain.json")):
        try:
            records = json.loads(json_path.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Skipping unreadable cache file: %s", json_path)
            continue
        if records:
            all_records.extend(records)

    if not all_records:
        logger.warning("No chain records found under %s.", cache_dir)
        return {k: pd.DataFrame() for k in ("chains", "passing", "summary", "ticker_summary")}

    chains_df = pd.DataFrame(all_records)
    chains_df["snap_date"] = pd.to_datetime(chains_df["snap_date"])
    chains_df["expiry"]    = pd.to_datetime(chains_df["expiry"]).dt.date
    if "right" not in chains_df.columns:
        chains_df["right"] = "C"  # back-compat: old call-only caches

    screen  = screen_chain(
        chains_df,
        max_rel_spread=max_rel_spread,
        dte_min=dte_min,
        dte_max=dte_max,
        delta_lo=delta_lo,
        delta_hi=delta_hi,
        min_dollar_delta=min_dollar_delta,
        min_dollar_gamma=min_dollar_gamma,
        min_dollar_vega=min_dollar_vega,
    )
    summary = screen["summary"]
    ticker_summary = _build_ticker_summary(summary)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chains_df.to_csv(out_dir / "chains.csv", index=False)
    summary.to_csv(out_dir / "summary.csv", index=False)
    if not ticker_summary.empty:
        ticker_summary.to_csv(out_dir / "ticker_summary.csv", index=False)

    logger.info(
        "Wrote %d chain rows, %d summary rows, %d ticker rows → %s",
        len(chains_df), len(summary),
        len(ticker_summary) if not ticker_summary.empty else 0,
        out_dir,
    )
    return {
        "chains":         chains_df,
        "passing":        screen["passing"],
        "summary":        summary,
        "ticker_summary": ticker_summary,
    }


# ---------------------------------------------------------------------------
# Public: IV-realized spread panel
# ---------------------------------------------------------------------------

def build_iv_spread_panel(
    iv_df:      pd.DataFrame,
    core_df:    pd.DataFrame | None = None,
    panel_path: str | None = None,
) -> pd.DataFrame:
    """Join IV and realised-vol series and compute the spread.

    Parameters
    ----------
    iv_df : pd.DataFrame
        Output of ``fetch_atm_iv_30d`` (one or more tickers concatenated).
        Must contain columns: ``date, ticker, iv_30d``.
    core_df : pd.DataFrame | None
        Pre-loaded core panel slice; loaded from *panel_path* if None.
    panel_path : str | None
        Path to core_panel.csv; used only when ``core_df`` is None.

    Returns
    -------
    pd.DataFrame
        Columns: ``date, ticker, vol_12w, vol_12w_annualized, iv_30d,
        iv_realized_spread, fwd_ret_4w, fwd_maxdd_12w, fwd_vol_12w``.
        Dates in the core panel absent from IV produce NaN rather than being
        dropped.
    """
    _CORE_COLS = ["Date", "Symbol", "Return", "vol_12w",
                  "fwd_ret_4w", "fwd_maxdd_12w", "fwd_vol_12w"]

    if core_df is None:
        path    = panel_path or str(config.core_panel_csv("offline"))
        core_df = pd.read_csv(path, usecols=_CORE_COLS, parse_dates=["Date"])

    core = core_df.rename(columns={"Date": "date", "Symbol": "ticker"}).copy()
    core["date"] = pd.to_datetime(core["date"])

    diagnostic_cols = [
        col for col in [
            "call_iv", "put_iv", "iv_side_count", "call_put_iv_gap",
            "abs_call_put_iv_gap", "call_rel_spread", "put_rel_spread",
            "iv_source",
        ]
        if col in iv_df.columns
    ]
    iv = iv_df[["date", "ticker", "iv_30d", *diagnostic_cols]].copy()
    iv["date"] = pd.to_datetime(iv["date"])

    merged = core.merge(iv, on=["date", "ticker"], how="left")
    merged["vol_12w_annualized"] = merged["vol_12w"] * _ANNUALISE_FACTOR
    merged["iv_realized_spread"] = merged["iv_30d"] - merged["vol_12w_annualized"]

    out_cols = ["date", "ticker", "vol_12w", "vol_12w_annualized",
                "iv_30d", *diagnostic_cols, "iv_realized_spread",
                "fwd_ret_4w", "fwd_maxdd_12w", "fwd_vol_12w"]
    return (
        merged[out_cols]
        .sort_values(["ticker", "date"])
        .reset_index(drop=True)
    )
