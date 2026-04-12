from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"
LEGACY_EXPORTS_DIR = EXPORTS_DIR / "legacy_csv_exports"

ETFDB_SCREENER_CSV = RAW_DIR / "etfdb_screener.csv"
LEGACY_DATABASE_CSV = LEGACY_EXPORTS_DIR / "database.csv"

WEEKLY_RETURNS_LONG_CSV = PROCESSED_DIR / "weekly_returns_long.csv"
MACRO_FACTORS_WEEKLY_CSV = PROCESSED_DIR / "macro_factors_weekly.csv"
CORE_PANEL_CSV = PROCESSED_DIR / "core_panel.csv"

DEFAULT_MIN_HISTORY_YEARS = 5
DEFAULT_PRICE_PERIOD = "max"
DEFAULT_PRICE_INTERVAL = "1d"
DEFAULT_MACRO_PRICE_PERIOD = "10y"
YAHOO_SLEEP_SECONDS = 0.12

FRED_API_KEY = os.getenv("FRED_API_KEY")

MACRO_SERIES_IDS = {
    "ANFCI": "ANFCI",
    "BAMLC0A0CM": "BAMLC0A0CM",
    "DGS10": "DGS10",
    "T10Y2Y": "T10Y2Y",
    "T5YIE": "T5YIE",
}

RISK_FREE_SERIES_ID = "DTB3"
GPR_DAILY_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"
