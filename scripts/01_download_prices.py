"""Download unadjusted EOD close prices for all core panel tickers via yfinance.

Saves a wide-format CSV: rows = dates, columns = tickers.

Usage
-----
    python scripts/01_download_prices.py
    python scripts/01_download_prices.py --start 2010-01-01 --out data/raw/prices.csv
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from src import config

_DEFAULT_START = "2010-01-01"
_DEFAULT_OUT   = config.RAW_DIR / "prices.csv"
_BATCH_SIZE    = 50   # tickers per yf.download call
_BATCH_SLEEP   = 2.0  # seconds between batches


def download_raw_prices(
    tickers: list[str],
    start: str = _DEFAULT_START,
    out: Path = _DEFAULT_OUT,
) -> pd.DataFrame:
    all_frames: list[pd.DataFrame] = []
    batches = [tickers[i:i + _BATCH_SIZE] for i in range(0, len(tickers), _BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"Batch {i+1}/{len(batches)}: {len(batch)} tickers ...")
        for attempt in range(3):
            try:
                hist = yf.download(
                    batch,
                    start=start,
                    auto_adjust=False,
                    group_by="ticker",
                    threads=False,
                    progress=False,
                )
                break
            except YFRateLimitError:
                wait = _BATCH_SLEEP * 2 ** attempt
                print(f"  Rate limited — waiting {wait:.0f}s ...")
                time.sleep(wait)
        else:
            print(f"  Skipping batch after 3 failures.")
            continue

        if hist.empty:
            continue

        is_multi = isinstance(hist.columns, pd.MultiIndex)
        for t in batch:
            try:
                # yfinance group_by="ticker" → MultiIndex order is (ticker, price_type)
                col = hist[t]["Close"].dropna() if is_multi else hist["Close"].dropna()
                col.name = t
                all_frames.append(col)
            except KeyError:
                pass

        if i < len(batches) - 1:
            time.sleep(_BATCH_SLEEP)

    if not all_frames:
        print("No data downloaded.")
        return pd.DataFrame()

    prices = pd.concat(all_frames, axis=1)
    prices.index = pd.to_datetime(prices.index, utc=True).tz_convert(None)
    prices.index.name = "Date"
    prices.sort_index(inplace=True)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(out)
    print(f"Saved {prices.shape[1]} tickers × {len(prices)} dates → {out}")
    return prices


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default=_DEFAULT_START)
    p.add_argument("--out",   default=str(_DEFAULT_OUT))
    args = p.parse_args()

    tickers = pd.read_csv(config.CORE_PANEL_CSV)["Symbol"].unique().tolist()
    print(f"Downloading prices for {len(tickers)} tickers from {args.start} ...")
    download_raw_prices(tickers, start=args.start, out=Path(args.out))


if __name__ == "__main__":
    main()
