"""Spec 0 robustness ladder (CGM two-way clustered) -> robustness_spec0.csv.

Canonical producer of the 18-row ladder previously computed in notebook 05
Section 10 (the notebook now displays this file). Also writes the side-level
capacity table consumed by scripts/08_paper_artifacts.py.

Specs: baseline date FE; ticker / ticker+date / bucket FE; Mundlak
within-between; drop-influential; winsorized; log; capacity-age controls;
snapshot-week subsample; call/put side capacity horse race.

Usage
-----
    python scripts/07_robustness_ladder.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from src import config as cfg
from src.analysis.regression_utils import cgm_summary
from src.analysis.side_capacity import build_side_capacity, merge_side
from src.data.options_universe import ticker_bucket

SIDE_CAPACITY_CSV = cfg.OPTIONS_SCREEN_DIR / "side_capacity.csv"

_rows: list[dict] = []


def _run(name: str, formula: str, df: pd.DataFrame, focal, note: str = "") -> None:
    d = df.copy()
    d["date_grp"] = pd.to_datetime(d["date"]).dt.strftime("%Y-%m-%d")
    tbl = cgm_summary(formula, d.assign(date=d["date_grp"]),
                      [focal] if isinstance(focal, str) else focal)
    for v in tbl.index:
        _rows.append({
            "spec": name, "var": v, "coef": tbl.loc[v, "coef"],
            "se_cgm": tbl.loc[v, "se_cgm"], "p_cgm": tbl.loc[v, "p_cgm"],
            "tickers": d["ticker"].nunique(), "note": note,
        })


def main() -> None:
    panel = pd.read_csv(cfg.OPTIONS_PANEL_CSV, parse_dates=["date"])
    reg = panel.dropna(subset=["hedge_capacity_ratio", "fwd_maxdd_12w"]).copy()
    reg["bucket"] = reg["ticker"].map(ticker_bucket)
    print(f"Robustness sample: {len(reg):,} obs, {reg['ticker'].nunique()} tickers")

    _run("S0 baseline (date FE)", "fwd_maxdd_12w ~ hedge_capacity_ratio + C(date_grp)",
         reg, "hedge_capacity_ratio")
    _run("R1a ticker FE", "fwd_maxdd_12w ~ hedge_capacity_ratio + C(ticker)",
         reg, "hedge_capacity_ratio")
    _run("R1b ticker+date FE", "fwd_maxdd_12w ~ hedge_capacity_ratio + C(ticker) + C(date_grp)",
         reg, "hedge_capacity_ratio")
    _run("R1c bucket+date FE", "fwd_maxdd_12w ~ hedge_capacity_ratio + C(bucket) + C(date_grp)",
         reg, "hedge_capacity_ratio")

    hcap_mean = reg.groupby("ticker")["hedge_capacity_ratio"].transform("mean")
    reg["hcap_between"] = hcap_mean
    reg["hcap_within"] = reg["hedge_capacity_ratio"] - hcap_mean
    _run("R2 Mundlak (date FE)", "fwd_maxdd_12w ~ hcap_within + hcap_between + C(date_grp)",
         reg, ["hcap_within", "hcap_between"])

    _run("R3a drop TLT/LQD/IEF", "fwd_maxdd_12w ~ hedge_capacity_ratio + C(date_grp)",
         reg[~reg["ticker"].isin(["TLT", "LQD", "IEF"])], "hedge_capacity_ratio")
    _run("R3b drop long bucket", "fwd_maxdd_12w ~ hedge_capacity_ratio + C(date_grp)",
         reg[reg["bucket"] != "long"], "hedge_capacity_ratio")

    lo, hi = reg["hedge_capacity_ratio"].quantile([0.01, 0.99])
    reg["hcap_w"] = reg["hedge_capacity_ratio"].clip(lo, hi)
    _run("R4a winsorized 1/99", "fwd_maxdd_12w ~ hcap_w + C(date_grp)", reg, "hcap_w")
    pos = reg[reg["hedge_capacity_ratio"] > 0].copy()
    pos["log_hcap"] = np.log(pos["hedge_capacity_ratio"])
    _run("R4b log(hcap), hcap>0", "fwd_maxdd_12w ~ log_hcap + C(date_grp)", pos, "log_hcap",
         note=f"drops {len(reg) - len(pos)} non-positive")

    # ── Side capacity rebuild (also persisted for 07_paper_artifacts) ────────
    print("Rebuilding side-level capacity from chains.csv ...")
    chains = pd.read_csv(cfg.CHAINS_CSV, parse_dates=["snap_date"])
    core = pd.read_csv(cfg.CORE_PANEL_CSV, parse_dates=["Date"]).rename(
        columns={"Date": "date", "Symbol": "ticker"})
    cap_df, _, _ = build_side_capacity(chains, core)
    cap_df.to_csv(SIDE_CAPACITY_CSV, index=False)
    print(f"  {len(cap_df)} (ticker, snap, side) rows -> {SIDE_CAPACITY_CSV}")

    reg_age = merge_side(reg, cap_df, "total", "hcap_total_chk")
    reg_age["capacity_age_days"] = (reg_age["date"] - reg_age["cap_date"]).dt.days
    _run("R5a + age control",
         "fwd_maxdd_12w ~ hedge_capacity_ratio + capacity_age_days + C(date_grp)",
         reg_age, ["hedge_capacity_ratio", "capacity_age_days"])
    _run("R5b fresh only (age<=30d)", "fwd_maxdd_12w ~ hedge_capacity_ratio + C(date_grp)",
         reg_age[reg_age["capacity_age_days"] <= 30], "hedge_capacity_ratio")
    _run("R6 snapshot weeks only", "fwd_maxdd_12w ~ hedge_capacity_ratio + C(date_grp)",
         reg_age[reg_age["capacity_age_days"] <= 7], "hedge_capacity_ratio")

    reg_side = merge_side(reg, cap_df, "call", "hcap_call")
    reg_side = merge_side(reg_side.drop(columns=["cap_date"], errors="ignore"),
                          cap_df, "put", "hcap_put")
    _run("R7a call capacity", "fwd_maxdd_12w ~ hcap_call + C(date_grp)",
         reg_side.dropna(subset=["hcap_call"]), "hcap_call")
    _run("R7b put capacity", "fwd_maxdd_12w ~ hcap_put + C(date_grp)",
         reg_side.dropna(subset=["hcap_put"]), "hcap_put")
    _run("R7c call+put horse race", "fwd_maxdd_12w ~ hcap_call + hcap_put + C(date_grp)",
         reg_side.dropna(subset=["hcap_call", "hcap_put"]), ["hcap_call", "hcap_put"])

    tbl = pd.DataFrame(_rows)
    tbl["sig"] = np.where(tbl["p_cgm"] < .01, "***",
                 np.where(tbl["p_cgm"] < .05, "**",
                 np.where(tbl["p_cgm"] < .1, "*", "")))
    cfg.ensure_options_dirs()
    tbl.to_csv(cfg.TABLES_DIR / "robustness_spec0.csv", index=False)
    print(tbl.round(4).to_string(index=False))
    print(f"\nWrote {cfg.TABLES_DIR / 'robustness_spec0.csv'}")


if __name__ == "__main__":
    main()
