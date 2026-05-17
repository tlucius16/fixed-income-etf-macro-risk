"""Rebuild core_panel.csv from legacy cached files (no FRED API required).

Sources:
  - data/exports/legacy_csv_exports/macro_factors.csv  (2016-04-15 to 2026-04)
  - data/exports/legacy_csv_exports/returns_w_long.csv (2002-08 to 2026-04)
  - data/exports/legacy_csv_exports/rf_w.csv           (1954 to 2026-04)
  - data/exports/legacy_csv_exports/database.csv       (ETF metadata)
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from src import config
from src.features.category import assign_category_bucket
from src.features.forward_outcomes import add_forward_outcomes
from src.features.rolling_risk import add_rolling_risk_metrics
from src.features.stress_index import add_stress_index
from src.features.structural import add_structural_features

LEGACY = ROOT / "data" / "exports" / "legacy_csv_exports"

# ── 1. Macro panel ─────────────────────────────────────────────────────────
print("Loading legacy macro factors...")
macro = pd.read_csv(LEGACY / "macro_factors.csv", parse_dates=["Date"])
macro = macro.sort_values("Date").reset_index(drop=True)

# Normalise column names to match current pipeline expectations
macro = macro.rename(columns={
    "BAML_C0A0CM":   "BAMLC0A0CM",
    "d_BAML_C0A0CM": "d_BAMLC0A0CM",
})
# The current pipeline also expects 'd_T5YIE'; legacy has it already.
print(f"  Macro: {macro.Date.min().date()} to {macro.Date.max().date()}  "
      f"| {len(macro)} weeks  | cols: {list(macro.columns)}")

# ── 2. Risk-free rate ──────────────────────────────────────────────────────
print("Loading risk-free rate...")
rf = pd.read_csv(LEGACY / "rf_w.csv", parse_dates=["Date"])
rf = rf[["Date", "RF_w"]].sort_values("Date")
print(f"  RF:    {rf.Date.min().date()} to {rf.Date.max().date()}")

# ── 3. ETF weekly returns ──────────────────────────────────────────────────
print("Loading ETF weekly returns...")
ret = pd.read_csv(LEGACY / "returns_w_long.csv", parse_dates=["Date"])
ret = ret.rename(columns={"Ticker": "Symbol"})
ret = ret[["Date", "Symbol", "Return"]].sort_values(["Symbol", "Date"]).reset_index(drop=True)
print(f"  Returns: {ret.Date.min().date()} to {ret.Date.max().date()}  "
      f"| {ret.Symbol.nunique()} ETFs  | {len(ret):,} rows")

# ── 4. ETF metadata ────────────────────────────────────────────────────────
print("Loading ETF metadata...")
meta_raw = pd.read_csv(LEGACY / "database.csv")
meta = meta_raw[["Symbol", "Name", "Assets", "ETF Database Category", "ER", "Inception"]].copy()
meta = meta.drop_duplicates("Symbol").reset_index(drop=True)
print(f"  Metadata: {len(meta)} ETFs")

# ── 5. Merge panel ─────────────────────────────────────────────────────────
print("Merging panel...")
# Returns ← macro (inner: only weeks where both exist)
panel = ret.merge(macro, on="Date", how="inner")
# ← RF (left: keep all return rows, fill missing RF with 0)
panel = panel.merge(rf, on="Date", how="left")
panel["RF_w"] = panel["RF_w"].fillna(0)
# ← Metadata (left: keep all ETFs)
panel = panel.merge(meta, on="Symbol", how="left")

panel = panel.sort_values(["Symbol", "Date"]).reset_index(drop=True)
print(f"  Panel after merge: {len(panel):,} rows  | "
      f"{panel.Symbol.nunique()} ETFs  | "
      f"{panel.Date.min().date()} to {panel.Date.max().date()}")

# ── 6. Feature engineering ─────────────────────────────────────────────────
print("Adding excess returns...")
panel["RET_XS"] = panel["Return"] - panel["RF_w"]

print("Adding structural features...")
panel["Inception"] = pd.to_datetime(panel["Inception"], errors="coerce")
panel = add_structural_features(panel)

print("Assigning category buckets...")
panel = assign_category_bucket(panel)

print("Adding stress index...")
panel = add_stress_index(panel)

print("Adding rolling risk metrics (12w)...")
panel = add_rolling_risk_metrics(panel)

print("Adding forward outcomes...")
panel = add_forward_outcomes(panel)

panel = panel.sort_values(["Symbol", "Date"]).reset_index(drop=True)

# ── 7. Save ────────────────────────────────────────────────────────────────
offline_dir = config.processed_dir_for_mode("offline")
offline_dir.mkdir(parents=True, exist_ok=True)

macro.to_csv(offline_dir / "macro_factors_weekly.csv", index=False)
ret.to_csv(offline_dir / "weekly_returns_long.csv", index=False)

out_path = offline_dir / "core_panel.csv"
print(f"Saving to {out_path}...")
panel.to_csv(out_path, index=False)

print(f"\nDone. Panel: {len(panel):,} rows  | "
      f"{panel.Symbol.nunique()} ETFs  | "
      f"{panel.Date.min().date()} to {panel.Date.max().date()}")
print(f"vol_12w coverage: {panel['vol_12w'].notna().sum():,} rows "
      f"({100*panel['vol_12w'].notna().mean():.1f}%)")

# Quick summary by year
yearly = panel.groupby(panel.Date.dt.year).agg(
    etfs=("Symbol", "nunique"),
    rows=("Symbol", "count"),
    vol12w_pct=("vol_12w", lambda x: f"{100*x.notna().mean():.0f}%")
)
print("\nRows per year:")
print(yearly.to_string())
