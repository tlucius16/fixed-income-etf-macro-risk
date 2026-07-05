"""Known-value tests for src.features.rate_space.

All numerical assertions are derived analytically from the formulas:
  rate_dv01  = D_i * S * |delta| * 0.0001 * 100
  rate_conv  = 0.5 * D_i² * S * (delta + S * gamma) * 0.0001² * 100
  rate_carry = |theta_daily| / rate_dv01  (NaN if rate_dv01 == 0)
  fund_dv01  = D_i * AUM * 0.0001
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.features.rate_space import add_rate_space_greeks, fund_dv01


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _single_contract(
    *,
    ticker: str = "TLT",
    delta: float = 0.5,
    gamma: float = 0.01,
    theta_daily: float = -0.05,
    underlying: float = 100.0,
    right: str = "C",
) -> pd.DataFrame:
    return pd.DataFrame({
        "ticker":      [ticker],
        "snap_date":   [pd.Timestamp("2024-01-05")],
        "right":       [right],
        "delta":       [delta],
        "gamma":       [gamma],
        "theta_daily": [theta_daily],
        "underlying":  [underlying],
        "quality":     [True],
    })


# ---------------------------------------------------------------------------
# rate_dv01 known-value
# ---------------------------------------------------------------------------

class TestRateDv01:
    def test_call_known_value(self):
        """delta=0.5, S=100, D_i=10 → rate_dv01 = 10*100*0.5*0.0001*100 = 5.0"""
        df  = _single_contract(delta=0.5, underlying=100.0)
        out = add_rate_space_greeks(df, {"TLT": 10.0})
        assert out.loc[0, "rate_dv01"] == pytest.approx(5.0)

    def test_put_uses_abs_delta(self):
        """Put delta = -0.5 → |delta| = 0.5 → same rate_dv01 as call at same |delta|"""
        df  = _single_contract(delta=-0.5, underlying=100.0, right="P")
        out = add_rate_space_greeks(df, {"TLT": 10.0})
        assert out.loc[0, "rate_dv01"] == pytest.approx(5.0)

    def test_scales_linearly_with_D_i(self):
        df = _single_contract(delta=0.5, underlying=100.0)
        out5  = add_rate_space_greeks(df, {"TLT": 5.0})
        out10 = add_rate_space_greeks(df, {"TLT": 10.0})
        assert out10.loc[0, "rate_dv01"] == pytest.approx(2.0 * out5.loc[0, "rate_dv01"])

    def test_scales_linearly_with_S(self):
        df50  = _single_contract(delta=0.5, underlying=50.0)
        df100 = _single_contract(delta=0.5, underlying=100.0)
        out50  = add_rate_space_greeks(df50,  {"TLT": 10.0})
        out100 = add_rate_space_greeks(df100, {"TLT": 10.0})
        assert out100.loc[0, "rate_dv01"] == pytest.approx(2.0 * out50.loc[0, "rate_dv01"])


# ---------------------------------------------------------------------------
# rate_conv known-value
# ---------------------------------------------------------------------------

class TestRateConv:
    def test_known_value(self):
        """delta=0.5, gamma=0.01, S=100, D_i=10
        rate_conv = 0.5 * 100 * 100 * (0.5 + 100*0.01) * 1e-8 * 100
                  = 0.5 * 100 * 100 * 1.5 * 1e-6
                  = 7.5e-3
        """
        df  = _single_contract(delta=0.5, gamma=0.01, underlying=100.0)
        out = add_rate_space_greeks(df, {"TLT": 10.0})
        expected = 0.5 * (10.0 ** 2) * 100.0 * (0.5 + 100.0 * 0.01) * (1e-4 ** 2) * 100.0
        assert out.loc[0, "rate_conv"] == pytest.approx(expected, rel=1e-9)

    def test_put_delta_signed(self):
        """For a put delta=-0.5, rate_conv uses signed delta."""
        df  = _single_contract(delta=-0.5, gamma=0.01, underlying=100.0, right="P")
        out = add_rate_space_greeks(df, {"TLT": 10.0})
        expected = 0.5 * (10.0 ** 2) * 100.0 * (-0.5 + 100.0 * 0.01) * (1e-4 ** 2) * 100.0
        assert out.loc[0, "rate_conv"] == pytest.approx(expected, rel=1e-9)


# ---------------------------------------------------------------------------
# rate_carry known-value
# ---------------------------------------------------------------------------

class TestRateCarry:
    def test_known_value(self):
        """theta=-0.05, rate_dv01=5.0 → carry = 0.05/5.0 = 0.01"""
        df  = _single_contract(delta=0.5, underlying=100.0, theta_daily=-0.05)
        out = add_rate_space_greeks(df, {"TLT": 10.0})
        assert out.loc[0, "rate_dv01"] == pytest.approx(5.0)
        assert out.loc[0, "rate_carry"] == pytest.approx(0.01)

    def test_carry_nan_when_dv01_zero(self):
        """delta=0 → rate_dv01=0 → rate_carry must be NaN, not inf."""
        df  = _single_contract(delta=0.0, underlying=100.0)
        out = add_rate_space_greeks(df, {"TLT": 10.0})
        assert out.loc[0, "rate_dv01"] == pytest.approx(0.0, abs=1e-15)
        assert math.isnan(out.loc[0, "rate_carry"])


# ---------------------------------------------------------------------------
# NaN D_i propagation
# ---------------------------------------------------------------------------

class TestNaNDuration:
    def test_snapshot_duration_column_takes_precedence(self):
        df = pd.concat([_single_contract(), _single_contract()], ignore_index=True)
        df["D_i"] = [5.0, 10.0]
        out = add_rate_space_greeks(df, {"TLT": 99.0})
        assert out.loc[0, "rate_dv01"] == pytest.approx(2.5)
        assert out.loc[1, "rate_dv01"] == pytest.approx(5.0)

    def test_nan_duration_propagates_to_rate_cols(self):
        df = _single_contract()
        out = add_rate_space_greeks(df, {"TLT": float("nan")})
        assert math.isnan(out.loc[0, "rate_dv01"])
        assert math.isnan(out.loc[0, "rate_conv"])
        assert math.isnan(out.loc[0, "rate_carry"])

    def test_missing_ticker_treated_as_nan(self):
        df = _single_contract(ticker="MISSING")
        out = add_rate_space_greeks(df, {"TLT": 10.0})
        assert math.isnan(out.loc[0, "rate_dv01"])

    def test_other_tickers_unaffected(self):
        df = pd.DataFrame({
            "ticker":      ["TLT",  "MISSING"],
            "snap_date":   [pd.Timestamp("2024-01-05")] * 2,
            "right":       ["C", "C"],
            "delta":       [0.5, 0.5],
            "gamma":       [0.01, 0.01],
            "theta_daily": [-0.05, -0.05],
            "underlying":  [100.0, 100.0],
            "quality":     [True, True],
        })
        out = add_rate_space_greeks(df, {"TLT": 10.0})
        assert out.loc[0, "rate_dv01"] == pytest.approx(5.0)
        assert math.isnan(out.loc[1, "rate_dv01"])


# ---------------------------------------------------------------------------
# fund_dv01
# ---------------------------------------------------------------------------

class TestFundDv01:
    def test_known_value(self):
        """D_i=10, AUM=1e9 → fund_dv01 = 10 * 1e9 * 0.0001 = 1e6"""
        assert fund_dv01(10.0, 1e9) == pytest.approx(1e6)

    def test_scales_with_aum(self):
        assert fund_dv01(10.0, 2e9) == pytest.approx(2e6)

    def test_scales_with_duration(self):
        assert fund_dv01(5.0, 1e9) == pytest.approx(5e5)
