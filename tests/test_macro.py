from __future__ import annotations

import numpy as np
import pandas as pd

from src.data import macro


def test_hybrid_baml_keeps_legacy_history_and_prefers_live_overlap(tmp_path, monkeypatch):
    legacy_path = tmp_path / "baml_w.csv"
    pd.DataFrame(
        {
            "Date": pd.to_datetime(["2020-01-03", "2020-01-10", "2020-01-17"]),
            "BAML_C0A0CM": [1.0, 1.1, 1.2],
            "d_BAML_C0A0CM": [pd.NA, 0.1, 0.1],
        }
    ).to_csv(legacy_path, index=False)

    live = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2020-01-10", "2020-01-24"]),
            "BAMLC0A0CM": [2.1, 2.4],
        }
    )
    monkeypatch.setattr(macro, "pull_fred_weekly_series", lambda *args, **kwargs: live)

    out = macro.build_hybrid_baml_weekly(api_key="test-key", legacy_path=legacy_path)

    assert out["Date"].tolist() == pd.to_datetime(
        ["2020-01-03", "2020-01-10", "2020-01-17", "2020-01-24"]
    ).tolist()
    assert out["BAMLC0A0CM"].tolist() == [1.0, 2.1, 1.2, 2.4]


def test_macro_panel_keeps_long_history_with_hybrid_baml(monkeypatch):
    dates = pd.date_range("2020-01-03", periods=4, freq="W-FRI")

    def frame(column: str, values: list[float]) -> pd.DataFrame:
        return pd.DataFrame({"Date": dates, column: values})

    def fake_fred_weekly(series_id, column_name, api_key=None, session=None):
        values_by_column = {
            "ANFCI": [1.0, 1.1, 1.2, 1.3],
            "DGS10": [2.0, 2.1, 2.2, 2.3],
            "T10Y2Y": [3.0, 3.1, 3.2, 3.3],
            "T5YIE": [4.0, 4.1, 4.2, 4.3],
        }
        return frame(column_name, values_by_column[column_name])

    monkeypatch.setattr(macro, "pull_fred_weekly_series", fake_fred_weekly)
    monkeypatch.setattr(macro, "build_hybrid_baml_weekly", lambda **kwargs: frame("BAMLC0A0CM", [5.0, 5.1, 5.2, 5.3]))
    monkeypatch.setattr(macro, "pull_yahoo_macro_series", lambda ticker, column_name: frame(column_name, [6.0, 6.1, 6.2, 6.3]))
    monkeypatch.setattr(macro, "pull_gpr_daily", lambda: frame("GPR", [7.0, 7.1, 7.2, 7.3]))

    out = macro.build_weekly_macro_panel(api_key="test-key")

    assert out["Date"].min() == pd.Timestamp("2020-01-10")
    assert out["Date"].max() == pd.Timestamp("2020-01-24")
    assert len(out) == 3
    assert np.allclose(out["d_BAMLC0A0CM"], [0.1, 0.1, 0.1])
