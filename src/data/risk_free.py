from __future__ import annotations

import pandas as pd

from src import config
from src.data.macro import fred_series, make_fred_session, to_weekly_friday


def annualized_percent_to_weekly_decimal(series: pd.Series) -> pd.Series:
    return series.astype(float) / 100 / 52


def build_weekly_risk_free(api_key: str | None = config.FRED_API_KEY) -> pd.DataFrame:
    session = make_fred_session()
    rf = fred_series(config.RISK_FREE_SERIES_ID, api_key=api_key, session=session)
    rf_w = to_weekly_friday(rf, config.RISK_FREE_SERIES_ID)
    rf_w["RF_w"] = annualized_percent_to_weekly_decimal(rf_w[config.RISK_FREE_SERIES_ID])
    return rf_w[["Date", "RF_w"]]
