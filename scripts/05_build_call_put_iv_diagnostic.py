"""Build the quarterly call/put IV diagnostic from cached chain data."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config as cfg
from src.features.call_put_iv import build_call_put_iv_diagnostic


def main() -> None:
    chains = pd.read_csv(cfg.CHAINS_CSV, parse_dates=["snap_date", "expiry"])
    diagnostic = build_call_put_iv_diagnostic(
        chains,
        max_rel_spread=cfg.MAX_REL_SPREAD,
    )
    cfg.ensure_options_dirs()
    diagnostic.to_csv(cfg.CALL_PUT_IV_CSV, index=False)

    paired = diagnostic["iv_side_count"].eq(2)
    print(
        f"Wrote {len(diagnostic):,} ticker-snapshot rows "
        f"({paired.sum():,} paired call/put) → {cfg.CALL_PUT_IV_CSV}"
    )
    if paired.any():
        gaps = diagnostic.loc[paired, "abs_call_put_iv_gap"]
        print(
            "Absolute call-put IV gap: "
            f"median={gaps.median():.4f}, p90={gaps.quantile(0.90):.4f}"
        )
    print(diagnostic["iv_source"].value_counts().to_string())


if __name__ == "__main__":
    main()
