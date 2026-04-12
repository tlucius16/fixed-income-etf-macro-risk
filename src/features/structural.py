from __future__ import annotations

import numpy as np
import pandas as pd


def compute_age_years(dates: pd.Series, inception_dates: pd.Series) -> pd.Series:
    date_values = pd.to_datetime(dates, errors="coerce")
    inception_values = pd.to_datetime(inception_dates, errors="coerce")
    return (date_values - inception_values).dt.days / 365.25


def parse_assets(value: object) -> float:
    if pd.isna(value):
        return np.nan

    text = str(value).strip().replace("$", "").replace(",", "")
    if not text or text in {"-", "--"}:
        return np.nan

    multiplier = 1.0
    suffix = text[-1].upper()
    if suffix == "K":
        multiplier = 1_000
        text = text[:-1]
    elif suffix == "M":
        multiplier = 1_000_000
        text = text[:-1]
    elif suffix == "B":
        multiplier = 1_000_000_000
        text = text[:-1]
    elif suffix == "T":
        multiplier = 1_000_000_000_000
        text = text[:-1]

    return pd.to_numeric(text, errors="coerce") * multiplier


def parse_expense_ratio(value: object) -> float:
    if pd.isna(value):
        return np.nan

    text = str(value).strip().replace("%", "")
    if not text or text in {"-", "--"}:
        return np.nan

    parsed = pd.to_numeric(text, errors="coerce")
    return parsed / 100 if pd.notna(parsed) else np.nan


def add_structural_features(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    out["age_years"] = compute_age_years(out["Date"], out["Inception"])
    out["Assets_clean"] = out["Assets"].map(parse_assets)
    out["ER_clean"] = out["ER"].map(parse_expense_ratio)
    out["log_assets"] = np.log(out["Assets_clean"].where(out["Assets_clean"] > 0))
    return out
