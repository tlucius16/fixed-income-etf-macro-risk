from __future__ import annotations

import time
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import yfinance as yf  # type: ignore[import-untyped]

from src import config


METADATA_COLUMNS = ["Symbol", "Name", "Assets", "ETF Database Category", "ER", "Inception"]
LFS_POINTER_PREFIX = "version https://git-lfs.github.com/spec/v1"


class DataFileUnavailableError(ValueError):
    """Raised when a configured data file exists but is not usable as CSV data."""


def is_lfs_pointer(path: str | Path) -> bool:
    """Return True when *path* is a Git LFS pointer instead of hydrated data."""
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        return False

    try:
        with candidate.open("r", encoding="utf-8") as handle:
            first_line = handle.readline().strip()
    except UnicodeDecodeError:
        return False

    return first_line == LFS_POINTER_PREFIX


def load_etfdb_screener(path: str | Path, skiprows: int | None = None) -> pd.DataFrame:
    """Load the ETFDB screener export used to define the ETF universe."""
    if is_lfs_pointer(path):
        raise DataFileUnavailableError(
            f"{path} is a Git LFS pointer, not a hydrated CSV. Run `git lfs pull` "
            "or use an already-built processed panel as the metadata fallback."
        )

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


def metadata_from_processed_panel(path: str | Path) -> pd.DataFrame:
    """Recover one metadata row per ETF from a previously-built core panel."""
    panel_path = Path(path)
    if is_lfs_pointer(panel_path):
        raise DataFileUnavailableError(f"{panel_path} is a Git LFS pointer, not a hydrated CSV.")

    metadata = pd.read_csv(panel_path, usecols=METADATA_COLUMNS)
    metadata = select_metadata(metadata)
    return metadata.drop_duplicates("Symbol").reset_index(drop=True)


def load_metadata_fallback(paths: list[str | Path]) -> pd.DataFrame:
    """Load ETF metadata from the first usable processed panel in *paths*."""
    skipped: list[str] = []
    for path in paths:
        candidate = Path(path)
        if not candidate.exists():
            skipped.append(f"{candidate} (missing)")
            continue
        try:
            return metadata_from_processed_panel(candidate)
        except (DataFileUnavailableError, ValueError) as exc:
            skipped.append(f"{candidate} ({exc})")

    raise DataFileUnavailableError(
        "No usable ETF metadata source found. Tried: " + "; ".join(skipped)
    )


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
    metadata_fallback_paths: list[str | Path] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    try:
        database = load_etfdb_screener(screener_csv)
        metadata = select_metadata(database)
        tickers = get_ticker_list(database)
    except DataFileUnavailableError:
        fallback_paths = metadata_fallback_paths or [
            config.core_panel_csv("live"),
            config.core_panel_csv("offline"),
        ]
        metadata = load_metadata_fallback(fallback_paths)
        tickers = get_ticker_list(metadata)

    if filter_history:
        tickers, _ = filter_tickers_by_min_history(tickers, min_years=min_years)

    metadata = metadata[metadata["Symbol"].isin(tickers)].copy()
    return metadata, tickers
