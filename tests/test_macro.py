from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

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


def test_hybrid_baml_uses_live_when_legacy_file_is_lfs_pointer(tmp_path, monkeypatch):
    legacy_path = tmp_path / "baml_w.csv"
    legacy_path.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:abc\n"
        "size 123\n",
        encoding="utf-8",
    )
    live = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2020-01-10", "2020-01-17"]),
            "BAMLC0A0CM": [2.1, 2.4],
        }
    )
    monkeypatch.setattr(macro, "pull_fred_weekly_series", lambda *args, **kwargs: live)

    with pytest.warns(RuntimeWarning, match="FRED-only"):
        out = macro.build_hybrid_baml_weekly(api_key="test-key", legacy_path=legacy_path)

    pd.testing.assert_frame_equal(out, live)


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
            "KCPRU": [8.0, 8.1, 8.2, 8.3],
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


def test_macro_snapshot_preserves_each_series_observation_date(monkeypatch):
    def frame(column: str, dates: list[str], values: list[float]) -> pd.DataFrame:
        return pd.DataFrame({"Date": pd.to_datetime(dates), column: values})

    def fake_fred(series_id, **kwargs):
        dates = ["2026-07-10", "2026-07-17"] if series_id == "ANFCI" else ["2026-07-16", "2026-07-17"]
        return frame(series_id, dates, [1.0, 1.25])

    monkeypatch.setattr(macro, "fred_series", fake_fred)
    monkeypatch.setattr(
        macro,
        "pull_yahoo_macro_series",
        lambda ticker, column_name: frame(
            column_name, ["2026-07-16", "2026-07-17"], [20.0, 21.5]
        ),
    )
    monkeypatch.setattr(
        macro,
        "pull_gpr_daily",
        lambda: frame("GPR", ["2026-07-15", "2026-07-16"], [100.0, 102.0]),
    )

    out = macro.build_macro_snapshot(api_key="test-key").set_index("series")

    assert set(out.index) == {
        "ANFCI",
        "BAMLC0A0CM",
        "DGS2",
        "DGS10",
        "DGS30",
        "T10Y2Y",
        "T5YIE",
        "VIX",
        "MOVE",
        "DXY",
        "GPR",
    }
    assert out.loc["ANFCI", "frequency"] == "weekly"
    assert out.loc["ANFCI", "observation_date"] == "2026-07-17"
    assert out.loc["VIX", "frequency"] == "daily"
    assert out.loc["VIX", "change"] == 1.5
    assert out.loc["GPR", "observation_date"] == "2026-07-16"
