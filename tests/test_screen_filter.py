"""Known-value tests for the new tradeability + economic-significance filter in screen_chain.

Tests that:
  - wide-spread contracts are excluded
  - out-of-moneyness-band contracts are excluded
  - contracts passing all criteria are included
  - transform columns (delta_gamma, theta_vega, theta_vega_theoretical, gamma_vega)
    are absent from the passing output when using the lean schema
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.data.options import screen_chain


def _base_contract(**overrides) -> dict:
    """A contract that passes all default filter criteria."""
    row = {
        "ticker":       "TLT",
        "snap_date":    pd.Timestamp("2024-01-05"),
        "right":        "C",
        "expiry":       "2024-02-02",
        "strike":       90.0,
        "dte":          28,          # in [14, 90]
        "underlying":   100.0,
        "bid":          1.90,
        "ask":          2.10,        # rel_spread = 0.20/2.00 = 0.10 ≤ 0.25
        "close":        2.00,
        "option_price": 2.00,
        "price_type":   "mid",
        "iv":           0.15,
        "delta":        0.50,        # abs(delta) in [0.10, 0.90]
        "gamma":        0.02,
        "vega":         5.0,
        "theta_daily":  -0.03,
        "dollar_delta": 50.0,        # ≥ 5.0
        "dollar_gamma": 0.002,       # ≥ 0.001
        "dollar_vega":  0.05,        # ≥ 0.01
    }
    row.update(overrides)
    return row


def _df(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


# ---------------------------------------------------------------------------
# Wide-spread exclusion
# ---------------------------------------------------------------------------

class TestWideSpreadExclusion:
    def test_wide_spread_excluded(self):
        """rel_spread = (ask-bid)/mid = 0.60/1.50 = 0.40 > 0.25 → excluded."""
        c = _base_contract(bid=1.20, ask=1.80)  # mid=1.50, spread=0.60, rs=0.40
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_narrow_spread_included(self):
        c = _base_contract()  # rel_spread = 0.10 ≤ 0.25
        result = screen_chain(_df(c))
        assert len(result["passing"]) == 1

    def test_zero_bid_excluded(self):
        c = _base_contract(bid=0.0)
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_zero_ask_excluded(self):
        c = _base_contract(ask=0.0)
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_exact_spread_threshold_passes(self):
        """rel_spread exactly 0.25 → passes (≤ threshold)."""
        c = _base_contract(bid=0.75, ask=1.25)  # mid=1.0, spread=0.50, rs=0.50 → fail
        # Make it exactly 0.25: bid=0.875, ask=1.125, mid=1.0
        c = _base_contract(bid=0.875, ask=1.125)  # rs = 0.25/1.0 = 0.25 → pass
        result = screen_chain(_df(c), max_rel_spread=0.25)
        assert len(result["passing"]) == 1


# ---------------------------------------------------------------------------
# Moneyness-band exclusion
# ---------------------------------------------------------------------------

class TestMoneynessExclusion:
    def test_deep_otm_excluded(self):
        """abs(delta) = 0.05 < 0.10 → excluded."""
        c = _base_contract(delta=0.05, dollar_delta=5.0)
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_deep_itm_excluded(self):
        """abs(delta) = 0.95 > 0.90 → excluded."""
        c = _base_contract(delta=0.95, dollar_delta=95.0)
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_put_deep_itm_excluded(self):
        """Put delta = -0.95 → abs(delta) = 0.95 > 0.90 → excluded."""
        c = _base_contract(delta=-0.95, right="P", dollar_delta=-95.0)
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_mid_band_call_passes(self):
        c = _base_contract(delta=0.50)
        result = screen_chain(_df(c))
        assert len(result["passing"]) == 1

    def test_mid_band_put_passes(self):
        c = _base_contract(delta=-0.50, right="P", dollar_delta=-50.0)
        result = screen_chain(_df(c))
        assert len(result["passing"]) == 1


# ---------------------------------------------------------------------------
# Dollar-threshold exclusions
# ---------------------------------------------------------------------------

class TestDollarThresholds:
    def test_low_dollar_delta_excluded(self):
        """dollar_delta = 3.0 < 5.0 → excluded."""
        c = _base_contract(dollar_delta=3.0)
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_low_dollar_gamma_excluded(self):
        c = _base_contract(dollar_gamma=0.0005)
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_low_dollar_vega_excluded(self):
        c = _base_contract(dollar_vega=0.005)
        result = screen_chain(_df(c))
        assert result["passing"].empty


# ---------------------------------------------------------------------------
# DTE exclusions
# ---------------------------------------------------------------------------

class TestDteExclusion:
    def test_dte_below_min_excluded(self):
        c = _base_contract(dte=7)
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_dte_above_max_excluded(self):
        c = _base_contract(dte=91)
        result = screen_chain(_df(c))
        assert result["passing"].empty

    def test_dte_at_min_passes(self):
        c = _base_contract(dte=14)
        result = screen_chain(_df(c))
        assert len(result["passing"]) == 1

    def test_dte_at_max_passes(self):
        c = _base_contract(dte=90)
        result = screen_chain(_df(c))
        assert len(result["passing"]) == 1


# ---------------------------------------------------------------------------
# Lean-schema: transform columns absent
# ---------------------------------------------------------------------------

class TestLeanSchema:
    OLD_TRANSFORM_COLS = [
        "delta_gamma",
        "theta_vega",
        "theta_vega_theoretical",
        "gamma_vega",
    ]

    def test_transform_cols_absent_from_quality_output_when_not_in_input(self):
        """When the input has only lean-schema columns, passing output has none of the
        old transform columns."""
        c = _base_contract()
        result = screen_chain(_df(c))
        for col in self.OLD_TRANSFORM_COLS:
            assert col not in result["passing"].columns, f"{col!r} found in passing output"

    def test_transform_cols_pass_through_if_present(self):
        """If the input happens to include old columns they are NOT stripped (pass-through).
        This ensures backward compat with old chain CSVs during the transition."""
        c = _base_contract()
        c["theta_vega"] = 0.05
        result = screen_chain(_df(c))
        # theta_vega is in the input and should be in passing (just not used by the filter)
        if len(result["passing"]) > 0:
            assert "theta_vega" in result["passing"].columns


# ---------------------------------------------------------------------------
# quality column
# ---------------------------------------------------------------------------

def test_quality_column_is_bool_true_for_all_passing():
    c = _base_contract()
    result = screen_chain(_df(c))
    assert result["passing"]["quality"].dtype == bool
    assert result["passing"]["quality"].all()
