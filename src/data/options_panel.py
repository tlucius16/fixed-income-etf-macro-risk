"""Build the hedge-capacity options panel (steps 3–7 of the pipeline).

Public entry point
------------------
    build_options_panel(core_panel, *, chains_df=None, write_csv=True)

Step 1 (chain fetching / repull) is intentionally excluded here — it requires
ThetaData credentials and is handled by scripts/02_fetch_chains.py.
"""
from __future__ import annotations

import logging
import sys

import pandas as pd

from src import config as cfg
from src.data.options import screen_chain
from src.data.options_universe import ETF_METADATA
from src.features.hedge_capacity import compute_chain_capacity
from src.features.options_features import estimate_rolling_rate_duration
from src.features.rate_space import add_rate_space_greeks

logger = logging.getLogger(__name__)

_DURATION_R2_MIN       = 0.20
_DURATION_ABS_MIN      = 1.0
_MIN_QUALITY_CONTRACTS = 5


def build_options_panel(
    core_panel: pd.DataFrame,
    *,
    chains_df: pd.DataFrame | None = None,
    write_csv: bool = True,
) -> pd.DataFrame:
    """Run steps 2–7 and return (and optionally write) options_panel.

    Parameters
    ----------
    core_panel:
        Weekly core panel with columns ``ticker`` / ``date`` (or ``Symbol`` /
        ``Date``) plus ``Return``, ``d_DGS10``, ``fwd_maxdd_12w``.  The
        function handles either column-name convention.
    chains_df:
        Raw chain rows to use.  If *None* (default), the function loads from
        ``cfg.CHAINS_CSV``; raises ``SystemExit`` if that file is missing.
    write_csv:
        Write ``options_panel.csv`` to ``cfg.OPTIONS_PANEL_CSV`` (default
        *True*).  Pass *False* to get the DataFrame without touching disk.
    """
    # ── Step 2: load chains ──────────────────────────────────────────────────
    if chains_df is None:
        if not cfg.CHAINS_CSV.exists():
            logger.error(
                "chains.csv not found at %s. Run scripts/02_fetch_chains.py "
                "followed by scripts/03_concat_screen.py first.",
                cfg.CHAINS_CSV,
            )
            sys.exit(1)
        logger.info("Loading chains from %s …", cfg.CHAINS_CSV)
        chains_df = pd.read_csv(cfg.CHAINS_CSV, parse_dates=["snap_date"])
        logger.info("  %d rows, %d tickers", len(chains_df), chains_df["ticker"].nunique())

    if "right" not in chains_df.columns:
        chains_df = chains_df.copy()
        chains_df["right"] = "C"

    # ── Step 2: screen ───────────────────────────────────────────────────────
    passing = screen_chain(
        chains_df,
        max_rel_spread=cfg.MAX_REL_SPREAD,
        dte_min=cfg.DTE_MIN,
        dte_max=cfg.DTE_MAX,
        delta_lo=cfg.DELTA_LO,
        delta_hi=cfg.DELTA_HI,
        min_dollar_delta=cfg.MIN_DOLLAR_DELTA,
        min_dollar_gamma=cfg.MIN_DOLLAR_GAMMA,
        min_dollar_vega=cfg.MIN_DOLLAR_VEGA,
    )["passing"]
    logger.info("Screen: %d / %d contracts pass quality filter.", len(passing), len(chains_df))

    if passing.empty:
        logger.error("No contracts pass the quality screen.")
        sys.exit(1)

    # ── Step 3: empirical duration by ticker × snapshot ─────────────────────
    date_col   = "date"   if "date"   in core_panel.columns else "Date"
    ticker_col = "ticker" if "ticker" in core_panel.columns else "Symbol"

    # The repository core panel contains a broader ETF research universe.
    # This pipeline is explicitly scoped to the 36-ticker options universe.
    core = core_panel.rename(columns={date_col: "date", ticker_col: "ticker"}).copy()
    core["date"] = pd.to_datetime(core["date"])
    core = core[core["ticker"].isin(ETF_METADATA)].copy()

    logger.info("Estimating rolling rate duration (52w window) …")
    dur_df = estimate_rolling_rate_duration(core)
    dur_df["duration_ok"] = (
        (dur_df.get("duration_r2", pd.Series(0.0, index=dur_df.index)) >= _DURATION_R2_MIN)
        & (dur_df["realized_rate_duration"].abs() >= _DURATION_ABS_MIN)
    )

    dur_ticker_col = "ticker" if "ticker" in dur_df.columns else ticker_col

    def _lookup(ticker: str, snap: pd.Timestamp) -> float:
        sub = dur_df[dur_df[dur_ticker_col] == ticker].sort_values("date")
        if sub.empty:
            return float("nan")
        idx = sub["date"].searchsorted(snap, side="right") - 1
        if idx < 0:
            return float("nan")
        row = sub.iloc[idx]
        return float(row["realized_rate_duration"]) if row.get("duration_ok", True) else float("nan")

    snap_pairs = passing[["ticker", "snap_date"]].drop_duplicates().copy()
    snap_pairs["D_i"] = snap_pairs.apply(
        lambda r: _lookup(r["ticker"], pd.Timestamp(r["snap_date"])), axis=1
    )
    passing = passing.merge(
        snap_pairs,
        on=["ticker", "snap_date"],
        how="left",
        validate="many_to_one",
    )

    # Retained for callers of the lower-level APIs.  The D_i column on each
    # contract is authoritative and prevents a late snapshot from overwriting
    # every historical estimate for that ticker.
    duration_map: dict[str, float] = (
        snap_pairs.sort_values("snap_date")
        .groupby("ticker", sort=False)["D_i"]
        .last()
        .to_dict()
    )

    nan_pairs = snap_pairs[snap_pairs["D_i"].isna()]
    if not nan_pairs.empty:
        logger.warning(
            "%d / %d ticker-snapshot pairs have NaN empirical duration; "
            "absolute rate columns will be NaN. Tickers: %s",
            len(nan_pairs), len(snap_pairs), sorted(nan_pairs["ticker"].unique()),
        )

    # ── Steps 4 + 5: rate-space Greeks → chain capacity ─────────────────────
    logger.info("Translating dollar-Greeks to rate-space …")
    contracts = add_rate_space_greeks(passing, duration_map)

    logger.info("Aggregating to chain-level hedge capacity …")
    cap_df = compute_chain_capacity(
        contracts, metadata=ETF_METADATA,
        duration_map=duration_map,
        min_quality_contracts=_MIN_QUALITY_CONTRACTS,
    )
    logger.info("  %d (ticker, snap_date, side) capacity rows.", len(cap_df))

    if cap_df.empty:
        logger.error("compute_chain_capacity returned an empty frame.")
        sys.exit(1)

    # ── Step 6: merge capacity onto core panel (merge_asof backward) ─────────
    logger.info("Merging capacity onto core panel …")

    cap_total = cap_df[cap_df["side"] == "total"].rename(columns={"snap_date": "date"}).copy()
    cap_total["date"] = pd.to_datetime(cap_total["date"])
    keep_cap = [c for c in [
        "date", "ticker",
        "hedge_capacity_ratio", "chain_rate_dv01", "fund_dv01",
        "convexity_capacity_ratio", "median_rate_carry",
        "quality_contracts", "weight_basis",
    ] if c in cap_total.columns]
    cap_total = cap_total[keep_cap]

    parts: list[pd.DataFrame] = []
    for t in core["ticker"].unique():
        core_t = core[core["ticker"] == t].sort_values("date")
        cap_t  = cap_total[cap_total["ticker"] == t].sort_values("date")
        if cap_t.empty:
            parts.append(core_t)
        else:
            parts.append(pd.merge_asof(
                core_t, cap_t.drop(columns=["ticker"], errors="ignore"),
                on="date", direction="backward",
            ))
    panel = pd.concat(parts, ignore_index=True).sort_values(["ticker", "date"]).reset_index(drop=True)
    logger.info("  Panel shape after merge: %s", panel.shape)

    # ── Step 7: join IV/VRP columns (optional appendix columns) ─────────────
    if cfg.IV_PANEL_CSV.exists():
        logger.info("Joining IV panel …")
        iv_df   = pd.read_csv(cfg.IV_PANEL_CSV, parse_dates=["date"])
        # Core outcomes (volatility, forward returns/drawdowns) are already in
        # panel. Rejoining them would replace their canonical names with _x/_y
        # suffixes and break downstream regressions.
        iv_cols = [
            c for c in iv_df.columns
            if c not in ("date", "ticker") and c not in panel.columns
        ]
        panel   = panel.merge(iv_df[["date", "ticker"] + iv_cols], on=["date", "ticker"], how="left")
        logger.info("  Added %d IV columns.", len(iv_cols))
    else:
        logger.info("IV panel not found at %s — skipping IV join.", cfg.IV_PANEL_CSV)

    # ── Write ────────────────────────────────────────────────────────────────
    if write_csv:
        cfg.ensure_options_dirs()
        panel.to_csv(cfg.OPTIONS_PANEL_CSV, index=False)
        logger.info(
            "Wrote options_panel.csv → %s  (%d rows × %d cols)",
            cfg.OPTIONS_PANEL_CSV, len(panel), panel.shape[1],
        )
        if "hedge_capacity_ratio" in panel.columns:
            n_obs     = panel["hedge_capacity_ratio"].notna().sum()
            n_tickers = panel.loc[panel["hedge_capacity_ratio"].notna(), "ticker"].nunique()
            logger.info(
                "hedge_capacity_ratio: %d / %d weekly rows have values (%d tickers).",
                n_obs, len(panel), n_tickers,
            )

    return panel
