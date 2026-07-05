"""Build the IV time-series panel for the 36-ticker options universe.

Fetches weekly (Friday) ATM 30-day IV from ThetaData for each ticker from
2020-01-03 through today, joins with the core panel, and writes:

    data/processed/options_screen/iv_panel_full.csv

Columns: date, ticker, vol_12w, vol_12w_annualized, iv_30d,
         iv_realized_spread, fwd_ret_4w, fwd_maxdd_12w, fwd_vol_12w

Usage
-----
    python scripts/03_build_iv_panel.py
    python scripts/03_build_iv_panel.py --start 2022-01-07 --end 2025-12-31
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

if not os.environ.get("FRED_API_KEY"):
    sys.exit("FRED_API_KEY not set. Export it in your environment first.")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config
from src.data.options import (
    build_iv_spread_panel,
    fetch_atm_call_put_iv_30d,
    fetch_atm_iv_30d,
)
from src.data.options_universe import UNIVERSE

_DEFAULT_START = "2020-01-03"
_TICKER_SUMMARY = config.PROCESSED_DIR / "options_screen" / "ticker_summary.csv"
_OUT_PATH       = config.PROCESSED_DIR / "options_screen" / "iv_panel_full.csv"


def main() -> None:
    p = argparse.ArgumentParser(description="Build IV panel for liquid tickers.")
    p.add_argument("--start", default=_DEFAULT_START,
                   help="Start date for IV fetch (default: 2020-01-03).")
    p.add_argument("--end", default=date.today().isoformat(),
                   help="End date for IV fetch (default: today).")
    p.add_argument("--ticker-summary", default=str(_TICKER_SUMMARY),
                   help="Path to ticker_summary.csv (written by run_screen/concat_results; "
                        "only needed with --liquid-only).")
    p.add_argument(
        "--call-only",
        action="store_true",
        help="Use the legacy ATM-call series instead of combined call/put IV.",
    )
    p.add_argument(
        "--liquid-only",
        action="store_true",
        help="Restrict the fetch to tickers passing the liquidity screen.",
    )
    args = p.parse_args()

    if args.liquid_only:
        ts_path = Path(args.ticker_summary)
        if not ts_path.exists():
            print(f"ticker_summary.csv not found at {ts_path}.")
            print("Run the screen first (notebook 05 Step 1, or "
                  "scripts/04_build_options_panel.py --repull).")
            sys.exit(1)
        ts      = pd.read_csv(ts_path)
        tickers = ts[ts["liquid"] == True]["ticker"].tolist()
    else:
        tickers = list(UNIVERSE)
    start   = args.start
    print(f"Fetching IV for {len(tickers)} tickers: {start} → {args.end}")
    iv_frames: list[pd.DataFrame] = []
    fetch_iv = fetch_atm_iv_30d if args.call_only else fetch_atm_call_put_iv_30d

    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {ticker} ...")
        df    = fetch_iv(ticker, start, args.end)
        n_ok  = df["iv_30d"].notna().sum()
        n_tot = len(df)
        print(f"    {n_ok}/{n_tot} Fridays with valid IV")
        iv_frames.append(df)

    if not iv_frames:
        print("No IV data fetched.")
        sys.exit(1)

    iv_all = pd.concat(iv_frames, ignore_index=True)

    print("Joining IV with core panel (liquid tickers only) ...")
    core_df = pd.read_csv(config.core_panel_csv("offline"), parse_dates=["Date"])
    core_df = core_df[core_df["Symbol"].isin(tickers)]
    panel = build_iv_spread_panel(iv_all, core_df=core_df)

    _OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(_OUT_PATH, index=False)

    rows_with_iv = panel["iv_30d"].notna().sum()
    print(f"Wrote {len(panel):,} rows ({rows_with_iv:,} with iv_30d) → {_OUT_PATH}")


if __name__ == "__main__":
    main()
