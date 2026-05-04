from __future__ import annotations

import numpy as np
import pandas as pd

from src import config
from src.features.category import CATEGORY_MAP
from src.features.forward_outcomes import add_forward_outcomes
from src.features.structural import parse_assets, parse_expense_ratio


def test_forward_outcomes_use_future_returns_only():
    panel = pd.DataFrame(
        {
            "Symbol": ["AAA"] * 6,
            "Date": pd.date_range("2024-01-05", periods=6, freq="W-FRI"),
            "Return": [0.01, 0.02, -0.01, 0.03, 0.04, -0.02],
        }
    )

    out = add_forward_outcomes(panel, fwd_short=2, fwd_long=3, min_periods_long=3)

    assert np.isclose(out.loc[0, "fwd_ret_4w"], (1 + 0.02) * (1 - 0.01) - 1)
    assert np.isclose(out.loc[1, "fwd_ret_4w"], (1 - 0.01) * (1 + 0.03) - 1)
    assert pd.isna(out.loc[4, "fwd_ret_4w"])
    assert pd.isna(out.loc[5, "fwd_ret_4w"])


def test_structural_parsers_handle_etfdb_formats_and_missing_markers():
    assert parse_assets("$1.2B") == 1_200_000_000
    assert parse_assets("42,609,200") == 42_609_200
    assert parse_assets("$750M") == 750_000_000
    assert pd.isna(parse_assets("--"))

    assert parse_expense_ratio("0.19%") == 0.0019
    assert parse_expense_ratio("1.00%") == 0.01
    assert pd.isna(parse_expense_ratio("-"))


def test_current_offline_panel_categories_are_mapped_when_available():
    panel_path = config.core_panel_csv("offline")
    if not panel_path.exists():
        return

    panel = pd.read_csv(panel_path, usecols=["ETF Database Category"])
    current_categories = set(panel["ETF Database Category"].dropna().unique())

    assert current_categories - set(CATEGORY_MAP) == set()
