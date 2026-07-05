import numpy as np
import pandas as pd

from src.analysis.regression_utils import cgm_summary


def test_cgm_summary_aligns_clusters_after_missing_regressor_rows():
    rng = np.random.default_rng(7)
    rows = []
    for ticker in ["A", "B", "C", "D"]:
        for date_idx in range(8):
            rows.append(
                {
                    "ticker": ticker,
                    "date": f"2024-{date_idx + 1:02d}-01",
                    "x": rng.normal(),
                    "y": rng.normal(),
                }
            )
    data = pd.DataFrame(rows)
    data.loc[[1, 9, 17], "x"] = np.nan

    result = cgm_summary("y ~ x", data, ["x"])

    assert list(result.index) == ["x"]
    assert np.isfinite(result.loc["x", "coef"])
    assert np.isfinite(result.loc["x", "se_cgm"])
