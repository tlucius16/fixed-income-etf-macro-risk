"""Contract-level dollar-Greek → rate-space translation.

Bridge formula: dS/S = -D_i * dy  →  dV/dy = (dV/dS)(dS/dy) = -D_i * S * delta_c

Per-contract rate-space exposures (contract multiplier = 100):

  rate_dv01_c  = D_i * S * |delta_c| * 0.0001 * 100
                 Dollar P&L per 1bp parallel yield move, per single contract.
                 Always non-negative (absorbs sign via abs).

  rate_conv_c  = 0.5 * D_i² * S * (delta_c + S * gamma_c) * (0.0001)² * 100
                 Second-order dollars per (1bp)². KEPT SIGNED: the D_i² factor
                 bridges to bond convexity (delta_c is signed for puts).

  rate_carry_c = |theta_daily_c| / rate_dv01_c   (NaN if rate_dv01_c == 0)
                 Daily theta per dollar of rate-DV01 hedged.
                 Multiply by 252 for annualised carry cost.

D_i = realized_rate_duration (positive for long-duration ETFs; NaN if the
duration quality gate fails).  Rows with NaN D_i get NaN rate columns.

Fund-level rate target (used in hedge_capacity.py):
  fund_dv01_i = D_i * AUM_i * 0.0001
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_EPS        = np.finfo(float).eps
_BP_DECIMAL = 0.0001       # 1 basis point in decimal
_MULTIPLIER = 100.0        # standard option contract multiplier


def add_rate_space_greeks(
    contracts_df:  pd.DataFrame,
    duration_map:  dict[str, float],
) -> pd.DataFrame:
    """Add rate_dv01, rate_conv, rate_carry columns to a per-contract DataFrame.

    Parameters
    ----------
    contracts_df
        Per-contract rows with at minimum: ``ticker``, ``delta``, ``gamma``,
        ``theta_daily``, ``underlying`` (= S).  Optional: ``open_interest``
        (used by hedge_capacity aggregation; not consumed here).
    duration_map
        ``{ticker: D_i}`` from ``estimate_rolling_rate_duration``.
        Missing tickers or NaN values produce NaN rate columns for those rows.
        Pass ``float("nan")`` for tickers that fail the quality gate.
        When ``contracts_df`` contains a ``D_i`` column, its snapshot-specific
        values take precedence over this ticker-level compatibility mapping.

    Returns
    -------
    pd.DataFrame
        Input frame with three new columns appended:
        ``rate_dv01``, ``rate_conv``, ``rate_carry``.
    """
    required = {"ticker", "delta", "gamma", "theta_daily", "underlying"}
    missing  = required - set(contracts_df.columns)
    if missing:
        raise KeyError(f"contracts_df is missing required columns: {sorted(missing)}")

    out = contracts_df.copy()

    S     = out["underlying"].to_numpy(dtype=float)
    delta = out["delta"].to_numpy(dtype=float)
    gamma = out["gamma"].to_numpy(dtype=float)
    theta = out["theta_daily"].to_numpy(dtype=float)

    if "D_i" in out.columns:
        D_i = pd.to_numeric(out["D_i"], errors="coerce").to_numpy(dtype=float)
    else:
        D_i = np.array(
            [float(duration_map.get(t, float("nan"))) for t in out["ticker"]],
            dtype=float,
        )

    nan_dur = np.isnan(D_i)
    if nan_dur.any():
        tickers_nan = out.loc[nan_dur, "ticker"].unique()
        logger.warning(
            "rate_space: %d contract(s) across %d ticker(s) have NaN D_i "
            "→ rate columns will be NaN.  Tickers: %s",
            int(nan_dur.sum()), len(tickers_nan), sorted(tickers_nan),
        )

    rate_dv01 = D_i * S * np.abs(delta) * _BP_DECIMAL * _MULTIPLIER
    rate_conv  = (
        0.5 * (D_i ** 2) * S * (delta + S * gamma) * (_BP_DECIMAL ** 2) * _MULTIPLIER
    )
    zero_dv01 = np.abs(rate_dv01) < _EPS
    if zero_dv01.any():
        logger.warning(
            "rate_space: %d contract(s) have rate_dv01 ≈ 0 → rate_carry set to NaN.",
            int(zero_dv01.sum()),
        )

    denom_safe    = np.where(zero_dv01 | nan_dur, float("nan"), rate_dv01)
    rate_carry    = np.abs(theta) / denom_safe

    out["rate_dv01"]  = np.where(nan_dur, float("nan"), rate_dv01)
    out["rate_conv"]  = np.where(nan_dur, float("nan"), rate_conv)
    out["rate_carry"] = rate_carry

    return out.reset_index(drop=True)


def fund_dv01(duration: float, aum: float) -> float:
    """Fund-level rate DV01 in dollars.

    fund_dv01 = D_i * AUM_i * 0.0001

    Equals the dollar P&L of the entire fund per 1bp parallel yield rise.
    ``duration`` should be ``realized_rate_duration`` (positive for long-duration).
    """
    return float(duration) * float(aum) * _BP_DECIMAL
