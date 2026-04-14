from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src import config
from src.data.macro import build_weekly_macro_panel
from src.data.prices import (
    build_daily_price_matrix,
    build_weekly_close_matrix,
    build_weekly_returns,
    download_price_history,
    reshape_weekly_returns_long,
)
from src.data.risk_free import build_weekly_risk_free
from src.data.universe import build_universe
from src.features.category import assign_category_bucket
from src.features.forward_outcomes import add_forward_outcomes
from src.features.rolling_risk import add_rolling_risk_metrics
from src.features.stress_index import add_stress_index
from src.features.structural import add_structural_features


def resolve_screener_csv(path: str | Path | None) -> Path:
    if path:
        candidate = Path(path)
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"ETFDB screener CSV not found: {candidate}")

    if config.ETFDB_SCREENER_CSV.exists():
        return config.ETFDB_SCREENER_CSV
    if config.LEGACY_DATABASE_CSV.exists():
        return config.LEGACY_DATABASE_CSV

    raise FileNotFoundError(
        "No ETFDB screener CSV found. Place one at data/raw/etfdb_screener.csv "
        "or keep the legacy database.csv export in data/exports/legacy_csv_exports/."
    )


def build_core_panel(
    screener_csv: str | Path | None = None,
    output_dir: str | Path = config.PROCESSED_DIR,
    min_years: int = config.DEFAULT_MIN_HISTORY_YEARS,
    fred_api_key: str | None = config.FRED_API_KEY,
) -> pd.DataFrame:
    screener_path = resolve_screener_csv(screener_csv)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata, tickers = build_universe(screener_path, min_years=min_years, filter_history=True)

    etf_prices_data = download_price_history(tickers)
    raw_prices = build_daily_price_matrix(etf_prices_data)
    weekly_prices = build_weekly_close_matrix(raw_prices)
    returns_w = build_weekly_returns(weekly_prices)
    returns_w_long = reshape_weekly_returns_long(returns_w)

    macro_factors = build_weekly_macro_panel(api_key=fred_api_key)
    rf_w = build_weekly_risk_free(api_key=fred_api_key)

    core_panel = returns_w_long.merge(macro_factors, on="Date", how="inner")
    core_panel = core_panel.merge(rf_w, on="Date", how="left")
    core_panel = core_panel.merge(metadata, on="Symbol", how="left")
    core_panel["RET_XS"] = core_panel["Return"] - core_panel["RF_w"]
    core_panel = add_structural_features(core_panel)
    core_panel = assign_category_bucket(core_panel)
    core_panel = add_stress_index(core_panel)
    core_panel = core_panel.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    core_panel = add_rolling_risk_metrics(core_panel)
    core_panel = add_forward_outcomes(core_panel)

    returns_w_long.to_csv(output_path / "weekly_returns_long.csv", index=False)
    macro_factors.to_csv(output_path / "macro_factors_weekly.csv", index=False)
    core_panel.to_csv(output_path / "core_panel.csv", index=False)

    return core_panel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the fixed-income ETF macro-risk core panel.")
    parser.add_argument("--screener-csv", default=None, help="Path to ETFDB screener CSV input.")
    parser.add_argument("--output-dir", default=str(config.PROCESSED_DIR), help="Directory for processed CSV outputs.")
    parser.add_argument("--min-years", type=int, default=config.DEFAULT_MIN_HISTORY_YEARS, help="Minimum ETF price history.")
    parser.add_argument("--fred-api-key", default=config.FRED_API_KEY, help="FRED API key. Defaults to FRED_API_KEY env var.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel = build_core_panel(
        screener_csv=args.screener_csv,
        output_dir=args.output_dir,
        min_years=args.min_years,
        fred_api_key=args.fred_api_key,
    )
    print(f"Wrote core panel with {len(panel):,} rows.")


if __name__ == "__main__":
    main()
