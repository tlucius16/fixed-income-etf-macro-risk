"""Chain-level hedge-capacity rollup.

Core metric — hedge_capacity_ratio
------------------------------------
The fraction of a fund's total rate (duration) exposure that the listed option
open interest on a given side can offset:

  chain_rate_dv01_side = Σ_c  rate_dv01_c * w_c
  hedge_capacity_ratio = chain_rate_dv01_side / fund_dv01

where w_c = open_interest_c if the column is present, else 1 (uniform weight).

Algebraic simplification
-------------------------
Because rate_dv01_c = D_i * S * |Δ_c| * 1e-4 * 100 and
fund_dv01 = D_i * AUM * 1e-4, D_i cancels in the ratio:

  hedge_capacity_ratio_side = (100 * S * Σ_c[|Δ_c| * w_c]) / AUM

This is delta-adjusted option OI notional as a share of fund AUM.
It is ROBUST: it does not depend on the noisy empirical D_i estimate.

    D_i does NOT cancel in the absolute exposures (rate_dv01_c, rate_conv_c) or in
    the convexity comparison, which is where duration structure stays informative.
    If D_i is unavailable, the ratio is still emitted from the reduced identity
    while those duration-dependent fields remain NaN.

Unweighted fallback
-------------------
If ``open_interest`` is absent from contracts_df, w_c = 1 for every quality
contract.  The ratio then degrades to a contract-count proxy (not depth-weighted).
This is flagged explicitly via ``weight_basis = 'unweighted'`` on every output row.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.features.rate_space import _BP_DECIMAL, _EPS, _MULTIPLIER
from src.features.rate_space import fund_dv01 as _fund_dv01

logger = logging.getLogger(__name__)


def compute_chain_capacity(
    contracts_df:  pd.DataFrame,
    metadata:      dict[str, dict],
    duration_map:  dict[str, float],
    *,
    min_quality_contracts: int   = 5,
) -> pd.DataFrame:
    """Aggregate quality contracts to a ticker × snap_date × side capacity table.

    Parameters
    ----------
    contracts_df
        Per-contract frame after ``rate_space.add_rate_space_greeks``.
        Must contain: ``ticker``, ``snap_date``, ``right`` (``"C"`` or ``"P"``),
        ``quality`` (bool), ``rate_dv01``, ``rate_conv``, ``theta_daily``,
        ``delta``, ``underlying``.  Optional: ``open_interest`` (float).
    metadata
        ``{ticker: {"aum": float, "eff_convexity": float | None, ...}}`` from
        ``src.data.options_universe.ETF_METADATA``.
    duration_map
        ``{ticker: D_i}`` compatibility mapping. If contracts contain ``D_i``,
        that snapshot-specific value takes precedence.
    min_quality_contracts
        Tickers with fewer quality contracts on a given snap_date are skipped.

    Returns
    -------
    pd.DataFrame with one row per (ticker, snap_date, side) where side ∈
    {``"put"``, ``"call"``, ``"total"``} and columns:

      ticker, snap_date, side,
      chain_rate_dv01, chain_rate_conv,
      fund_dv01, fund_conv_dollar,
      hedge_capacity_ratio, convexity_capacity_ratio,
      median_rate_carry,
      quality_contracts, weight_basis
    """
    required = {
        "ticker", "snap_date", "right", "quality",
        "rate_dv01", "rate_conv", "theta_daily", "delta", "underlying",
    }
    missing = required - set(contracts_df.columns)
    if missing:
        raise KeyError(f"contracts_df missing columns: {sorted(missing)}")

    has_oi       = "open_interest" in contracts_df.columns
    weight_basis = "open_interest" if has_oi else "unweighted"

    quality = contracts_df[contracts_df["quality"]].copy()
    if quality.empty:
        logger.warning("compute_chain_capacity: no quality contracts in input.")
        return pd.DataFrame()

    quality["side"] = quality["right"].str.upper().map({"C": "call", "P": "put"}).fillna("call")
    quality["_w"]   = quality["open_interest"].astype(float) if has_oi else 1.0
    quality["_rate_carry"] = quality.get("rate_carry", np.nan)

    rows: list[dict] = []

    for (ticker, snap_date), grp in quality.groupby(["ticker", "snap_date"], sort=False):
        if "D_i" in grp.columns:
            duration_values = pd.to_numeric(grp["D_i"], errors="coerce").dropna()
            D_i = (
                float(duration_values.iloc[0])
                if not duration_values.empty
                else float("nan")
            )
        else:
            D_i = float(duration_map.get(ticker, float("nan")))
        meta = metadata.get(ticker, {})
        aum  = meta.get("aum")
        eff_conv = meta.get("eff_convexity")

        if aum is None:
            logger.warning(
                "compute_chain_capacity: %s %s skipped — AUM missing.",
                ticker, snap_date,
            )
            continue

        duration_available = np.isfinite(D_i) and D_i > 0
        if duration_available:
            f_dv01 = _fund_dv01(D_i, aum)
        else:
            logger.warning(
                "compute_chain_capacity: %s %s has no valid positive D_i; "
                "emitting duration-independent hedge capacity only.",
                ticker, snap_date,
            )
            f_dv01 = float("nan")

        if not duration_available:
            fund_conv_dollar = float("nan")
        elif eff_conv is not None:
            fund_conv_dollar = 0.5 * eff_conv * aum * (_BP_DECIMAL ** 2)
        else:
            logger.warning(
                "compute_chain_capacity: %s eff_convexity not available; "
                "using D_i² proxy for fund_conv_dollar.",
                ticker,
            )
            fund_conv_dollar = 0.5 * (D_i ** 2) * aum * (_BP_DECIMAL ** 2)

        sides_to_aggregate = list(grp["side"].unique()) + ["total"]

        for side in sides_to_aggregate:
            if side == "total":
                sub = grp
            else:
                sub = grp[grp["side"] == side]

            n_qual = len(sub)
            if n_qual < min_quality_contracts:
                if side != "total":
                    logger.warning(
                        "compute_chain_capacity: %s %s side=%s has only %d quality "
                        "contracts (< %d) — skipping this side row.",
                        ticker, snap_date, side, n_qual, min_quality_contracts,
                    )
                continue

            w          = sub["_w"].to_numpy(dtype=float)
            rate_dv01  = sub["rate_dv01"].to_numpy(dtype=float)
            rate_conv  = sub["rate_conv"].to_numpy(dtype=float)
            rate_carry = sub["_rate_carry"].to_numpy(dtype=float)
            underlying = sub["underlying"].to_numpy(dtype=float)
            delta      = sub["delta"].to_numpy(dtype=float)

            valid_ratio = (
                np.isfinite(underlying) & np.isfinite(delta) & np.isfinite(w)
            )
            if not valid_ratio.any():
                continue

            valid_dv01 = np.isfinite(rate_dv01) & np.isfinite(w)
            valid_conv = np.isfinite(rate_conv) & np.isfinite(w)
            valid_carry = np.isfinite(rate_carry)

            chain_dv01 = (
                float(np.sum(rate_dv01[valid_dv01] * w[valid_dv01]))
                if valid_dv01.any() else float("nan")
            )
            chain_conv = (
                float(np.sum(rate_conv[valid_conv] * w[valid_conv]))
                if valid_conv.any() else float("nan")
            )
            median_carry = (
                float(np.median(rate_carry[valid_carry]))
                if valid_carry.any() else float("nan")
            )

            # Reduced identity: D_i cancels, so this remains identified even
            # when the empirical duration quality gate fails.
            hcr = float(
                _MULTIPLIER
                * np.sum(
                    underlying[valid_ratio]
                    * np.abs(delta[valid_ratio])
                    * w[valid_ratio]
                )
                / float(aum)
            )
            ccr = (
                chain_conv / fund_conv_dollar
                if np.isfinite(chain_conv)
                and np.isfinite(fund_conv_dollar)
                and abs(fund_conv_dollar) > _EPS
                else float("nan")
            )

            rows.append({
                "ticker":                    ticker,
                "snap_date":                 snap_date,
                "side":                      side,
                "chain_rate_dv01":           chain_dv01,
                "chain_rate_conv":           chain_conv,
                "fund_dv01":                 f_dv01,
                "fund_conv_dollar":          fund_conv_dollar,
                "hedge_capacity_ratio":      hcr,
                "convexity_capacity_ratio":  ccr,
                "median_rate_carry":         median_carry,
                "quality_contracts":         n_qual,
                "weight_basis":              weight_basis,
            })

    if not rows:
        logger.warning("compute_chain_capacity: no rows produced.")
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out["snap_date"] = pd.to_datetime(out["snap_date"])
    return out.reset_index(drop=True)
