"""Tests for src.data.options — chain filtering and summary logic."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.data.options import screen_chain


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chain(
    n: int = 10,
    ticker: str = "HYG",
    snap: str = "2024-01-05",
    all_pass: bool = False,
) -> pd.DataFrame:
    """Synthetic chain DataFrame compatible with the new tradeability filter.

    All contracts have valid bid/ask/mid with rel_spread ≈ 0.05 (narrow),
    dte=28 (in [14,90]), delta in (0.1, 0.9), and reasonable dollar Greeks.
    Pass ``all_pass=False`` (default) for a normal mix; the relaxed-thresholds
    tests explicitly set thresholds to 0/inf to force all-pass/all-fail.
    """
    rng = np.random.default_rng(42)
    underlying = 79.0
    mid_prices = rng.uniform(0.50, 5.0, n)
    half_spread = mid_prices * 0.025   # 5% rel spread → passes 0.25 threshold
    bid = mid_prices - half_spread
    ask = mid_prices + half_spread

    return pd.DataFrame({
        "ticker":       ticker,
        "snap_date":    pd.Timestamp(snap),
        "right":        "C",
        "expiry":       date(2024, 2, 2),
        "strike":       np.linspace(70, 90, n),
        "dte":          28,
        "underlying":   underlying,
        "bid":          bid,
        "ask":          ask,
        "close":        mid_prices,
        "option_price": mid_prices,
        "price_type":   "mid",
        "iv":           rng.uniform(0.05, 0.25, n),
        "delta":        rng.uniform(0.10, 0.90, n),
        "gamma":        rng.uniform(0.005, 0.05, n),
        "vega":         rng.uniform(3.0, 12.0, n),
        "theta_daily":  rng.uniform(-0.08, -0.01, n),
        "dollar_delta": rng.uniform(8.0, 70.0, n),
        "dollar_gamma": rng.uniform(0.002, 0.02, n),
        "dollar_vega":  rng.uniform(0.02, 0.15, n),
    })


# ---------------------------------------------------------------------------
# screen_chain
# ---------------------------------------------------------------------------

class TestScreenChain:
    def test_empty_input_returns_empty(self):
        result = screen_chain(pd.DataFrame())
        assert result["passing"].empty
        assert result["summary"].empty

    def test_all_pass_with_relaxed_thresholds(self):
        chain = _make_chain(10)
        result = screen_chain(
            chain,
            max_rel_spread=999.0,
            delta_lo=0.0,
            delta_hi=1.0,
            min_dollar_delta=0.0,
            min_dollar_gamma=0.0,
            min_dollar_vega=0.0,
        )
        assert len(result["passing"]) == 10

    def test_all_fail_with_strict_dollar_delta(self):
        chain = _make_chain(10)
        result = screen_chain(chain, min_dollar_delta=9999.0)
        assert result["passing"].empty

    def test_all_fail_with_zero_spread_threshold(self):
        chain = _make_chain(10)
        result = screen_chain(chain, max_rel_spread=0.0)
        assert result["passing"].empty

    def test_dollar_vega_filter(self):
        chain = _make_chain(10)
        threshold = chain["dollar_vega"].median()
        result = screen_chain(
            chain,
            min_dollar_vega=threshold,
            max_rel_spread=999.0,
            delta_lo=0.0,
            delta_hi=1.0,
            min_dollar_delta=0.0,
            min_dollar_gamma=0.0,
        )
        assert (result["passing"]["dollar_vega"] >= threshold).all()

    def test_dollar_gamma_filter(self):
        chain = _make_chain(10)
        threshold = chain["dollar_gamma"].median()
        result = screen_chain(
            chain,
            min_dollar_gamma=threshold,
            max_rel_spread=999.0,
            delta_lo=0.0,
            delta_hi=1.0,
            min_dollar_delta=0.0,
            min_dollar_vega=0.0,
        )
        assert (result["passing"]["dollar_gamma"] >= threshold).all()

    def test_summary_has_one_row_per_ticker_date(self):
        hyg = _make_chain(6, ticker="HYG", snap="2024-01-05")
        lqd = _make_chain(6, ticker="LQD", snap="2024-01-05")
        chain = pd.concat([hyg, lqd], ignore_index=True)
        result = screen_chain(
            chain,
            max_rel_spread=999.0,
            delta_lo=0.0,
            delta_hi=1.0,
            min_dollar_delta=0.0,
            min_dollar_gamma=0.0,
            min_dollar_vega=0.0,
        )
        assert len(result["summary"]) == 2
        assert set(result["summary"]["ticker"]) == {"HYG", "LQD"}

    def test_pass_rate_between_0_and_1(self):
        chain = _make_chain(10)
        result = screen_chain(chain)
        assert (result["summary"]["pass_rate"].between(0, 1)).all()

    def test_pass_rate_consistent_with_passing_count(self):
        chain = _make_chain(10)
        result = screen_chain(chain)
        row = result["summary"].iloc[0]
        expected = row["passing_contracts"] / row["total_contracts"]
        assert row["pass_rate"] == pytest.approx(expected, rel=1e-6)

    def test_summary_contains_median_greeks(self):
        chain = _make_chain(10)
        result = screen_chain(
            chain,
            max_rel_spread=999.0,
            delta_lo=0.0,
            delta_hi=1.0,
            min_dollar_delta=0.0,
            min_dollar_gamma=0.0,
            min_dollar_vega=0.0,
        )
        for col in ["median_dollar_vega", "median_dollar_gamma", "median_iv"]:
            assert col in result["summary"].columns

    def test_two_dates_same_ticker_two_summary_rows(self):
        d1 = _make_chain(5, snap="2024-01-05")
        d2 = _make_chain(5, snap="2024-02-02")
        chain = pd.concat([d1, d2], ignore_index=True)
        result = screen_chain(
            chain,
            max_rel_spread=999.0,
            delta_lo=0.0,
            delta_hi=1.0,
            min_dollar_delta=0.0,
            min_dollar_gamma=0.0,
            min_dollar_vega=0.0,
        )
        assert len(result["summary"]) == 2

    def test_quality_column_added_to_passing(self):
        chain = _make_chain(10)
        result = screen_chain(chain)
        assert "quality" in result["passing"].columns
        assert result["passing"]["quality"].all()

    def test_no_bid_ask_contracts_excluded(self):
        chain = _make_chain(5)
        chain.loc[0, "bid"] = 0.0
        chain.loc[0, "ask"] = 0.0
        result = screen_chain(
            chain,
            max_rel_spread=999.0,
            delta_lo=0.0,
            delta_hi=1.0,
            min_dollar_delta=0.0,
            min_dollar_gamma=0.0,
            min_dollar_vega=0.0,
        )
        assert len(result["passing"]) == 4
