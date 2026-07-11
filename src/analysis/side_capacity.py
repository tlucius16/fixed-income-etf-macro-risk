"""Side-level capacity rebuild shared by the robustness ladder and paper artifacts.

Mirrors ``build_options_panel`` steps 2–5 but keeps the call/put side rows the
panel build discards (it stores side == "total" only), and provides the
merge-asof helpers used to attach side capacity and capacity age to the weekly
regression frame.
"""
from __future__ import annotations

import pandas as pd

from src import config as cfg
from src.data.options import screen_chain
from src.data.options_universe import ETF_METADATA
from src.features.hedge_capacity import compute_chain_capacity
from src.features.options_features import estimate_rolling_rate_duration
from src.features.rate_space import add_rate_space_greeks

_DURATION_R2_MIN  = 0.20
_DURATION_ABS_MIN = 1.0


def build_side_capacity(
    chains: pd.DataFrame,
    core_panel: pd.DataFrame,
    *,
    min_quality_contracts: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (cap_df, passing, duration_map).

    ``cap_df`` has one row per (ticker, snap_date, side) with side in
    {call, put, total}; ``core_panel`` must use ticker/date column names.
    """
    passing = screen_chain(
        chains,
        max_rel_spread=cfg.MAX_REL_SPREAD, dte_min=cfg.DTE_MIN, dte_max=cfg.DTE_MAX,
        delta_lo=cfg.DELTA_LO, delta_hi=cfg.DELTA_HI,
        min_dollar_delta=cfg.MIN_DOLLAR_DELTA, min_dollar_gamma=cfg.MIN_DOLLAR_GAMMA,
        min_dollar_vega=cfg.MIN_DOLLAR_VEGA,
    )["passing"]

    core = core_panel[core_panel["ticker"].isin(ETF_METADATA)].copy()
    dur = estimate_rolling_rate_duration(core)
    dur["duration_ok"] = (
        (dur.get("duration_r2", pd.Series(0.0, index=dur.index)) >= _DURATION_R2_MIN)
        & (dur["realized_rate_duration"].abs() >= _DURATION_ABS_MIN)
    )

    def _lookup(tk: str, snap: pd.Timestamp) -> float:
        sub = dur[dur["ticker"] == tk].sort_values("date")
        if sub.empty:
            return float("nan")
        i = sub["date"].searchsorted(snap, side="right") - 1
        if i < 0:
            return float("nan")
        row = sub.iloc[i]
        return float(row["realized_rate_duration"]) if row.get("duration_ok", True) else float("nan")

    snap_pairs = passing[["ticker", "snap_date"]].drop_duplicates().copy()
    snap_pairs["D_i"] = snap_pairs.apply(
        lambda r: _lookup(r["ticker"], pd.Timestamp(r["snap_date"])), axis=1)
    passing = passing.merge(snap_pairs, on=["ticker", "snap_date"], how="left")
    duration_map = (snap_pairs.sort_values("snap_date")
                    .groupby("ticker", sort=False)["D_i"].last().to_dict())

    cap_df = compute_chain_capacity(
        add_rate_space_greeks(passing, duration_map),
        metadata=ETF_METADATA, duration_map=duration_map,
        min_quality_contracts=min_quality_contracts,
    )
    return cap_df, passing, duration_map


def merge_side(base: pd.DataFrame, cap_df: pd.DataFrame, side: str,
               colname: str) -> pd.DataFrame:
    """merge_asof(backward) one side's hedge_capacity_ratio onto weekly rows.

    Adds ``colname`` and a ``cap_date`` column (the matched snapshot date).
    """
    s = cap_df[cap_df["side"] == side][["ticker", "snap_date", "hedge_capacity_ratio"]].rename(
        columns={"snap_date": "cap_date", "hedge_capacity_ratio": colname}).copy()
    s["cap_date"] = pd.to_datetime(s["cap_date"])
    parts = []
    for t in base["ticker"].unique():
        bt = base[base["ticker"] == t].sort_values("date")
        st = s[s["ticker"] == t].sort_values("cap_date")
        parts.append(bt if st.empty else pd.merge_asof(
            bt, st.drop(columns="ticker"), left_on="date", right_on="cap_date",
            direction="backward"))
    return pd.concat(parts, ignore_index=True)
