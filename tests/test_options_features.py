"""Tests for src.features.options_features."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.features.options_features import (
    compute_vrp, compute_hedgeability_score, _ANNUALISE_FACTOR,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _iv_panel(
    n: int = 20,
    iv: float = 0.15,
    rvol: float = 0.10,
    fwd_vol_12w: float | None = None,
) -> pd.DataFrame:
    dates = pd.date_range("2022-01-07", periods=n, freq="W-FRI")
    df = pd.DataFrame({
        "date":               dates,
        "ticker":             "TLT",
        "iv_30d":             np.full(n, iv),
        "vol_12w_annualized": np.full(n, rvol),
    })
    if fwd_vol_12w is not None:
        df["fwd_vol_12w"] = fwd_vol_12w
    return df


def _ticker_summary(tickers: list[str], pass_rates: list[float]) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = len(tickers)
    return pd.DataFrame({
        "ticker":              tickers,
        "mean_pass_rate":      pass_rates,
        "median_dollar_vega":  rng.uniform(0.01, 0.15, n),
        "median_dollar_gamma": rng.uniform(0.005, 0.05, n),
        "median_theta_vega":   rng.uniform(0.0005, 0.002, n),
        "liquid":              [True] * n,
    })


def _core_panel(tickers: list[str], drawdowns: list[float]) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2022-01-07", periods=10, freq="W-FRI")
    for ticker, dd in zip(tickers, drawdowns):
        for d in dates:
            rows.append({"Date": d, "Symbol": ticker, "fwd_maxdd_12w": dd})
    return pd.DataFrame(rows)


# ── compute_vrp ───────────────────────────────────────────────────────────────

class TestComputeVrp:
    def test_vrp_value(self):
        df = _iv_panel(iv=0.20, rvol=0.10)
        out = compute_vrp(df)
        expected = 0.20 ** 2 - 0.10 ** 2
        np.testing.assert_allclose(out["vrp"].values, expected, rtol=1e-10)

    def test_vrp_positive_clips_negative(self):
        # rvol > iv → VRP is negative; vrp_positive should be 0
        df = _iv_panel(iv=0.05, rvol=0.20)
        out = compute_vrp(df)
        assert (out["vrp"] < 0).all()
        assert (out["vrp_positive"] == 0.0).all()

    def test_vrp_positive_preserves_positive(self):
        df = _iv_panel(iv=0.20, rvol=0.05)
        out = compute_vrp(df)
        pd.testing.assert_series_equal(
            out["vrp_positive"], out["vrp"], check_names=False
        )

    def test_rate_regime_tightening(self):
        # 2022-06-03 falls in tightening regime
        df = pd.DataFrame({
            "date":               [pd.Timestamp("2022-06-03")],
            "ticker":             ["TLT"],
            "iv_30d":             [0.15],
            "vol_12w_annualized": [0.10],
        })
        out = compute_vrp(df)
        assert out["rate_regime"].iloc[0] == "tightening"

    def test_rate_regime_easing(self):
        df = pd.DataFrame({
            "date":               [pd.Timestamp("2025-01-10")],
            "ticker":             ["TLT"],
            "iv_30d":             [0.12],
            "vol_12w_annualized": [0.08],
        })
        out = compute_vrp(df)
        assert out["rate_regime"].iloc[0] == "easing"

    def test_original_columns_preserved(self):
        df = _iv_panel()
        out = compute_vrp(df)
        assert {"iv_30d", "vol_12w_annualized", "ticker", "date"} <= set(out.columns)

    def test_no_mutation_of_input(self):
        df = _iv_panel()
        original_cols = set(df.columns)
        compute_vrp(df)
        assert set(df.columns) == original_cols

    def test_iv_realized_var_gap_equals_vrp_alias(self):
        df = _iv_panel(iv=0.20, rvol=0.10)
        out = compute_vrp(df)
        pd.testing.assert_series_equal(out["iv_realized_var_gap"], out["vrp"],
                                       check_names=False)

    def test_vrp_ex_post_absent_without_fwd_vol(self):
        df = _iv_panel()  # no fwd_vol_12w column
        out = compute_vrp(df)
        assert "vrp_ex_post_12w" not in out.columns
        assert "fwd_vol_12w_annualized" not in out.columns

    def test_vrp_ex_post_computed_when_fwd_vol_present(self):
        fwd_vol = 0.008  # weekly units
        df = _iv_panel(iv=0.15, rvol=0.10, fwd_vol_12w=fwd_vol)
        out = compute_vrp(df)
        assert "vrp_ex_post_12w" in out.columns
        assert "fwd_vol_12w_annualized" in out.columns
        expected_annualized = fwd_vol * _ANNUALISE_FACTOR
        np.testing.assert_allclose(out["fwd_vol_12w_annualized"].values,
                                   expected_annualized, rtol=1e-10)
        expected_ex_post = 0.15 ** 2 - expected_annualized ** 2
        np.testing.assert_allclose(out["vrp_ex_post_12w"].values,
                                   expected_ex_post, rtol=1e-10)


# ── compute_hedgeability_score ────────────────────────────────────────────────

class TestComputeHedgeabilityScore:
    @pytest.fixture
    def six_ticker_inputs(self):
        tickers = ["AGG", "TLT", "HYG", "IEF", "LQD", "BIL"]
        pass_rates = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
        ts = _ticker_summary(tickers, pass_rates)
        # More negative drawdown for later tickers (more fragile)
        drawdowns = [-0.01, -0.02, -0.03, -0.04, -0.05, -0.06]
        core = _core_panel(tickers, drawdowns)
        return ts, core

    def test_output_has_required_columns(self, six_ticker_inputs):
        ts, core = six_ticker_inputs
        out = compute_hedgeability_score(ts, core)
        required = {
            "ticker", "H", "hedgeability_tercile", "fragility_tercile",
            "fragility_hedgeability_group",
        }
        assert required <= set(out.columns)

    def test_row_count_equals_liquid_tickers(self, six_ticker_inputs):
        ts, core = six_ticker_inputs
        out = compute_hedgeability_score(ts, core)
        assert len(out) == 6

    def test_hedgeability_tercile_range(self, six_ticker_inputs):
        ts, core = six_ticker_inputs
        out = compute_hedgeability_score(ts, core)
        assert set(out["hedgeability_tercile"].unique()) <= {1, 2, 3}

    def test_fragility_tercile_range(self, six_ticker_inputs):
        ts, core = six_ticker_inputs
        out = compute_hedgeability_score(ts, core)
        assert set(out["fragility_tercile"].unique()) <= {1, 2, 3}

    def test_group_label_format(self, six_ticker_inputs):
        ts, core = six_ticker_inputs
        out = compute_hedgeability_score(ts, core)
        for g in out["fragility_hedgeability_group"]:
            assert g.startswith("F") and "_H" in g

    def test_h_score_monotone_with_pass_rate_when_other_metrics_equal(self):
        # When dollar_vega and dollar_gamma are identical across tickers,
        # H should rank purely by pass_rate.
        tickers = ["A", "B", "C", "D"]
        pass_rates = [0.9, 0.7, 0.5, 0.3]
        ts = pd.DataFrame({
            "ticker":              tickers,
            "mean_pass_rate":      pass_rates,
            "median_dollar_vega":  [0.05] * 4,
            "median_dollar_gamma": [0.02] * 4,
            "median_theta_vega":   [0.001] * 4,
            "liquid":              [True] * 4,
        })
        core = _core_panel(tickers, [-0.01, -0.02, -0.03, -0.04])
        out = compute_hedgeability_score(ts, core).sort_values("H", ascending=False)
        assert out["ticker"].iloc[0] == "A"
        assert out["ticker"].iloc[-1] == "D"

    def test_illiquid_tickers_excluded(self, six_ticker_inputs):
        ts, core = six_ticker_inputs
        # mark last ticker as illiquid
        ts = ts.copy()
        ts.loc[ts["ticker"] == "BIL", "liquid"] = False
        out = compute_hedgeability_score(ts, core)
        assert "BIL" not in out["ticker"].values
        assert len(out) == 5
