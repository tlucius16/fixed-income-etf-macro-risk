"""Call/put implied-volatility diagnostics from cached option chains."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_call_put_iv_diagnostic(
    chains_df: pd.DataFrame,
    *,
    target_dte: int = 30,
    dte_min: int = 14,
    dte_max: int = 60,
    max_rel_spread: float = 0.35,
) -> pd.DataFrame:
    """Build one quality-controlled near-ATM call/put IV row per snapshot.

    The expiry closest to ``target_dte`` with at least one usable quote is
    selected. Within that expiry, the closest-to-spot strike having both a
    usable call and put is preferred; if no paired strike exists, the closest
    usable single-side strike is retained. ``iv_30d_cp`` is the median of the
    available side IVs (the arithmetic mean when both sides are present).

    This is a discrete near-30-day ATM diagnostic, not model-free variance or
    an interpolation to exactly 30 calendar days.
    """
    required = {
        "ticker", "snap_date", "expiry", "strike", "right", "dte",
        "underlying", "bid", "ask", "iv",
    }
    missing = required - set(chains_df.columns)
    if missing:
        raise KeyError(f"chains_df missing columns: {sorted(missing)}")

    work = chains_df.copy()
    work["snap_date"] = pd.to_datetime(work["snap_date"])
    work["expiry"] = pd.to_datetime(work["expiry"])
    work["right"] = work["right"].astype(str).str.upper()
    for col in ["strike", "dte", "underlying", "bid", "ask", "iv"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    mid = (work["bid"] + work["ask"]) / 2.0
    work["rel_spread"] = (work["ask"] - work["bid"]) / mid.replace(0.0, np.nan)
    work["_usable"] = (
        work["right"].isin(["C", "P"])
        & work["dte"].between(dte_min, dte_max)
        & (work["bid"] > 0)
        & (work["ask"] > 0)
        & (work["rel_spread"] >= 0)
        & (work["rel_spread"] <= max_rel_spread)
        & np.isfinite(work["iv"])
        & (work["iv"] > 0)
    )
    usable = work[work["_usable"]].copy()
    if usable.empty:
        return pd.DataFrame(
            columns=[
                "ticker", "snap_date", "expiry", "strike", "days_to_expiry",
                "underlying", "call_iv", "put_iv", "iv_30d_cp",
                "iv_side_count", "call_put_iv_gap", "abs_call_put_iv_gap",
                "call_rel_spread", "put_rel_spread", "iv_source",
            ]
        )

    rows: list[dict] = []
    for (ticker, snap_date), snap in usable.groupby(
        ["ticker", "snap_date"], sort=False
    ):
        expiry_rank = (
            snap[["expiry", "dte"]]
            .drop_duplicates()
            .assign(_distance=lambda x: (x["dte"] - target_dte).abs())
            .sort_values(["_distance", "dte", "expiry"])
        )
        expiry = expiry_rank.iloc[0]["expiry"]
        exp_rows = snap[snap["expiry"] == expiry].copy()
        underlying = float(exp_rows["underlying"].median())

        by_strike = (
            exp_rows.groupby("strike")["right"]
            .nunique()
            .rename("side_count")
            .reset_index()
        )
        paired = by_strike[by_strike["side_count"] == 2]
        strike_pool = paired if not paired.empty else by_strike
        strike = float(
            strike_pool.assign(
                _distance=(strike_pool["strike"] - underlying).abs()
            )
            .sort_values(["_distance", "strike"])
            .iloc[0]["strike"]
        )
        selected = exp_rows[exp_rows["strike"] == strike]

        def _side_value(right: str, column: str) -> float:
            values = selected.loc[selected["right"] == right, column].dropna()
            return float(values.median()) if not values.empty else float("nan")

        call_iv = _side_value("C", "iv")
        put_iv = _side_value("P", "iv")
        side_ivs = np.array([call_iv, put_iv], dtype=float)
        valid_sides = np.isfinite(side_ivs)
        side_count = int(valid_sides.sum())
        combined = float(np.median(side_ivs[valid_sides]))
        gap = put_iv - call_iv if side_count == 2 else float("nan")

        rows.append(
            {
                "ticker": ticker,
                "snap_date": snap_date,
                "expiry": expiry,
                "strike": strike,
                "days_to_expiry": int(selected["dte"].iloc[0]),
                "underlying": underlying,
                "call_iv": call_iv,
                "put_iv": put_iv,
                "iv_30d_cp": combined,
                "iv_side_count": side_count,
                "call_put_iv_gap": gap,
                "abs_call_put_iv_gap": abs(gap) if np.isfinite(gap) else float("nan"),
                "call_rel_spread": _side_value("C", "rel_spread"),
                "put_rel_spread": _side_value("P", "rel_spread"),
                "iv_source": "call_put_median" if side_count == 2 else (
                    "call_only" if np.isfinite(call_iv) else "put_only"
                ),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["ticker", "snap_date"])
        .reset_index(drop=True)
    )
