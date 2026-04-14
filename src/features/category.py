from __future__ import annotations

import pandas as pd

# Maps every ETF Database Category in the current universe to one of the
# eleven broad research buckets from the blueprint.  "Other" covers inverse
# and leveraged bond products that are not traditional fixed-income ETFs and
# should typically be excluded from cross-sectional regressions.
#
# International Government Bonds (foreign DM sovereigns: IGOV, BWX, BWZ,
# FLIA, ISHG) get their own "International Government" bucket.  They are not
# US Treasuries and contain no EM exposure — EM sovereign funds sit in the
# separate "Emerging Markets Bonds" ETFdb category.
CATEGORY_MAP: dict[str, str] = {
    "California Munis":                 "Muni",
    "Corporate Bonds":                  "Investment Grade Corporate",
    "Emerging Markets Bonds":           "EM Debt",
    "Government Bonds":                 "Treasury / Government",
    "High Yield Bonds":                 "High Yield",
    "Inflation-Protected Bonds":        "TIPS / Inflation-Linked",
    "International Government Bonds":   "DM Debt",
    "Inverse Bonds":                    "Other",
    "Leveraged Bonds":                  "Other",
    "Money Market":                     "Short Duration / Cash-like",
    "Mortgage Backed Securities":       "Mortgage / Securitized",
    "National Munis":                   "Muni",
    "New York Munis":                   "Muni",
    "Preferred Stock/Convertible Bonds": "Preferred / Hybrid",
    "Total Bond Market":                "Core / Aggregate / Intermediate",
}


def assign_category_bucket(panel: pd.DataFrame) -> pd.DataFrame:
    """Add a *category_bucket* column mapped from *ETF Database Category*.

    Rows whose ETFdb category is absent from the mapping receive NaN so they
    are easy to filter rather than silently absorbed into a catch-all bucket.
    """
    out = panel.copy()
    out["category_bucket"] = out["ETF Database Category"].map(CATEGORY_MAP)
    return out
