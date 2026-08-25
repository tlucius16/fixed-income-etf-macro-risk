from __future__ import annotations

import math
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
LEGACY_MACRO_FACTORS_CSV = LEGACY_EXPORTS_DIR / "macro_factors.csv"
LEGACY_RAW_PRICES_CSV = LEGACY_EXPORTS_DIR / "raw_prices.csv"
RAW_PRICES_CSV = RAW_DIR / "prices.csv"
SPX_DAILY_CSV = RAW_DIR / "spx_daily.csv"
DXY_DAILY_CSV = RAW_DIR / "dxy_daily.csv"


def _load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv()

PANEL_MODES = {"offline", "live"}
DEFAULT_PANEL_MODE = os.getenv("PANEL_MODE", "offline")

# ── Options screen paths ──────────────────────────────────────────────────────
OPTIONS_SCREEN_RAW_DIR = RAW_DIR / "options_screen"
OPTIONS_SCREEN_DIR     = PROCESSED_DIR / "options_screen"
OPTIONS_PANEL_CSV      = OPTIONS_SCREEN_DIR / "options_panel.csv"
IV_PANEL_CSV           = OPTIONS_SCREEN_DIR / "iv_panel_full.csv"
CALL_PUT_IV_CSV        = OPTIONS_SCREEN_DIR / "call_put_iv_diagnostic.csv"
TICKER_SUMMARY_CSV     = OPTIONS_SCREEN_DIR / "ticker_summary.csv"
CHAINS_CSV             = OPTIONS_SCREEN_DIR / "chains.csv"
SCREEN_SUMMARY_CSV     = OPTIONS_SCREEN_DIR / "summary.csv"

PAPER_DIR   = PROJECT_ROOT / "docs" / "hedge_capacity"
FIGURES_DIR = PAPER_DIR / "figures"
TABLES_DIR  = PAPER_DIR / "tables"

# ── Shared numeric constants ──────────────────────────────────────────────────
WEEKS_PER_YEAR   = 52.0
ANNUALISE_FACTOR = math.sqrt(WEEKS_PER_YEAR)   # weekly vol → annualized

# ── Options quality-filter thresholds (held constant across sample) ───────────
MAX_REL_SPREAD   = 0.35    # (ask-bid)/mid ≤ this
DTE_MIN          = 14      # calendar days to expiry lower bound
DTE_MAX          = 90      # calendar days to expiry upper bound
DELTA_LO         = 0.10    # |delta| lower bound
DELTA_HI         = 0.90    # |delta| upper bound
MIN_DOLLAR_DELTA = 5.0     # dollar directional exposure per share
MIN_DOLLAR_GAMMA = 0.001   # dollar convexity per share
MIN_DOLLAR_VEGA  = 0.01    # dollar vega per share


def ensure_options_dirs() -> None:
    for d in (OPTIONS_SCREEN_RAW_DIR, OPTIONS_SCREEN_DIR, FIGURES_DIR, TABLES_DIR):
        d.mkdir(parents=True, exist_ok=True)


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


def macro_snapshot_csv(mode: str = DEFAULT_PANEL_MODE) -> Path:
    return processed_dir_for_mode(mode) / "macro_snapshot.csv"


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
    "KCPRU": "KCPRU",
}

RISK_FREE_SERIES_ID = "DTB3"
GPR_DAILY_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"
