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


def _date_range_text(df: pd.DataFrame, date_col: str = "Date") -> str:
    if date_col not in df.columns or df.empty:
        return "n/a"

    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if dates.empty:
        return "n/a"
    return f"{dates.min().date()} to {dates.max().date()} ({dates.nunique():,} dates)"


def _print_panel_diagnostic(label: str, df: pd.DataFrame, symbol_col: str | None = None) -> None:
    parts = [f"[diagnostic] {label}: rows={len(df):,}", f"dates={_date_range_text(df)}"]
    if symbol_col and symbol_col in df.columns:
        parts.append(f"{symbol_col.lower()}s={df[symbol_col].nunique():,}")
    print(" | ".join(parts))


def build_core_panel(
    screener_csv: str | Path | None = None,
    output_dir: str | Path | None = None,
    min_years: int = config.DEFAULT_MIN_HISTORY_YEARS,
    fred_api_key: str | None = config.FRED_API_KEY,
    panel_mode: str = "live",
) -> pd.DataFrame:
    screener_path = resolve_screener_csv(screener_csv)
    output_path = Path(output_dir) if output_dir is not None else config.processed_dir_for_mode(panel_mode)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata, tickers = build_universe(screener_path, min_years=min_years, filter_history=True)
    print(f"[diagnostic] universe: metadata_rows={len(metadata):,} | tickers={len(tickers):,}")

    etf_prices_data = download_price_history(tickers)
    raw_prices = build_daily_price_matrix(etf_prices_data)
    weekly_prices = build_weekly_close_matrix(raw_prices)
    returns_w = build_weekly_returns(weekly_prices)
    returns_w_long = reshape_weekly_returns_long(returns_w)
    _print_panel_diagnostic("weekly_returns_long", returns_w_long, symbol_col="Symbol")

    macro_factors = build_weekly_macro_panel(api_key=fred_api_key)
    rf_w = build_weekly_risk_free(api_key=fred_api_key)
    _print_panel_diagnostic("macro_factors_weekly", macro_factors)
    _print_panel_diagnostic("risk_free_weekly", rf_w)

    core_panel = returns_w_long.merge(macro_factors, on="Date", how="inner")
    _print_panel_diagnostic("after returns x macro merge", core_panel, symbol_col="Symbol")
    core_panel = core_panel.merge(rf_w, on="Date", how="left")
    _print_panel_diagnostic("after risk-free merge", core_panel, symbol_col="Symbol")
    core_panel = core_panel.merge(metadata, on="Symbol", how="left")
    _print_panel_diagnostic("after metadata merge", core_panel, symbol_col="Symbol")
    core_panel["RET_XS"] = core_panel["Return"] - core_panel["RF_w"]
    core_panel = add_structural_features(core_panel)
    core_panel = assign_category_bucket(core_panel)
    core_panel = add_stress_index(core_panel)
    core_panel = core_panel.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    core_panel = add_rolling_risk_metrics(core_panel)
    core_panel = add_forward_outcomes(core_panel)
    _print_panel_diagnostic("final core_panel", core_panel, symbol_col="Symbol")

    returns_w_long.to_csv(output_path / "weekly_returns_long.csv", index=False)
    macro_factors.to_csv(output_path / "macro_factors_weekly.csv", index=False)
    core_panel.to_csv(output_path / "core_panel.csv", index=False)

    return core_panel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the fixed-income ETF macro-risk core panel.")
    parser.add_argument("--screener-csv", default=None, help="Path to ETFDB screener CSV input.")
    parser.add_argument(
        "--panel-mode",
        choices=sorted(config.PANEL_MODES),
        default="live",
        help="Processed panel slot to write when --output-dir is not provided.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for processed CSV outputs. Overrides --panel-mode.",
    )
    parser.add_argument("--min-years", type=int, default=config.DEFAULT_MIN_HISTORY_YEARS, help="Minimum ETF price history.")
    parser.add_argument("--fred-api-key", default=config.FRED_API_KEY, help="FRED API key. Defaults to FRED_API_KEY env var.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel = build_core_panel(
        screener_csv=args.screener_csv,
        output_dir=args.output_dir,
        panel_mode=args.panel_mode,
        min_years=args.min_years,
        fred_api_key=args.fred_api_key,
    )
    output_dir = Path(args.output_dir) if args.output_dir is not None else config.processed_dir_for_mode(args.panel_mode)
    print(f"Wrote core panel with {len(panel):,} rows to {output_dir}.")


if __name__ == "__main__":
    main()
