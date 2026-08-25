"""Rebuild the screen outputs from the cached chain JSONs (no API calls).

Walks data/raw/options_screen/{ticker}/*_chain.json and writes
chains.csv, summary.csv, and ticker_summary.csv (with the sqrt-notional
liquidity screeners and the `liquid` gate) to data/processed/options_screen/.

Usage
-----
    python scripts/03_concat_screen.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.options import concat_results


def main() -> None:
    result = concat_results()
    ts = result["ticker_summary"]
    if ts.empty:
        sys.exit("No chain cache found under data/raw/options_screen/.")
    print(f"chains: {len(result['chains']):,} rows | "
          f"tickers: {len(ts)} | liquid: {int(ts['liquid'].sum())} "
          f"({sorted(ts.loc[ts['liquid'], 'ticker'])})")


if __name__ == "__main__":
    main()
