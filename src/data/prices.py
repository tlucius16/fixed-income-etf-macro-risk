from __future__ import annotations

import time

import pandas as pd
import yfinance as yf

from src import config


def clean_datetime_index(series: pd.Series) -> pd.Series:
    out = series.copy()
    out.index = pd.to_datetime(out.index, errors="coerce", utc=True).tz_localize(None)
    out = out[~out.index.isna()]
    return out.sort_index()


def download_price_history(
    tickers: list[str],
    period: str = config.DEFAULT_PRICE_PERIOD,
    interval: str = config.DEFAULT_PRICE_INTERVAL,
    sleep_seconds: float = config.YAHOO_SLEEP_SECONDS,
) -> dict[str, pd.Series]:
    etf_prices_data: dict[str, pd.Series] = {}

    for ticker in tickers:
        try:
            history = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
            if history.empty or "Close" not in history:
                continue
            close = clean_datetime_index(history["Close"].rename(ticker))
            if not close.empty:
                etf_prices_data[ticker] = close
        except Exception as exc:
            print(f"[yfinance] {ticker}: {exc}")
        time.sleep(sleep_seconds)

    return etf_prices_data


def build_daily_price_matrix(etf_prices_data: dict[str, pd.Series]) -> pd.DataFrame:
    return pd.DataFrame(etf_prices_data).sort_index()


def build_weekly_close_matrix(raw_prices: pd.DataFrame) -> pd.DataFrame:
    weekly_prices = raw_prices.copy()
    weekly_prices.index = pd.to_datetime(weekly_prices.index, errors="coerce", utc=True).tz_localize(None)
    weekly_prices = weekly_prices[~weekly_prices.index.isna()].sort_index()
    return weekly_prices.resample("W-FRI").last().dropna(how="all")


def build_weekly_returns(weekly_prices: pd.DataFrame) -> pd.DataFrame:
    return weekly_prices.pct_change().dropna(how="all")


def reshape_weekly_returns_long(returns_w: pd.DataFrame) -> pd.DataFrame:
    returns_w_long = (
        returns_w.reset_index()
        .rename(columns={returns_w.index.name or "index": "Date"})
        .melt(id_vars="Date", var_name="Symbol", value_name="Return")
        .dropna(subset=["Return"])
        .sort_values(["Symbol", "Date"])
        .reset_index(drop=True)
    )
    returns_w_long["Date"] = pd.to_datetime(returns_w_long["Date"], errors="coerce")
    return returns_w_long.dropna(subset=["Date"])
