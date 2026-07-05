import math

import pandas as pd
import pytest

from src.features.call_put_iv import build_call_put_iv_diagnostic


def _row(expiry, strike, right, iv, bid=1.0, ask=1.1):
    snap = pd.Timestamp("2024-01-02")
    expiry = pd.Timestamp(expiry)
    return {
        "ticker": "TLT",
        "snap_date": snap,
        "expiry": expiry,
        "strike": strike,
        "right": right,
        "dte": (expiry - snap).days,
        "underlying": 100.0,
        "bid": bid,
        "ask": ask,
        "iv": iv,
    }


def test_prefers_paired_atm_strike_and_combines_sides():
    chains = pd.DataFrame(
        [
            _row("2024-02-02", 100.0, "C", 0.20),
            _row("2024-02-02", 100.0, "P", 0.24),
            _row("2024-02-02", 99.0, "C", 0.19),
            _row("2024-03-01", 100.0, "C", 0.30),
            _row("2024-03-01", 100.0, "P", 0.32),
        ]
    )

    result = build_call_put_iv_diagnostic(chains).iloc[0]

    assert result["strike"] == 100.0
    assert result["days_to_expiry"] == 31
    assert result["call_iv"] == pytest.approx(0.20)
    assert result["put_iv"] == pytest.approx(0.24)
    assert result["iv_30d_cp"] == pytest.approx(0.22)
    assert result["call_put_iv_gap"] == pytest.approx(0.04)
    assert result["iv_source"] == "call_put_median"


def test_rejects_wide_side_and_falls_back_to_call():
    chains = pd.DataFrame(
        [
            _row("2024-02-02", 100.0, "C", 0.20),
            _row("2024-02-02", 100.0, "P", 0.50, bid=0.1, ask=1.0),
        ]
    )

    result = build_call_put_iv_diagnostic(chains).iloc[0]

    assert result["iv_side_count"] == 1
    assert result["iv_30d_cp"] == pytest.approx(0.20)
    assert math.isnan(result["put_iv"])
    assert result["iv_source"] == "call_only"


def test_requires_expected_chain_columns():
    with pytest.raises(KeyError, match="chains_df missing columns"):
        build_call_put_iv_diagnostic(pd.DataFrame({"ticker": ["TLT"]}))
