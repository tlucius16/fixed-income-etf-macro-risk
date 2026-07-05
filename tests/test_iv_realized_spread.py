"""Tests for src.features.iv_realized_spread."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.data.options import _ANNUALISE_FACTOR, build_iv_spread_panel


def _make_core(ticker: str, n: int = 10) -> pd.DataFrame:
    dates = pd.date_range("2022-01-07", periods=n, freq="W-FRI")
    return pd.DataFrame({
        "Date": dates,
        "Symbol": ticker,
        "Return": np.random.default_rng(0).normal(0, 0.005, n),
        "vol_12w": np.full(n, 0.005),
        "fwd_ret_4w": np.random.default_rng(1).normal(0, 0.01, n),
        "fwd_maxdd_12w": -np.abs(np.random.default_rng(2).normal(0, 0.02, n)),
        "fwd_vol_12w": np.full(n, 0.006),
    })


def _make_iv(ticker: str, n: int = 10, iv_val: float = 0.08) -> pd.DataFrame:
    dates = pd.date_range("2022-01-07", periods=n, freq="W-FRI")
    return pd.DataFrame({
        "date": dates,
        "ticker": ticker,
        "iv_30d": np.full(n, iv_val),
    })


class TestBuildIvSpreadPanel:
    def test_annualise_factor_correct(self):
        assert _ANNUALISE_FACTOR == pytest.approx(math.sqrt(52), rel=1e-10)

    def test_vol_12w_annualized_column(self):
        core = _make_core("HYG")
        iv = _make_iv("HYG")
        out = build_iv_spread_panel(iv, core_df=core)
        expected = core["vol_12w"].values * math.sqrt(52)
        np.testing.assert_allclose(out["vol_12w_annualized"].values, expected, rtol=1e-10)

    def test_spread_equals_iv_minus_annualized_vol(self):
        core = _make_core("HYG")
        iv = _make_iv("HYG", iv_val=0.10)
        out = build_iv_spread_panel(iv, core_df=core)
        expected_spread = 0.10 - core["vol_12w"].values * math.sqrt(52)
        np.testing.assert_allclose(out["iv_realized_spread"].values, expected_spread, rtol=1e-10)

    def test_two_tickers_concatenated(self):
        hyg_core = _make_core("HYG")
        lqd_core = _make_core("LQD")
        core = pd.concat([hyg_core, lqd_core], ignore_index=True)

        hyg_iv = _make_iv("HYG", iv_val=0.08)
        lqd_iv = _make_iv("LQD", iv_val=0.05)
        iv = pd.concat([hyg_iv, lqd_iv], ignore_index=True)

        out = build_iv_spread_panel(iv, core_df=core)
        assert set(out["ticker"].unique()) == {"HYG", "LQD"}
        assert len(out) == 20  # 10 rows × 2 tickers

    def test_missing_iv_dates_produce_nan_not_drop(self):
        # IV only has 5 of 10 dates; other rows should have NaN iv_30d
        core = _make_core("HYG", n=10)
        dates_10 = pd.date_range("2022-01-07", periods=10, freq="W-FRI")
        iv = pd.DataFrame({
            "date": dates_10[:5],
            "ticker": "HYG",
            "iv_30d": np.full(5, 0.08),
        })
        out = build_iv_spread_panel(iv, core_df=core)
        assert len(out) == 10
        assert out["iv_30d"].notna().sum() == 5
        assert out["iv_30d"].isna().sum() == 5
        assert out["iv_realized_spread"].isna().sum() == 5

    def test_output_sorted_by_ticker_then_date(self):
        hyg_core = _make_core("HYG")
        lqd_core = _make_core("LQD")
        core = pd.concat([lqd_core, hyg_core], ignore_index=True)  # LQD first
        iv = pd.concat([_make_iv("LQD"), _make_iv("HYG")], ignore_index=True)
        out = build_iv_spread_panel(iv, core_df=core)
        assert out["ticker"].iloc[0] == "HYG"
        assert out["ticker"].iloc[-1] == "LQD"

    def test_required_columns_present(self):
        core = _make_core("HYG")
        iv = _make_iv("HYG")
        out = build_iv_spread_panel(iv, core_df=core)
        expected = {
            "date", "ticker", "vol_12w", "vol_12w_annualized",
            "iv_30d", "iv_realized_spread",
            "fwd_ret_4w", "fwd_maxdd_12w", "fwd_vol_12w",
        }
        assert expected <= set(out.columns)

    def test_call_put_diagnostics_are_preserved(self):
        core = _make_core("HYG", n=2)
        iv = _make_iv("HYG", n=2)
        iv["call_iv"] = [0.08, 0.09]
        iv["put_iv"] = [0.10, np.nan]
        iv["iv_side_count"] = [2, 1]
        iv["iv_source"] = ["call_put_median", "call_only"]

        out = build_iv_spread_panel(iv, core_df=core)

        assert out["call_iv"].tolist() == [0.08, 0.09]
        assert out["iv_side_count"].tolist() == [2, 1]
        assert out["iv_source"].tolist() == ["call_put_median", "call_only"]
