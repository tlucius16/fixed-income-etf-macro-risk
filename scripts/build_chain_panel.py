"""Build chains.csv + the liquidity screen from pull_liquid_options.py output.

Offline: reads only already-pulled partitions; never fetches, never touches the
pinned data/processed/options_screen/ tree the active study reads.

Usage
-----
    python scripts/build_chain_panel.py --pulls data/raw/hedge_design/theta-liquid-mac-pilot-20260914 \\
        --dataset-id chain-panel-pilot-20260914
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.build_chain_panel import build_and_write


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pulls", nargs="+", required=True, type=Path,
                        help="One or more pull_liquid_options.py output directories")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--screen-version", choices=["v1", "v2"], default="v1",
                        help="v1: legacy-ported score and liquidity flag (default, unchanged). "
                             "v2: revised screen -- separate quote eligibility/scope/OI sizing, "
                             "no dollar-greek floor, no call/put balance gate, no composite score "
                             "or liquidity flag (see summary.csv's date-specific diagnostics).")
    args = parser.parse_args()
    try:
        destination = build_and_write(args.pulls, ROOT / "data/processed/chain_panels",
                                      args.dataset_id, screen_version=args.screen_version)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {destination.relative_to(ROOT)}")
    ticker_summary_path = destination / "ticker_summary.csv"
    if ticker_summary_path.exists():
        print(ticker_summary_path.read_text())
    else:
        print("No ticker_summary.csv for this screen version -- see summary.csv "
              "for date-specific put/call diagnostics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
