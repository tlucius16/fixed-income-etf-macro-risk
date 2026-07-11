from __future__ import annotations

import time
from os import PathLike
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src import config


def make_fred_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fred_series(
    series_id: str,
    api_key: str | None = config.FRED_API_KEY,
    session: requests.Session | None = None,
    sleep_sec: float = 0.25,
    timeout: int = 30,
) -> pd.DataFrame:
    if not api_key:
        raise ValueError("FRED_API_KEY is required for FRED API pulls.")

    session = session or make_fred_session()
    time.sleep(sleep_sec)
    response = session.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={"series_id": series_id, "api_key": api_key, "file_type": "json"},
        timeout=timeout,
    )
    response.raise_for_status()

    df = pd.DataFrame(response.json().get("observations", []))
    df["Date"] = pd.to_datetime(df["date"], errors="coerce")
    df[series_id] = pd.to_numeric(df["value"], errors="coerce")
    return df[["Date", series_id]].dropna().sort_values("Date").reset_index(drop=True)


def pull_gpr_daily(url: str = config.GPR_DAILY_URL) -> pd.DataFrame:
    gpr_daily = pd.read_excel(url, index_col="date")
    gpr_daily.columns = [str(col).strip() for col in gpr_daily.columns]
    gpr_daily = gpr_daily.reset_index().rename(columns={"date": "Date", "GPRD": "GPR"})
    return gpr_daily[["Date", "GPR"]].dropna()


def pull_yahoo_macro_series(ticker: str, column_name: str, period: str = config.DEFAULT_MACRO_PRICE_PERIOD) -> pd.DataFrame:
    data = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
    if data.empty or "Close" not in data:
        raise ValueError(f"No yfinance Close history returned for {ticker}.")

    out = data[["Close"]].rename(columns={"Close": column_name}).reset_index()
    return out.rename(columns={"index": "Date"})[["Date", column_name]]


