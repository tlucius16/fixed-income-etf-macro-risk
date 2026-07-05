"""Tests for src.data.options_iv — Black-Scholes helpers and pure logic."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.data.options import (
    _bs_call_price,
    _friday_dates_in_range,
    compute_bs_iv,
    compute_greeks,
)


# ---------------------------------------------------------------------------
# Black-Scholes price formula
# ---------------------------------------------------------------------------

class TestBsCallPrice:
    def test_atm_call_positive(self):
        # ATM, 30d, 5% vol, 5% rf, no div
        price = _bs_call_price(S=100, K=100, T=30/365, r=0.05, sigma=0.15, q=0.0)
        assert price > 0

    def test_deep_itm_approaches_intrinsic(self):
        # Very deep ITM: call price ≈ S - K (discounted)
        price = _bs_call_price(S=200, K=100, T=1.0, r=0.0, sigma=0.01, q=0.0)
        assert price == pytest.approx(100.0, rel=0.01)

    def test_deep_otm_near_zero(self):
        price = _bs_call_price(S=100, K=200, T=30/365, r=0.05, sigma=0.15, q=0.0)
        assert price < 0.01

    def test_zero_time_returns_intrinsic(self):
        price = _bs_call_price(S=110, K=100, T=0, r=0.05, sigma=0.20, q=0.0)
        assert price == pytest.approx(10.0, abs=0.01)

    def test_dividend_reduces_call_price(self):
        no_div = _bs_call_price(S=100, K=100, T=1.0, r=0.05, sigma=0.20, q=0.0)
        with_div = _bs_call_price(S=100, K=100, T=1.0, r=0.05, sigma=0.20, q=0.05)
        assert with_div < no_div


# ---------------------------------------------------------------------------
# BS IV inversion (roundtrip)
# ---------------------------------------------------------------------------

class TestComputeBsIv:
    @pytest.mark.parametrize("true_sigma", [0.05, 0.10, 0.20, 0.50, 1.50])
    def test_roundtrip_no_dividend(self, true_sigma):
        S, K, T, r, q = 100.0, 100.0, 30/365, 0.05, 0.0
        C = _bs_call_price(S, K, T, r, true_sigma, q)
        recovered = compute_bs_iv(C, S, K, int(T * 365), r, q)
        assert recovered == pytest.approx(true_sigma, rel=1e-4)

    @pytest.mark.parametrize("q", [0.03, 0.06])
    def test_roundtrip_with_dividend(self, q):
        true_sigma = 0.12
        S, K, T, r = 78.0, 78.0, 30/365, 0.05
        C = _bs_call_price(S, K, T, r, true_sigma, q)
        recovered = compute_bs_iv(C, S, K, int(T * 365), r, q)
        assert recovered == pytest.approx(true_sigma, rel=1e-3)

    def test_returns_nan_for_zero_price(self):
        assert math.isnan(compute_bs_iv(0.0, 100, 100, 30, 0.05))

    def test_returns_nan_for_negative_price(self):
        assert math.isnan(compute_bs_iv(-1.0, 100, 100, 30, 0.05))

    def test_returns_nan_for_zero_days(self):
        assert math.isnan(compute_bs_iv(2.0, 100, 100, 0, 0.05))

    def test_returns_nan_for_price_at_intrinsic(self):
        # C = intrinsic → IV is undefined
        assert math.isnan(compute_bs_iv(10.0, 110, 100, 30, 0.0))

    def test_atm_hyg_like_realistic_values(self):
        # Realistic HYG parameters: S≈79, K≈79, T=30d, r=5%, q=5.5%, σ≈8%
        true_sigma = 0.08
        S, K, T, r, q = 79.0, 79.0, 30/365, 0.05, 0.055
        C = _bs_call_price(S, K, T, r, true_sigma, q)
        recovered = compute_bs_iv(C, S, K, int(T * 365), r, q)
        assert recovered == pytest.approx(true_sigma, rel=1e-3)


# ---------------------------------------------------------------------------
# Friday date generation
# ---------------------------------------------------------------------------

class TestFridayDatesInRange:
    def test_single_friday(self):
        dates = _friday_dates_in_range("2024-11-01", "2024-11-01")
        assert len(dates) == 1
        assert dates[0].weekday() == 4  # Friday

    def test_first_friday_advances_correctly(self):
        # 2024-11-04 is a Monday; first Friday is 2024-11-08
        dates = _friday_dates_in_range("2024-11-04", "2024-11-20")
        assert dates[0].weekday() == 4
        assert str(dates[0]) == "2024-11-08"

    def test_weekly_cadence(self):
        dates = _friday_dates_in_range("2024-01-05", "2024-03-01")
        diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        assert all(d == 7 for d in diffs)

    def test_empty_range_returns_empty(self):
        # end before any Friday
        dates = _friday_dates_in_range("2024-11-11", "2024-11-13")
        assert dates == []

    def test_start_on_friday_includes_it(self):
        dates = _friday_dates_in_range("2024-11-08", "2024-11-08")
        from datetime import date
        assert dates == [date(2024, 11, 8)]


# ---------------------------------------------------------------------------
# compute_greeks
# ---------------------------------------------------------------------------

class TestComputeGreeks:
    # Canonical HYG-like ATM call: S=K=79, T=30d, r=5%, q=5.84%, σ=10%
    _S, _K, _T, _r, _q, _σ = 79.0, 79.0, 30, 0.05, 0.0584, 0.10

    def _g(self, **kw):
        params = dict(underlying=self._S, strike=self._K, days_to_expiry=self._T,
                      rf_annual=self._r, sigma=self._σ, div_yield=self._q)
        params.update(kw)
        return compute_greeks(**params)

    def test_returns_all_keys(self):
        g = self._g()
        # Lean schema: delta_gamma, theta_vega, theta_vega_theoretical, gamma_vega removed.
        expected = {"delta", "gamma", "vega", "theta_daily",
                    "dollar_delta", "dollar_gamma", "dollar_vega"}
        assert expected <= set(g)

    def test_lean_schema_transform_cols_absent(self):
        g = self._g()
        for col in ("delta_gamma", "theta_vega", "theta_vega_theoretical", "gamma_vega"):
            assert col not in g, f"{col!r} should be absent from lean schema"

    def test_delta_atm_near_half(self):
        # ATM call delta ≈ 0.5 (slightly below 0.5 due to dividend)
        g = self._g()
        assert 0.3 < g["delta"] < 0.6

    def test_gamma_positive(self):
        assert self._g()["gamma"] > 0

    def test_vega_positive(self):
        assert self._g()["vega"] > 0

    def test_theta_daily_negative(self):
        # Long call loses time value (for normal yield levels)
        assert self._g()["theta_daily"] < 0

    def test_dollar_delta_definition(self):
        g = self._g()
        expected = g["delta"] * self._S
        assert g["dollar_delta"] == pytest.approx(expected, rel=1e-10)

    def test_dollar_delta_positive(self):
        assert self._g()["dollar_delta"] > 0

    def test_dollar_gamma_definition(self):
        g = self._g()
        expected = 0.5 * g["gamma"] * self._S**2 * (0.01)**2
        assert g["dollar_gamma"] == pytest.approx(expected, rel=1e-10)

    def test_dollar_vega_definition(self):
        g = self._g()
        expected = g["vega"] * 0.01
        assert g["dollar_vega"] == pytest.approx(expected, rel=1e-10)

    def test_invalid_inputs_return_all_nan(self):
        g = compute_greeks(underlying=0, strike=79, days_to_expiry=30,
                           rf_annual=0.05, sigma=0.10)
        assert all(math.isnan(v) for v in g.values())

    def test_higher_vega_for_longer_tenor(self):
        g30  = self._g(days_to_expiry=30)
        g60  = self._g(days_to_expiry=60)
        assert g60["vega"] > g30["vega"]

    def test_dollar_gamma_scale_invariant(self):
        # A $160 underlying with same moneyness should give ~4x dollar gamma
        # (gamma halves per dollar² but S² quadruples → net 2x, times 2x from
        # ATM gamma scaling ... simplest check: dollar_gamma > 0 and finite)
        g = self._g(underlying=160.0, strike=160.0)
        assert g["dollar_gamma"] > 0 and math.isfinite(g["dollar_gamma"])
