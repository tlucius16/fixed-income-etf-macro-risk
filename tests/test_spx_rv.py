"""Tests for S&P realized vol construction and the 5-component stress index."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.stress_index import _COMPONENTS, add_stress_index


def test_stress_components_include_spx_rv_and_dxy():
    assert _COMPONENTS == ["d_ANFCI", "d_BAMLC0A0CM", "d_MOVE", "d_VIX",
                           "d_SPX_RV_21d", "d_DXY", "d_KCPRU"]


def test_stress_index_is_mean_of_component_zscores():
    rng = np.random.default_rng(7)
    n = 120
    dates = pd.date_range("2020-01-03", periods=n, freq="W-FRI")
    panel = pd.DataFrame({"Date": dates})
    for c in _COMPONENTS:
        panel[c] = rng.normal(size=n)
    out = add_stress_index(panel)

    z = (panel[_COMPONENTS] - panel[_COMPONENTS].mean()) / panel[_COMPONENTS].std(ddof=1)
    expected = z.mean(axis=1)
    pd.testing.assert_series_equal(
        out["stress_index"], expected.rename("stress_index"), rtol=1e-12
    )
    assert set(out["high_stress"].unique()) <= {0, 1}
    assert (out["high_stress"] == (out["stress_index"] > 1.0).astype(int)).all()


def test_spx_rv_from_cached_closes_annualization():
    """RV builder on a synthetic constant-vol price path recovers sigma."""
    from src.data.macro import build_spx_realized_vol

    rng = np.random.default_rng(42)
    sigma_daily = 0.01                        # 1% daily → ~15.87% annualized
    n = 800
    dates = pd.bdate_range("2020-01-02", periods=n)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, sigma_daily, n)))

    cache = None
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        cache = pathlib.Path(td) / "spx.csv"
        pd.DataFrame({"Date": dates, "Close": prices}).to_csv(cache, index=False)
        out = build_spx_realized_vol(cache_csv=cache)

    assert {"SPX_RV_21d", "SPX_RV_12w", "d_SPX_RV_21d", "d_SPX_RV_12w"} <= set(out.columns)
    ann = sigma_daily * np.sqrt(252)
    med = out["SPX_RV_21d"].median()
    assert med == pytest.approx(ann, rel=0.15)   # noisy estimator, generous band
    # weekly convention roughly agrees with daily convention on iid data
    assert out["SPX_RV_12w"].median() == pytest.approx(ann, rel=0.35)
    # no NaN after warmup dropna
    assert out["d_SPX_RV_21d"].notna().all()
