"""Explicit price/distribution accounting for fixed-share ETF holdings."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

FIELDS = ["close", "adj_close", "dividends", "capital_gains", "splits"]


def validate_market(frame: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    missing = set(["date", "ticker", *FIELDS]) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing market columns: {sorted(missing)}")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    if frame[["date", "ticker"]].isna().any().any() or frame.duplicated(["date", "ticker"]).any():
        raise ValueError("Null or duplicate market key")
    if set(frame.ticker) != set(tickers):
        raise ValueError("Market ticker set does not match configuration")
    frame[FIELDS] = frame[FIELDS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(frame[FIELDS]).all().all():
        raise ValueError("Nonfinite market data; no filling is permitted")
    if (frame[["close", "adj_close"]] <= 0).any().any():
        raise ValueError("Market prices must be positive")
    if (frame[["dividends", "capital_gains", "splits"]] < 0).any().any():
        raise ValueError("Negative corporate action")
    if frame.splits.ne(0).any():
        raise ValueError("Split-aware holdings/deliverables are not implemented")
    counts = frame.groupby("date").ticker.nunique()
    if not counts.eq(len(tickers)).all():
        raise ValueError("Unaligned market dates; do not drop missing ticker observations")
    return frame.sort_values(["date", "ticker"]).reset_index(drop=True)


def load_market(path: Path, tickers: list[str]) -> pd.DataFrame:
    return validate_market(pd.read_csv(path), tickers)


def market_panels(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = frame.pivot(index="date", columns="ticker", values="close").sort_index()
    cash = frame.assign(cash=frame.dividends + frame.capital_gains).pivot(
        index="date", columns="ticker", values="cash").reindex(prices.index)
    return prices, cash


def holding_return(prices: pd.DataFrame, cash: pd.DataFrame,
                   start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.Series, pd.Series]:
    """Fixed shares; ex-date entitlement on (start, end], cash retained at par."""
    if start not in prices.index or end not in prices.index or end <= start:
        raise ValueError("Holding window needs exact, increasing market dates")
    price_return = prices.loc[end] / prices.loc[start] - 1
    cash_return = cash.loc[(cash.index > start) & (cash.index <= end)].sum() / prices.loc[start]
    return price_return, cash_return


def historical_scenarios(prices: pd.DataFrame, cash: pd.DataFrame, decision: pd.Timestamp,
                         expiry: pd.Timestamp, lookback_years: int) -> pd.DataFrame:
    """Joint overlapping windows with the holding period's trading-session count."""
    if decision not in prices.index or expiry not in prices.index or expiry <= decision:
        raise ValueError("Missing exact decision/expiry price")
    horizon = int(((prices.index > decision) & (prices.index <= expiry)).sum())
    dates = prices.index[(prices.index >= decision - pd.DateOffset(years=lookback_years))
                         & (prices.index < decision)]
    if len(dates) <= horizon:
        raise ValueError("Insufficient strictly historical scenario data")
    rows = []
    for i in range(len(dates) - horizon):
        start, end = dates[i], dates[i + horizon]
        pr, cr = holding_return(prices, cash, start, end)
        row = {"scenario_id": i, "window_start": start, "window_end": end,
               "trading_sessions": horizon, "calendar_days": (end - start).days}
        for ticker in prices.columns:
            row[f"{ticker}_price_return"] = float(pr[ticker])
            row[f"{ticker}_cash_return"] = float(cr[ticker])
        rows.append(row)
    result = pd.DataFrame(rows)
    result["weight"] = 1 / len(result)
    return result


def adjustment_diagnostic(frame: pd.DataFrame) -> pd.DataFrame:
    """Vendor-internal check only, not independent issuer confirmation."""
    rows = []
    for ticker, group in frame.groupby("ticker"):
        group = group.sort_values("date")
        explicit = (group.close + group.dividends + group.capital_gains) / group.close.shift() - 1
        adjusted = group.adj_close.pct_change(fill_method=None)
        gap = (explicit - adjusted).abs().dropna()
        rows.append({"ticker": ticker, "rows": len(group),
                     "distribution_events": int((group.dividends + group.capital_gains).gt(0).sum()),
                     "max_daily_return_gap_bps": float(gap.max() * 10000),
                     "check": "vendor_internal_not_independent"})
    return pd.DataFrame(rows)
