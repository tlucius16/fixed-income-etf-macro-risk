from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from src import config


METADATA_COLUMNS = ["Symbol", "Name", "Assets", "ETF Database Category", "ER", "Inception"]


def load_etfdb_screener(path: str | Path, skiprows: int | None = None) -> pd.DataFrame:
    """Load the ETFDB screener export used to define the ETF universe."""
    if skiprows is not None:
        return pd.read_csv(path, skiprows=skiprows)

    preview = pd.read_csv(path, nrows=0)
    if "Symbol" in preview.columns:
        return pd.read_csv(path)
    return pd.read_csv(path, skiprows=1)


def clean_symbols(symbols: pd.Series) -> pd.Series:
    """Clean ETF symbols for yfinance compatibility."""
    return symbols.dropna().astype(str).str.upper().str.replace(".", "-", regex=False)


def select_metadata(database: pd.DataFrame) -> pd.DataFrame:
    """Keep the metadata columns used by the prototype pipeline."""
    missing = [col for col in METADATA_COLUMNS if col not in database.columns]
    if missing:
        raise ValueError(f"Missing required metadata columns: {missing}")

    metadata = database[METADATA_COLUMNS].copy()
    metadata["Symbol"] = clean_symbols(metadata["Symbol"])
    metadata["Inception"] = pd.to_datetime(metadata["Inception"], errors="coerce")
    return metadata.dropna(subset=["Symbol"])


def get_ticker_list(database: pd.DataFrame) -> list[str]:
    return clean_symbols(database["Symbol"]).drop_duplicates().tolist()


def filter_tickers_by_min_history(
    tickers: list[str],
    min_years: int = config.DEFAULT_MIN_HISTORY_YEARS,
    sleep_seconds: float = config.YAHOO_SLEEP_SECONDS,
) -> tuple[list[str], list[str]]:
    """Filter tickers by available yfinance history span."""
    min_days = min_years * 365
    valid_tickers: list[str] = []
    invalid_tickers: list[str] = []

    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).history(
                period=config.DEFAULT_PRICE_PERIOD,
                interval=config.DEFAULT_PRICE_INTERVAL,
                auto_adjust=True,
            )
            if data.empty:
                invalid_tickers.append(ticker)
                continue
            history_span = (data.index.max() - data.index.min()).days
            if history_span >= min_days:
                valid_tickers.append(ticker)
            else:
                invalid_tickers.append(ticker)
        except Exception:
            invalid_tickers.append(ticker)
        time.sleep(sleep_seconds)

    return valid_tickers, invalid_tickers


def build_universe(
    screener_csv: str | Path,
    min_years: int = config.DEFAULT_MIN_HISTORY_YEARS,
    filter_history: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    database = load_etfdb_screener(screener_csv)
    metadata = select_metadata(database)
    tickers = get_ticker_list(database)

    if filter_history:
        tickers, _ = filter_tickers_by_min_history(tickers, min_years=min_years)

    metadata = metadata[metadata["Symbol"].isin(tickers)].copy()
    return metadata, tickers
