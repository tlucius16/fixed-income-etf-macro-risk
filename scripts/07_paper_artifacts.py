"""Paper tables and figures (Sections 2, 4, 5) -> docs/options_paper/.

Canonical producer of the artifacts previously generated in notebook 05
Section 11 (the notebook now displays these files):

  tables/capacity_accounting.csv     figures/24_missing_market.png
  tables/call_put_dv01_ratio.csv     figures/25_call_put_ratio.png
  tables/duration_validation.csv     figures/26_duration_validation.png
  tables/universe.csv

Usage
-----
    python scripts/07_paper_artifacts.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src import config as cfg
from src.analysis.side_capacity import build_side_capacity
from src.data.options_universe import BUCKET_ORDER, ETF_METADATA, UNIVERSE, ticker_bucket
from src.features.options_features import estimate_rolling_rate_duration

COLORS = {"short": "#4C72B0", "intermediate": "#DD8452",
          "long": "#55A868", "credit": "#C44E52", "other": "#937860"}


def main() -> None:
    sns.set_theme(style="ticks", palette="deep", font_scale=1.1)
    cfg.ensure_options_dirs()

    chains = pd.read_csv(cfg.CHAINS_CSV, parse_dates=["snap_date"])
    core = pd.read_csv(cfg.CORE_PANEL_CSV, parse_dates=["Date"]).rename(
        columns={"Date": "date", "Symbol": "ticker"})
    cap_r, passing_r, dmap_r = build_side_capacity(chains, core)
    SNAP_LATEST = cap_r["snap_date"].max()

    # ── Table: capacity accounting ───────────────────────────────────────────
    def _side_at(t, side, col, snap=None):
        g = cap_r[(cap_r["ticker"] == t) & (cap_r["side"] == side)]
        if snap is not None:
            g = g[g["snap_date"] == snap]
        v = g[col]
        return float(v.iloc[0]) if len(v) else np.nan

    pq = passing_r[passing_r["snap_date"] == SNAP_LATEST].copy()
    pq["rel_spread"] = (pq["ask"] - pq["bid"]) / ((pq["ask"] + pq["bid"]) / 2)
    spread_latest = pq.groupby("ticker")["rel_spread"].median()
    put_hist = (cap_r[cap_r["side"] == "put"].groupby("ticker")["chain_rate_dv01"]
                .agg(put_dv01_med_all_snaps="median", put_dv01_min="min", put_dv01_max="max"))

    rows = []
    for t in sorted(cap_r["ticker"].unique()):
        D = dmap_r.get(t, np.nan)
        put_dv01 = _side_at(t, "put", "chain_rate_dv01", SNAP_LATEST)
        fund_dv01 = _side_at(t, "total", "fund_dv01", SNAP_LATEST)
        pos = put_dv01 / (D * 1e-4) / 1e6 if np.isfinite(put_dv01) and np.isfinite(D) and D > 0 else np.nan
        rows.append({
            "ticker": t, "bucket": ticker_bucket(t), "D_i": D,
            "put_dv01": put_dv01,
            "call_dv01": _side_at(t, "call", "chain_rate_dv01", SNAP_LATEST),
            "fund_dv01": fund_dv01,
            "put_capacity_ratio": put_dv01 / fund_dv01 if np.isfinite(put_dv01) and np.isfinite(fund_dv01) else np.nan,
            "hedgeable_pos_100pct_musd": pos,
            "hedgeable_pos_10pct_musd": pos * 0.10 if np.isfinite(pos) else np.nan,
            "median_rel_spread": spread_latest.get(t, np.nan),
            "quality_contracts": _side_at(t, "total", "quality_contracts", SNAP_LATEST),
        })
    acct = (pd.DataFrame(rows).merge(put_hist, on="ticker", how="left")
            .sort_values("fund_dv01", ascending=False))
    acct.to_csv(cfg.TABLES_DIR / "capacity_accounting.csv", index=False)
    print(f"capacity_accounting.csv: {len(acct)} tickers (snapshot {SNAP_LATEST.date()})")

    # ── Figure 24: missing market ────────────────────────────────────────────
    mm = acct.copy()
    mm["aum_busd"] = mm["ticker"].map(lambda t: ETF_METADATA[t]["aum"] / 1e9)
    plot_df = mm[mm["hedgeable_pos_100pct_musd"] > 0].dropna(subset=["aum_busd"])
    zero_put = sorted(mm.loc[(mm["put_dv01"].fillna(0) <= 0)
                             | mm["hedgeable_pos_100pct_musd"].isna(), "ticker"])
    fig, ax = plt.subplots(figsize=(8, 6))
    xs = np.array([0.2, 200.0])
    for frac, lbl in [(1.0, "100% of fund"), (0.1, "10%"), (0.01, "1%"), (0.001, "0.1%")]:
        ax.plot(xs, xs * 1000 * frac, ls="--", lw=0.8, color="0.75", zorder=1)
        ax.annotate(lbl, (xs[1], xs[1] * 1000 * frac), fontsize=7, color="0.5",
                    xytext=(4, 0), textcoords="offset points", va="center")
    for _, r in plot_df.iterrows():
        ax.scatter(r["aum_busd"], r["hedgeable_pos_100pct_musd"],
                   color=COLORS.get(r["bucket"], "#888"), s=55, zorder=3,
                   edgecolor="white", linewidth=0.8)
        ax.annotate(r["ticker"], (r["aum_busd"], r["hedgeable_pos_100pct_musd"]),
                    fontsize=8, xytext=(5, 3), textcoords="offset points")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.2, 400)
    ax.set_xlabel("Fund AUM ($B, log)")
    ax.set_ylabel("Position hedgeable by entire put book ($M, log)")
    ax.set_title(f"The Missing Hedge Market: Put-Side Capacity vs. Fund Size ({SNAP_LATEST.date()})")
    handles = [plt.Line2D([], [], marker="o", ls="", color=COLORS[b], label=b)
               for b in BUCKET_ORDER if b in plot_df["bucket"].values]
    ax.legend(handles=handles, loc="upper left", fontsize=8,
              title="Duration bucket", title_fontsize=8)
    ax.grid(True, which="major", lw=0.3, color="0.9")
    sns.despine()
    plt.tight_layout(rect=[0, 0.07, 1, 1])
    fig.text(0.02, 0.01, "No quality put depth: " + ", ".join(zero_put),
             fontsize=7.5, color="0.35", va="bottom")
    fig.savefig(cfg.FIGURES_DIR / "24_missing_market.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ── Table + Figure 25: call/put anatomy ──────────────────────────────────
    cp = acct[["ticker", "bucket", "call_dv01", "put_dv01"]].copy()
    cp["call_put_ratio"] = cp["call_dv01"] / cp["put_dv01"].where(cp["put_dv01"] > 0)
    cp = cp.sort_values("call_put_ratio", ascending=True)
    cp.to_csv(cfg.TABLES_DIR / "call_put_dv01_ratio.csv", index=False)

    plot_cp = cp[np.isfinite(cp["call_put_ratio"])]
    no_put = sorted(cp.loc[cp["put_dv01"].fillna(0) <= 0, "ticker"])
    put_only = sorted(cp.loc[(cp["put_dv01"] > 0)
                             & (cp["call_dv01"].fillna(0) <= 0), "ticker"])
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(plot_cp) + 1.5))
    ax.barh(plot_cp["ticker"], plot_cp["call_put_ratio"],
            color=plot_cp["bucket"].map(COLORS), height=0.62)
    ax.axvline(1, color="0.3", lw=1)
    ax.annotate("parity", (1, len(plot_cp) - 0.3), fontsize=7.5, color="0.4",
                ha="center", va="bottom")
    for y, (_, r) in enumerate(plot_cp.iterrows()):
        ax.annotate(f'{r["call_put_ratio"]:.1f}×', (r["call_put_ratio"], y),
                    fontsize=7.5, color="0.35", xytext=(4, 0),
                    textcoords="offset points", va="center")
    ax.set_xscale("log")
    ax.set_xlabel("Call ÷ put chain DV01 (log scale)")
    ax.set_title(f"A Call-Sided Book: Standing DV01 by Side ({SNAP_LATEST.date()})")
    handles = [plt.Line2D([], [], marker="s", ls="", color=COLORS[b], label=b)
               for b in BUCKET_ORDER if b in plot_cp["bucket"].values]
    ax.legend(handles=handles, loc="center right", fontsize=8,
              title="Duration bucket", title_fontsize=8)
    ax.grid(True, axis="x", lw=0.3, color="0.9")
    sns.despine()
    plt.tight_layout(rect=[0, 0.11, 1, 1])
    fig.text(0.02, 0.055, "Call-only book (no quality puts): " + ", ".join(no_put),
             fontsize=7.5, color="0.35", va="bottom")
    fig.text(0.02, 0.01, "Put-only book (no quality calls): " + ", ".join(put_only),
             fontsize=7.5, color="0.35", va="bottom")
    fig.savefig(cfg.FIGURES_DIR / "25_call_put_ratio.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"call_put_dv01_ratio.csv: {len(cp)} tickers "
          f"({len(plot_cp)} two-sided, {len(no_put)} call-only, {len(put_only)} put-only)")

    # ── Table + Figure 26: duration validation ───────────────────────────────
    dur = estimate_rolling_rate_duration(core[core["ticker"].isin(ETF_METADATA)].copy())
    dur["duration_ok"] = (
        (dur.get("duration_r2", pd.Series(0.0, index=dur.index)) >= 0.20)
        & (dur["realized_rate_duration"].abs() >= 1.0))
    dur_latest = (dur.sort_values("date").groupby("ticker", as_index=False).tail(1)
                  [["ticker", "date", "realized_rate_duration", "duration_r2", "duration_ok"]])
    dur_latest["published_duration"] = dur_latest["ticker"].map(
        lambda t: ETF_METADATA.get(t, {}).get("eff_duration"))
    dur_latest["bucket"] = dur_latest["ticker"].map(ticker_bucket)
    dur_val = dur_latest.dropna(subset=["published_duration", "realized_rate_duration"]).copy()
    dur_val.to_csv(cfg.TABLES_DIR / "duration_validation.csv", index=False)

    corr = dur_val["published_duration"].corr(dur_val["realized_rate_duration"])
    fig, ax = plt.subplots(figsize=(7, 6))
    lim = max(dur_val["published_duration"].max(),
              dur_val["realized_rate_duration"].max()) * 1.1
    ax.plot([0, lim], [0, lim], ls="--", lw=0.8, color="0.7", zorder=1)
    for _, r in dur_val.iterrows():
        filled = bool(r["duration_ok"])
        ax.scatter(r["published_duration"], r["realized_rate_duration"],
                   facecolor=COLORS.get(r["bucket"], "#888") if filled else "white",
                   edgecolor=COLORS.get(r["bucket"], "#888"), linewidth=1.2, s=50, zorder=3)
    label_us = dur_val[(dur_val["published_duration"] > 10)
                       | ((dur_val["realized_rate_duration"]
                           - dur_val["published_duration"]).abs() > 2)]
    for _, r in label_us.iterrows():
        ax.annotate(r["ticker"], (r["published_duration"], r["realized_rate_duration"]),
                    fontsize=8, xytext=(5, 3), textcoords="offset points")
    ax.set_xlabel("Published effective duration (fact sheet)")
    ax.set_ylabel("Empirical rate duration (52w rolling)")
    ax.set_title(f"Duration Validation: Empirical vs. Published (r = {corr:.2f})")
    handles = [plt.Line2D([], [], marker="o", ls="", color=COLORS[b], label=b)
               for b in BUCKET_ORDER if b in dur_val["bucket"].values]
    handles.append(plt.Line2D([], [], marker="o", ls="", markerfacecolor="white",
                              markeredgecolor="0.4", label="fails quality gate"))
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    ax.grid(True, lw=0.3, color="0.9")
    sns.despine()
    plt.tight_layout()
    fig.savefig(cfg.FIGURES_DIR / "26_duration_validation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"duration_validation.csv: r = {corr:.3f} on {len(dur_val)} tickers")

    # ── Table: universe ──────────────────────────────────────────────────────
    uni = pd.DataFrame([
        {"ticker": t, "category": cat, "duration_bucket": ticker_bucket(t),
         "aum_busd": ETF_METADATA[t]["aum"] / 1e9,
         "published_duration": ETF_METADATA[t]["eff_duration"],
         "expense_ratio_bps": ETF_METADATA[t]["expense_ratio"] * 1e4}
        for t, cat in UNIVERSE.items()
    ]).sort_values(["duration_bucket", "published_duration"], ascending=[True, False])
    uni.to_csv(cfg.TABLES_DIR / "universe.csv", index=False)
    print(f"universe.csv: {len(uni)} tickers")


if __name__ == "__main__":
    main()