def pull_fred_weekly_series(
    series_id: str,
    column_name: str,
    api_key: str | None = config.FRED_API_KEY,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    df = fred_series(series_id, api_key=api_key, session=session)
    return to_weekly_friday(df.rename(columns={series_id: column_name}), column_name)


def to_weekly_friday(df: pd.DataFrame, value_col: str, date_col: str = "Date") -> pd.DataFrame:
    out = df.copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce", utc=True).dt.tz_localize(None)
    out = out.dropna(subset=[date_col]).set_index(date_col).sort_index()
    out = out[[value_col]].resample("W-FRI").last().dropna().reset_index()
    out = out.rename(columns={date_col: "Date"})
    return out.drop_duplicates(subset="Date", keep="last").reset_index(drop=True)


def add_weekly_changes(macro_levels: pd.DataFrame, factor_cols: list[str]) -> pd.DataFrame:
    out = macro_levels.sort_values("Date").copy()
    for col in factor_cols:
        out[f"d_{col}"] = out[col].diff()
    return out.dropna(subset=[f"d_{col}" for col in factor_cols]).reset_index(drop=True)


def load_legacy_baml_weekly(path: str | PathLike[str] = config.LEGACY_BAML_WEEKLY_CSV) -> pd.DataFrame:
    legacy = pd.read_csv(path, parse_dates=["Date"])
    legacy = legacy.rename(columns={"BAML_C0A0CM": "BAMLC0A0CM"})
    missing = {"Date", "BAMLC0A0CM"} - set(legacy.columns)
    if missing:
        raise ValueError(f"Legacy BAML file is missing required columns: {sorted(missing)}")
    return (
        legacy[["Date", "BAMLC0A0CM"]]
        .dropna(subset=["Date", "BAMLC0A0CM"])
        .sort_values("Date")
        .drop_duplicates(subset="Date", keep="last")
        .reset_index(drop=True)
    )


def build_hybrid_baml_weekly(
    api_key: str | None = config.FRED_API_KEY,
    session: requests.Session | None = None,
    legacy_path: str | PathLike[str] = config.LEGACY_BAML_WEEKLY_CSV,
) -> pd.DataFrame:
    legacy = load_legacy_baml_weekly(legacy_path)
    live = pull_fred_weekly_series("BAMLC0A0CM", "BAMLC0A0CM", api_key=api_key, session=session)
    return (
        pd.concat([legacy, live], ignore_index=True)
        .sort_values("Date")
        .drop_duplicates(subset="Date", keep="last")
        .reset_index(drop=True)
    )


def build_spx_realized_vol(
    cache_csv: str | PathLike[str] = config.SPX_DAILY_CSV,
    start: str = "2015-01-01",
) -> pd.DataFrame:
    """Weekly (Friday) S&P 500 realized volatility, annualised.

    Columns
    -------
    SPX_RV_21d   : rolling 21-trading-day std of daily log returns × √252
                   (matches the ~1-month horizon of VIX, but realised)
    SPX_RV_12w   : rolling 12-week std of weekly Friday log returns × √52
                   (matches the panel's vol_12w convention)
    d_SPX_RV_21d, d_SPX_RV_12w : weekly first differences

    Daily ^GSPC closes are cached to *cache_csv* on first fetch so offline
    panel rebuilds are deterministic and internet-free.
    """
    cache = Path(cache_csv)
    if cache.exists():
        daily = pd.read_csv(cache, parse_dates=["Date"]).set_index("Date")["Close"]
    else:
        hist = yf.Ticker("^GSPC").history(start=start, interval="1d", auto_adjust=True)
        if hist.empty:
            raise RuntimeError("^GSPC download returned no data.")
        hist.index = pd.to_datetime(hist.index, utc=True).tz_convert(None)
        daily = hist["Close"]
        cache.parent.mkdir(parents=True, exist_ok=True)
        daily.rename_axis("Date").reset_index().to_csv(cache, index=False)

    log_ret = np.log(daily / daily.shift(1))
    rv_21d = (log_ret.rolling(21).std(ddof=1) * np.sqrt(252)).resample("W-FRI").last()

    weekly_px = daily.resample("W-FRI").last()
    weekly_lr = np.log(weekly_px / weekly_px.shift(1))
    rv_12w = weekly_lr.rolling(12).std(ddof=1) * np.sqrt(52)

    out = pd.DataFrame({
        "Date":       rv_21d.index,
        "SPX_RV_21d": rv_21d.values,
        "SPX_RV_12w": rv_12w.reindex(rv_21d.index).values,
    })
    out["d_SPX_RV_21d"] = out["SPX_RV_21d"].diff()
    out["d_SPX_RV_12w"] = out["SPX_RV_12w"].diff()
    return out.dropna(subset=["d_SPX_RV_21d", "d_SPX_RV_12w"]).reset_index(drop=True)


def build_dxy_weekly(
    cache_csv: str | PathLike[str] = config.DXY_DAILY_CSV,
    start: str = "2015-01-01",
) -> pd.DataFrame:
    """Weekly (Friday) US Dollar Index level and change.

    DXY   : Friday close of the ICE dollar index (Yahoo ``DX-Y.NYB``)
    d_DXY : weekly first difference (dollar appreciation = global
            dollar-funding stress; same higher-is-stress sign convention
            as the other composite components)

    Daily closes are cached to *cache_csv* on first fetch so offline panel
    rebuilds are deterministic and internet-free.
    """
    cache = Path(cache_csv)
    if cache.exists():
        daily = pd.read_csv(cache, parse_dates=["Date"]).set_index("Date")["Close"]
    else:
        hist = yf.Ticker("DX-Y.NYB").history(start=start, interval="1d", auto_adjust=True)
        if hist.empty:
            raise RuntimeError("DX-Y.NYB download returned no data.")
        hist.index = pd.to_datetime(hist.index, utc=True).tz_convert(None)
        daily = hist["Close"]
        cache.parent.mkdir(parents=True, exist_ok=True)
        daily.rename_axis("Date").reset_index().to_csv(cache, index=False)

    weekly = daily.resample("W-FRI").last()
    out = pd.DataFrame({"Date": weekly.index, "DXY": weekly.values})
    out["d_DXY"] = out["DXY"].diff()
    return out.dropna(subset=["d_DXY"]).reset_index(drop=True)


def build_weekly_macro_panel(
    api_key: str | None = config.FRED_API_KEY,
    use_hybrid_baml: bool = True,
) -> pd.DataFrame:
    session = make_fred_session()
    weekly_frames: list[pd.DataFrame] = []

    for name, series_id in config.MACRO_SERIES_IDS.items():
        if name == "BAMLC0A0CM" and use_hybrid_baml:
            weekly_frames.append(build_hybrid_baml_weekly(api_key=api_key, session=session))
            continue
        weekly_frames.append(pull_fred_weekly_series(series_id, name, api_key=api_key, session=session))

    vix = pull_yahoo_macro_series("^VIX", "VIX")
    move = pull_yahoo_macro_series("^MOVE", "MOVE")
    gpr = pull_gpr_daily()

    weekly_frames.extend(
        [
            to_weekly_friday(vix, "VIX"),
            to_weekly_friday(move, "MOVE"),
            to_weekly_friday(gpr, "GPR"),
        ]
    )

    macro_levels = weekly_frames[0]
    for right in weekly_frames[1:]:
        macro_levels = pd.merge(macro_levels, right, on="Date", how="inner")

    factor_cols = ["ANFCI", "BAMLC0A0CM", "DGS10", "T10Y2Y", "T5YIE", "VIX", "MOVE", "GPR"]
    macro_weekly = add_weekly_changes(macro_levels, factor_cols)

    # S&P realized vol and DXY: merged after the dropna in add_weekly_changes
    # so their warmup/diff NaNs can't truncate the panel start (left merges,
    # own diffs).
    macro_weekly = macro_weekly.merge(build_spx_realized_vol(), on="Date", how="left")
    return macro_weekly.merge(build_dxy_weekly(), on="Date", how="left")
