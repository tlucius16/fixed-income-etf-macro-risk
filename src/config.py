from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"
LEGACY_EXPORTS_DIR = EXPORTS_DIR / "legacy_csv_exports"
TABLES_EXPORT_DIR = EXPORTS_DIR / "tables"
RAW_LIVE_DIR = RAW_DIR / "live"
PROCESSED_OFFLINE_DIR = PROCESSED_DIR / "offline"
PROCESSED_LIVE_DIR = PROCESSED_DIR / "live"

ETFDB_SCREENER_CSV = RAW_DIR / "etfdb_screener.csv"
LEGACY_DATABASE_CSV = LEGACY_EXPORTS_DIR / "database.csv"
LEGACY_BAML_WEEKLY_CSV = LEGACY_EXPORTS_DIR / "baml_w.csv"

PANEL_MODES = {"offline", "live"}
DEFAULT_PANEL_MODE = os.getenv("PANEL_MODE", "offline")


def processed_dir_for_mode(mode: str = DEFAULT_PANEL_MODE) -> Path:
    normalized = mode.lower()
    if normalized == "offline":
        return PROCESSED_OFFLINE_DIR
    if normalized == "live":
        return PROCESSED_LIVE_DIR
    raise ValueError(f"Unknown panel mode {mode!r}. Expected one of {sorted(PANEL_MODES)}.")


def weekly_returns_long_csv(mode: str = DEFAULT_PANEL_MODE) -> Path:
    return processed_dir_for_mode(mode) / "weekly_returns_long.csv"


def macro_factors_weekly_csv(mode: str = DEFAULT_PANEL_MODE) -> Path:
    return processed_dir_for_mode(mode) / "macro_factors_weekly.csv"


def core_panel_csv(mode: str = DEFAULT_PANEL_MODE) -> Path:
    return processed_dir_for_mode(mode) / "core_panel.csv"


WEEKLY_RETURNS_LONG_CSV = weekly_returns_long_csv()
MACRO_FACTORS_WEEKLY_CSV = macro_factors_weekly_csv()
CORE_PANEL_CSV = core_panel_csv()

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
