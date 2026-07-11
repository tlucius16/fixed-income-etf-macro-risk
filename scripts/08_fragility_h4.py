"""H4 reference estimates (fragility x stress amplification) -> CSV.

Reproduces notebook 03 cell-33 models (2) and (3) exactly — the binary and
continuous stress-interaction specs — and reports each focal coefficient
under three SE treatments:

  se_symbol : one-way cluster by Symbol (the notebook's choice)
  se_date   : one-way cluster by Date  (high_stress varies only by week,
              so this is the binding dimension — Moulton)
  se_cgm    : CGM (2011) two-way Symbol x Date

Writes data/exports/tables/fragility_h4_reference.csv, the parity gate for
julia/scripts/fragility_boot.jl (wild-cluster bootstrap).

Usage
-----
    python scripts/08_fragility_h4.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as scipy_stats

from src import config as cfg
from src.analysis.regression_utils import twoway_cluster_se

OUT_CSV = cfg.TABLES_EXPORT_DIR / "fragility_h4_reference.csv"

FRAG_VARS   = ["vol_12w", "downside_vol_12w", "maxdd_12w"]
STRUCT_VARS = ["log_assets", "ER_clean", "age_years"]
CONTROLS    = "log_assets + ER_clean + age_years + C(category_bucket) + C(year)"

SPECS = {
    "H4 binary (m3b)": (
        f"fwd_maxdd_12w ~ vol_12w * high_stress + downside_vol_12w + maxdd_12w + {CONTROLS}",
        ["vol_12w", "high_stress", "vol_12w:high_stress"],
    ),
    "H4 continuous (m3c)": (
        f"fwd_maxdd_12w ~ vol_12w * stress_index + downside_vol_12w + maxdd_12w + {CONTROLS}",
        ["vol_12w", "stress_index", "vol_12w:stress_index"],
    ),
}


def build_reg3() -> pd.DataFrame:
    panel = pd.read_csv(cfg.CORE_PANEL_CSV, parse_dates=["Date"])
    panel["year"] = panel["Date"].dt.year
    reg3 = panel.dropna(
        subset=["fwd_maxdd_12w", "category_bucket", "high_stress",
                "stress_index", "year"] + FRAG_VARS + STRUCT_VARS
    ).copy()
    return reg3[reg3["category_bucket"] != "Other"]


def main() -> None:
    reg3 = build_reg3()
    n_stress_weeks = int(reg3.drop_duplicates("Date")["high_stress"].sum())
    print(f"reg3: {len(reg3):,} rows, {reg3['Symbol'].nunique()} funds, "
          f"{reg3['Date'].nunique()} weeks ({n_stress_weeks} high-stress)")

    rows = []
    for spec_name, (formula, focal) in SPECS.items():
        m_sym = smf.ols(formula, data=reg3).fit(
            cov_type="cluster", cov_kwds={"groups": reg3["Symbol"]})
        m_dat = smf.ols(formula, data=reg3).fit(
            cov_type="cluster", cov_kwds={"groups": reg3["Date"]})
        _, se_cgm, _ = twoway_cluster_se(formula, reg3, "Symbol", "Date")
        se_cgm = pd.Series(se_cgm, index=m_sym.params.index)

        for var in focal:
            coef = float(m_sym.params[var])
            row = {"spec": spec_name, "var": var, "coef": coef,
                   "n": int(m_sym.nobs), "stress_weeks": n_stress_weeks}
            for label, se in (("symbol", float(m_sym.bse[var])),
                              ("date", float(m_dat.bse[var])),
                              ("cgm", float(se_cgm[var]))):
                p = 2 * (1 - scipy_stats.norm.cdf(abs(coef / se)))
                row[f"se_{label}"] = se
                row[f"p_{label}"] = p
            rows.append(row)

    tbl = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    tbl.to_csv(OUT_CSV, index=False)
    print(tbl.round(4).to_string(index=False))
    print(f"\nWrote {OUT_CSV}")


if __name__ == "__main__":
    main()
