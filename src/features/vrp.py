"""IV / VRP diagnostics for the options paper appendix.

These functions establish that option-implied pricing is uninformative as a
predictor of forward drawdown severity, motivating the hedge-capacity focus.
They are NOT part of the main panel build; run them to populate the appendix.

compute_vrp — add variance-gap columns to an IV panel.
"""
from __future__ import annotations

import logging

import pandas as pd

from src import config

logger = logging.getLogger(__name__)

_ANNUALISE_FACTOR = config.ANNUALISE_FACTOR

_REGIME_BINS = [
    pd.Timestamp("2000-01-01"),
    pd.Timestamp("2022-01-01"),
    pd.Timestamp("2023-07-01"),
    pd.Timestamp("2024-10-01"),
    pd.Timestamp("2030-01-01"),
]
_REGIME_LABELS = ["pre_tightening", "tightening", "plateau", "easing"]


def _add_rate_regime(df: pd.DataFrame, *, date_col: str, out_col: str = "rate_regime") -> pd.DataFrame:
    out = df.copy()
    out[out_col] = pd.cut(
        pd.to_datetime(out[date_col]),
        bins=_REGIME_BINS,
        labels=_REGIME_LABELS,
        right=False,
    )
    return out


def compute_vrp(df: pd.DataFrame) -> pd.DataFrame:
    """Add variance-gap columns to the IV panel.

    Requires columns: date, iv_30d, vol_12w_annualized.
    Adds:
      iv_realized_var_gap - iv_30d^2 minus trailing 12-week realized variance
      vrp                 - backward-compatible alias for iv_realized_var_gap
      vrp_positive        - max(vrp, 0)
      vrp_ex_post_12w     - iv_30d^2 minus forward 12-week realized variance, if
                            fwd_vol_12w is available
      rate_regime         - pre_tightening / tightening / plateau / easing

    The ``vrp`` alias is an ex-ante predictor (only uses information known at
    date t).  The ex-post premium is stored separately to avoid look-ahead.
    """
    out = df.copy()
    out["iv_realized_var_gap"] = out["iv_30d"] ** 2 - out["vol_12w_annualized"] ** 2
    out["vrp"]          = out["iv_realized_var_gap"]
    out["vrp_positive"] = out["vrp"].clip(lower=0)

    if "fwd_vol_12w" in out.columns:
        out["fwd_vol_12w_annualized"] = out["fwd_vol_12w"] * _ANNUALISE_FACTOR
        out["vrp_ex_post_12w"] = out["iv_30d"] ** 2 - out["fwd_vol_12w_annualized"] ** 2

    return _add_rate_regime(out, date_col="date")
