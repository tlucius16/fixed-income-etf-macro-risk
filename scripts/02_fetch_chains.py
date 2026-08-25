"""Fetch full options chains from ThetaData (calls and puts with open interest).

This live stage uses ThetaData credentials and writes raw JSON caches. Run
``scripts/03_concat_screen.py`` afterward to rebuild the canonical processed
chain and liquidity-screen CSVs from every cached ticker and date.

Usage
-----
    # Fetch all tickers on monthly business-start dates from 2016 onward:
    python scripts/02_fetch_chains.py

    # Fetch selected tickers only:
    python scripts/02_fetch_chains.py --tickers TLT IEF LQD

    # Fetch selected snapshot dates only:
    python scripts/02_fetch_chains.py --snap-dates 2025-01-02 2025-04-01
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.options import run_screen
from src.data.options_universe import UNIVERSE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _generate_snap_dates(start: str = "2016-01-01", freq: str = "BMS") -> list[str]:
    """Generate snapshot dates through today at the requested pandas frequency."""
    end = pd.Timestamp.today().strftime("%Y-%m-%d")
    dates = pd.date_range(start=start, end=end, freq=freq)
    return [date.strftime("%Y-%m-%d") for date in dates]


_DEFAULT_SNAP_DATES = _generate_snap_dates()


def _fetch_chains(tickers: list[str], snap_dates: list[str]) -> pd.DataFrame:
    logger.info(
        "Fetching chains for %d tickers on %d snap dates (C+P, with OI) ...",
        len(tickers),
        len(snap_dates),
    )
    result = run_screen(
        tickers=tickers,
        snap_dates=snap_dates,
        rights=("C", "P"),
        max_workers=1,
    )
    chains_df = result["chains"]
    if chains_df.empty:
        sys.exit("run_screen returned no chains.")

    logger.info(
        "Cached %d fetched chain rows. Run scripts/03_concat_screen.py to "
        "rebuild the canonical processed CSVs from all caches.",
        len(chains_df),
    )
    return chains_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        metavar="TICKER",
        help="Tickers to fetch; defaults to all 36 universe tickers.",
    )
    parser.add_argument(
        "--snap-dates",
        nargs="+",
        default=None,
        dest="snap_dates",
        metavar="YYYY-MM-DD",
        help="Snapshot dates; defaults to monthly business starts from 2016 onward.",
    )
    args = parser.parse_args()

    tickers = args.tickers or list(UNIVERSE)
    snap_dates = args.snap_dates or _DEFAULT_SNAP_DATES
    _fetch_chains(tickers, snap_dates)


if __name__ == "__main__":
    main()
