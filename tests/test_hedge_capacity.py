"""Known-value tests for src.features.hedge_capacity.

Pin the core math:
  rate_dv01  = D_i * S * |delta| * 1e-4 * 100
  fund_dv01  = D_i * AUM * 1e-4
  ratio      = chain_rate_dv01 / fund_dv01

Reduced-identity cross-check (D_i cancels in the ratio):
  ratio = (100 * S * Σ[|delta| * w]) / AUM

Both must give the same answer.
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from src.features.hedge_capacity import compute_chain_capacity
from src.features.rate_space import add_rate_space_greeks

# Canonical test parameters
_D_I   = 10.0
_S     = 100.0
_AUM   = 1_000_000_000.0   # 1 billion
_DELTA = 0.5
_OI    = 1.0

_METADATA = {
    "TLT": {"aum": _AUM, "eff_duration": _D_I, "eff_convexity": None, "expense_ratio": 0.0015},
}
_DURATION_MAP = {"TLT": _D_I}


def _make_quality_contract(
    *,
    ticker: str = "TLT",
    snap_date: str = "2024-01-05",
    right: str = "C",
    delta: float = _DELTA,
    gamma: float = 0.01,
    theta_daily: float = -0.05,
    underlying: float = _S,
    open_interest: float | None = None,
    quality: bool = True,
) -> pd.DataFrame:
    row: dict = {
        "ticker":      ticker,
        "snap_date":   pd.Timestamp(snap_date),
        "right":       right,
        "delta":       delta,
        "gamma":       gamma,
        "theta_daily": theta_daily,
        "underlying":  underlying,
        "quality":     quality,
    }
    if open_interest is not None:
        row["open_interest"] = open_interest
    return pd.DataFrame([row])


def _with_rate_greeks(df: pd.DataFrame, duration_map: dict) -> pd.DataFrame:
    return add_rate_space_greeks(df, duration_map)


# ---------------------------------------------------------------------------
# Capacity ratio known-value (unweighted, w=1)
# ---------------------------------------------------------------------------

class TestCapacityRatioUnweighted:
    """One put contract, no OI column (unweighted), S=100, delta=0.5, D_i=10, AUM=1e9."""

    def setup_method(self):
        raw = _make_quality_contract(right="P", delta=-_DELTA)
        self.df = _with_rate_greeks(raw, _DURATION_MAP)

    def test_ratio_unweighted_known_value(self):
        """ratio = rate_dv01 / fund_dv01 = 5.0 / 1e6 = 5e-6"""
        out = compute_chain_capacity(self.df, _METADATA, _DURATION_MAP, min_quality_contracts=1)
        put_row = out[out["side"] == "put"].iloc[0]
        assert put_row["hedge_capacity_ratio"] == pytest.approx(5e-6, rel=1e-9)

    def test_reduced_identity_cross_check(self):
        """(100 * S * sum[|delta|*w]) / AUM = (100 * 100 * 0.5 * 1) / 1e9 = 5e-6."""
        out = compute_chain_capacity(self.df, _METADATA, _DURATION_MAP, min_quality_contracts=1)
        put_row = out[out["side"] == "put"].iloc[0]
        reduced = (100.0 * _S * abs(_DELTA) * 1.0) / _AUM
        assert put_row["hedge_capacity_ratio"] == pytest.approx(reduced, rel=1e-9)

    def test_weight_basis_unweighted(self):
        out = compute_chain_capacity(self.df, _METADATA, _DURATION_MAP, min_quality_contracts=1)
        assert (out["weight_basis"] == "unweighted").all()


# ---------------------------------------------------------------------------
# OI-weighted capacity ratio
# ---------------------------------------------------------------------------

class TestCapacityRatioOiWeighted:
    def test_ratio_oi_weighted(self):
        """OI=2 → chain_dv01 = 2 * 5.0 = 10.0; ratio = 10.0 / 1e6 = 1e-5."""
        raw = _make_quality_contract(right="P", delta=-_DELTA, open_interest=2.0)
        df  = _with_rate_greeks(raw, _DURATION_MAP)
        out = compute_chain_capacity(df, _METADATA, _DURATION_MAP, min_quality_contracts=1)
        put_row = out[out["side"] == "put"].iloc[0]
        assert put_row["hedge_capacity_ratio"] == pytest.approx(1e-5, rel=1e-9)

    def test_weight_basis_oi_when_column_present(self):
        raw = _make_quality_contract(right="C", delta=_DELTA, open_interest=1.0)
        df  = _with_rate_greeks(raw, _DURATION_MAP)
        out = compute_chain_capacity(df, _METADATA, _DURATION_MAP, min_quality_contracts=1)
        assert (out["weight_basis"] == "open_interest").all()


# ---------------------------------------------------------------------------
# Side separation: put does not leak into call capacity
# ---------------------------------------------------------------------------

class TestSideSeparation:
    def test_put_not_in_call_capacity(self):
        raw = _make_quality_contract(right="P", delta=-_DELTA)
        df  = _with_rate_greeks(raw, _DURATION_MAP)
        out = compute_chain_capacity(df, _METADATA, _DURATION_MAP, min_quality_contracts=1)
        assert "call" not in out["side"].values

    def test_call_not_in_put_capacity(self):
        raw = _make_quality_contract(right="C", delta=_DELTA)
        df  = _with_rate_greeks(raw, _DURATION_MAP)
        out = compute_chain_capacity(df, _METADATA, _DURATION_MAP, min_quality_contracts=1)
        assert "put" not in out["side"].values

    def test_total_equals_put_plus_call(self):
        raw = pd.concat([
            _make_quality_contract(right="C", delta=_DELTA),
            _make_quality_contract(right="P", delta=-_DELTA),
        ], ignore_index=True)
        df  = _with_rate_greeks(raw, _DURATION_MAP)
        out = compute_chain_capacity(df, _METADATA, _DURATION_MAP, min_quality_contracts=1)

        total_row = out[out["side"] == "total"].iloc[0]
        put_row   = out[out["side"] == "put"].iloc[0]
        call_row  = out[out["side"] == "call"].iloc[0]

        assert total_row["chain_rate_dv01"] == pytest.approx(
            put_row["chain_rate_dv01"] + call_row["chain_rate_dv01"], rel=1e-9
        )
        assert total_row["hedge_capacity_ratio"] == pytest.approx(
            put_row["hedge_capacity_ratio"] + call_row["hedge_capacity_ratio"], rel=1e-9
        )


# ---------------------------------------------------------------------------
# Quality gate exclusion
# ---------------------------------------------------------------------------

class TestQualityGate:
    def test_non_quality_contracts_excluded(self):
        raw = _make_quality_contract(quality=False)
        df  = _with_rate_greeks(raw, _DURATION_MAP)
        out = compute_chain_capacity(df, _METADATA, _DURATION_MAP, min_quality_contracts=1)
        assert len(out) == 0

    def test_min_quality_contracts_enforced(self):
        """With min_quality_contracts=2 and only 1 quality contract, all sides are skipped."""
        raw = _make_quality_contract(right="C", delta=_DELTA)
        df  = _with_rate_greeks(raw, _DURATION_MAP)
        out = compute_chain_capacity(df, _METADATA, _DURATION_MAP, min_quality_contracts=2)
        # call side has only 1 contract → both call and total rows skipped → empty output
        assert len(out) == 0

    def test_missing_aum_ticker_excluded(self):
        raw = _make_quality_contract(ticker="UNKNOWN", delta=_DELTA)
        df  = _with_rate_greeks(raw, {"UNKNOWN": 5.0})
        out = compute_chain_capacity(df, {}, {"UNKNOWN": 5.0}, min_quality_contracts=1)
        assert len(out) == 0

    def test_nan_duration_preserves_reduced_capacity_ratio(self):
        raw = _make_quality_contract()
        df  = _with_rate_greeks(raw, {"TLT": float("nan")})
        out = compute_chain_capacity(df, _METADATA, {"TLT": float("nan")}, min_quality_contracts=1)
        total = out[out["side"] == "total"].iloc[0]
        assert total["hedge_capacity_ratio"] == pytest.approx(5e-6)
        assert math.isnan(total["chain_rate_dv01"])
        assert math.isnan(total["fund_dv01"])
        assert math.isnan(total["convexity_capacity_ratio"])

    def test_snapshot_duration_column_takes_precedence(self):
        raw = _make_quality_contract()
        raw["D_i"] = 5.0
        df = _with_rate_greeks(raw, {"TLT": 99.0})
        out = compute_chain_capacity(
            df, _METADATA, {"TLT": 99.0}, min_quality_contracts=1
        )
        total = out[out["side"] == "total"].iloc[0]
        assert total["fund_dv01"] == pytest.approx(5.0 * _AUM * 1e-4)
