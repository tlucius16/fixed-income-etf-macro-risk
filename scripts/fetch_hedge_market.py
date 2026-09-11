"""Explicit online acquisition; never called by the offline experiment runner."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.hedge_inputs import sha256_file
from src.hedge_design.market import validate_market


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--end", default="2025-02-01", help="Exclusive vendor end date")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", args.dataset_id):
        parser.error("Use a simple dataset ID, not a path")
    destination = ROOT / "data/raw/hedge_design" / f"{args.dataset_id}.csv"
    manifest_path = ROOT / "data/manifests" / f"{args.dataset_id}.json"
    if destination.exists() or manifest_path.exists():
        parser.error("Dataset already exists; choose a new ID")

    import pandas as pd
    import yfinance as yf

    tickers = ["LQD", "TLT", "IEF"]
    frames = []
    for ticker in tickers:
        history = yf.Ticker(ticker).history(start=args.start, end=args.end,
                                           auto_adjust=False, actions=True)
        required = ["Close", "Adj Close", "Dividends", "Capital Gains", "Stock Splits"]
        if history.empty or not set(required).issubset(history.columns):
            raise ValueError(f"Incomplete vendor response for {ticker}; no zero-action inference")
        data = history[required].rename(columns={"Close": "close", "Adj Close": "adj_close",
                "Dividends": "dividends", "Capital Gains": "capital_gains", "Stock Splits": "splits"})
        data.insert(0, "ticker", ticker)
        data.insert(0, "date", history.index.tz_localize(None).normalize())
        frames.append(data.reset_index(drop=True))
        print(f"{ticker}: {len(data):,} rows", flush=True)
    frame = validate_market(pd.concat(frames, ignore_index=True), tickers)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, mode="x")
    manifest = {"dataset_id": args.dataset_id, "provider": "Yahoo Finance via yfinance",
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "request": {"tickers": tickers, "start": args.start, "end_exclusive": args.end,
                            "auto_adjust": False, "actions": True},
                "yfinance_version": importlib.metadata.version("yfinance"),
                "source_url": "https://finance.yahoo.com/quote/LQD/history/",
                "path": destination.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(destination), "rows": len(frame),
                "first_date": str(frame.date.min().date()), "last_date": str(frame.date.max().date()),
                "conventions": {"prices": "Vendor Close; no splits allowed by pilot validator",
                    "distributions": "Vendor ex-date amounts, not payment dates; revised vintage",
                    "adj_close": "Internal diagnostic only; never an option settlement price",
                    "independent_issuer_verification": False}}
    with manifest_path.open("x") as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(manifest_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
