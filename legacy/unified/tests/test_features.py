from __future__ import annotations

import numpy as np
import pandas as pd

from legacy.unified.src import config
from legacy.unified.src.features.category import CATEGORY_MAP
from legacy.unified.src.features.structural import parse_assets, parse_expense_ratio


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
