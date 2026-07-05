"""Build the hedge-capacity options panel (options_panel.csv).

Pipeline
--------
1. Load the cached chain CSVs (or re-pull via ThetaData if --repull is set).
2–7. Screen, duration-map, rate-space Greeks, hedge capacity, merge, IV join.
8. Write options_panel.csv.

Steps 2–7 are handled by ``src.data.options_panel.build_options_panel``,
which can also be called directly from a notebook cell.

Usage
-----
    # Build from existing chain cache (no new ThetaData calls):
    python scripts/04_build_options_panel.py

    # Re-pull chains for puts+calls with OI (will call ThetaData):
    python scripts/04_build_options_panel.py --repull

    # Re-pull a specific ticker only:
    python scripts/04_build_options_panel.py --repull --tickers TLT IEF LQD

    # Use a specific set of snap dates:
    python scripts/04_build_options_panel.py --repull --snap-dates 2025-01-02 2025-04-01
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config as cfg
from src.data.options_panel import build_options_panel
from src.data.options_universe import UNIVERSE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_QUARTERLY_SNAP_DATES = [
    "2020-01-02", "2020-04-01", "2020-07-01", "2020-10-01",
    "2021-01-04", "2021-04-01", "2021-07-01", "2021-10-01",
    "2022-01-03", "2022-04-01", "2022-07-01", "2022-10-03",
    "2023-01-03", "2023-04-03", "2023-07-03", "2023-10-02",
    "2024-01-02", "2024-04-01", "2024-07-01", "2024-10-01",
    "2025-01-02", "2025-04-01",
]


def _repull_chains(tickers: list[str], snap_dates: list[str]) -> pd.DataFrame:
    from src.data.options import run_screen  # noqa: PLC0415

    logger.info(
        "Re-pulling chains for %d tickers on %d snap dates (C+P, with OI) …",
        len(tickers), len(snap_dates),
    )
    result    = run_screen(tickers=tickers, snap_dates=snap_dates, rights=("C", "P"))
    chains_df = result["chains"]
    if chains_df.empty:
        logger.error("run_screen returned no chains.")
        sys.exit(1)

    cfg.ensure_options_dirs()
    chains_df.to_csv(cfg.CHAINS_CSV, index=False)
    logger.info("Wrote %d chain rows to %s", len(chains_df), cfg.CHAINS_CSV)
    return chains_df


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repull", action="store_true",
                   help="Re-fetch chains from ThetaData for puts+calls with OI.")
    p.add_argument("--tickers", nargs="+", default=None, metavar="TICKER",
                   help="Tickers to (re-)pull; defaults to all 36 universe tickers.")
    p.add_argument("--snap-dates", nargs="+", default=None, dest="snap_dates",
                   metavar="YYYY-MM-DD",
                   help="Snap dates to (re-)pull; defaults to quarterly 2020-2025.")
    args = p.parse_args()

    logger.info("Loading core panel from %s …", cfg.CORE_PANEL_CSV)
    core_df = pd.read_csv(cfg.CORE_PANEL_CSV, parse_dates=["Date"])
    logger.info("  %d rows, %d tickers", len(core_df), core_df["Symbol"].nunique())

    chains_df = None
    if args.repull:
        tickers    = args.tickers    or list(UNIVERSE.keys())
        snap_dates = args.snap_dates or _QUARTERLY_SNAP_DATES
        chains_df  = _repull_chains(tickers, snap_dates)

    build_options_panel(core_df, chains_df=chains_df, write_csv=True)


if __name__ == "__main__":
    main()
