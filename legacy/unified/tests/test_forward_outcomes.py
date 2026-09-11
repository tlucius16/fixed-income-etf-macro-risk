"""Legacy forward labels are not hedge-design scenario inputs."""
import numpy as np
import pandas as pd

from legacy.unified.src.features.forward_outcomes import add_forward_outcomes


def test_forward_outcomes_use_future_returns_only():
    panel = pd.DataFrame({
        "Symbol": ["AAA"] * 6,
        "Date": pd.date_range("2024-01-05", periods=6, freq="W-FRI"),
        "Return": [0.01, 0.02, -0.01, 0.03, 0.04, -0.02],
    })
    out = add_forward_outcomes(panel, fwd_short=2, fwd_long=3, min_periods_long=3)
    assert np.isclose(out.loc[0, "fwd_ret_4w"], (1 + 0.02) * (1 - 0.01) - 1)
    assert np.isclose(out.loc[1, "fwd_ret_4w"], (1 - 0.01) * (1 + 0.03) - 1)
    assert pd.isna(out.loc[4, "fwd_ret_4w"])
    assert pd.isna(out.loc[5, "fwd_ret_4w"])
