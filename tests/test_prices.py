from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.prices import build_weekly_returns, reshape_weekly_returns_long


def test_weekly_returns_do_not_forward_fill_missing_prices():
    prices = pd.DataFrame(
        {
            "ETF_A": [100.0, np.nan, 110.0],
            "ETF_B": [np.nan, 50.0, 55.0],
        },
        index=pd.date_range("2024-01-05", periods=3, freq="W-FRI"),
    )

    returns = build_weekly_returns(prices).reindex(prices.index)

    assert pd.isna(returns.loc["2024-01-12", "ETF_A"])
    assert pd.isna(returns.loc["2024-01-19", "ETF_A"])
    assert np.isclose(returns.loc["2024-01-19", "ETF_B"], 0.10)


def test_reshape_weekly_returns_long_drops_missing_returns_only():
    returns = pd.DataFrame(
        {
            "ETF_A": [np.nan, 0.01],
            "ETF_B": [0.02, np.nan],
        },
        index=pd.date_range("2024-01-05", periods=2, freq="W-FRI"),
    )

    long = reshape_weekly_returns_long(returns)

    assert long[["Date", "Symbol", "Return"]].to_dict("records") == [
        {"Date": pd.Timestamp("2024-01-12"), "Symbol": "ETF_A", "Return": 0.01},
        {"Date": pd.Timestamp("2024-01-05"), "Symbol": "ETF_B", "Return": 0.02},
    ]
