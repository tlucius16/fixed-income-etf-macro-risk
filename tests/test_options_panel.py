import pandas as pd

from src.data import options_panel as module


def test_build_options_panel_uses_snapshot_durations_and_options_universe(
    monkeypatch, tmp_path
):
    core = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-01-05", "2024-04-05", "2024-01-05", "2024-04-05"]
            ),
            "ticker": ["AGG", "AGG", "AAA", "AAA"],
            "Return": [0.01, 0.02, 0.03, 0.04],
            "d_DGS10": [0.1, 0.2, 0.1, 0.2],
        }
    )
    passing = pd.DataFrame(
        {
            "ticker": ["AGG", "AGG"],
            "snap_date": pd.to_datetime(["2024-01-02", "2024-04-01"]),
        }
    )
    durations = pd.DataFrame(
        {
            "ticker": ["AGG", "AGG"],
            "date": pd.to_datetime(["2024-01-02", "2024-04-01"]),
            "realized_rate_duration": [2.0, 4.0],
            "duration_r2": [0.5, 0.5],
        }
    )
    captured = {}

    monkeypatch.setattr(
        module, "screen_chain", lambda *args, **kwargs: {"passing": passing}
    )
    monkeypatch.setattr(
        module, "estimate_rolling_rate_duration", lambda frame: durations
    )

    def fake_add_rate_space_greeks(frame, duration_map):
        captured["contracts"] = frame.copy()
        return frame

    monkeypatch.setattr(module, "add_rate_space_greeks", fake_add_rate_space_greeks)
    monkeypatch.setattr(
        module,
        "compute_chain_capacity",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "ticker": ["AGG", "AGG"],
                "snap_date": pd.to_datetime(["2024-01-02", "2024-04-01"]),
                "side": ["total", "total"],
                "hedge_capacity_ratio": [0.1, 0.2],
            }
        ),
    )
    monkeypatch.setattr(module.cfg, "IV_PANEL_CSV", tmp_path / "missing_iv.csv")

    out = module.build_options_panel(
        core, chains_df=pd.DataFrame({"right": ["C"]}), write_csv=False
    )

    assert set(out["ticker"]) == {"AGG"}
    assert captured["contracts"]["D_i"].tolist() == [2.0, 4.0]
    assert out["hedge_capacity_ratio"].tolist() == [0.1, 0.2]


def test_iv_join_does_not_suffix_existing_core_outcomes(monkeypatch, tmp_path):
    core = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05"]),
            "ticker": ["AGG"],
            "Return": [0.01],
            "d_DGS10": [0.1],
            "fwd_maxdd_12w": [-0.05],
        }
    )
    passing = pd.DataFrame(
        {"ticker": ["AGG"], "snap_date": pd.to_datetime(["2024-01-02"])}
    )
    durations = pd.DataFrame(
        {
            "ticker": ["AGG"],
            "date": pd.to_datetime(["2024-01-02"]),
            "realized_rate_duration": [2.0],
            "duration_r2": [0.5],
        }
    )
    iv_path = tmp_path / "iv.csv"
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05"]),
            "ticker": ["AGG"],
            "iv_30d": [0.2],
            "fwd_maxdd_12w": [-0.99],
        }
    ).to_csv(iv_path, index=False)

    monkeypatch.setattr(
        module, "screen_chain", lambda *args, **kwargs: {"passing": passing}
    )
    monkeypatch.setattr(
        module, "estimate_rolling_rate_duration", lambda frame: durations
    )
    monkeypatch.setattr(
        module, "add_rate_space_greeks", lambda frame, duration_map: frame
    )
    monkeypatch.setattr(
        module,
        "compute_chain_capacity",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "ticker": ["AGG"],
                "snap_date": pd.to_datetime(["2024-01-02"]),
                "side": ["total"],
                "hedge_capacity_ratio": [0.1],
            }
        ),
    )
    monkeypatch.setattr(module.cfg, "IV_PANEL_CSV", iv_path)

    out = module.build_options_panel(
        core, chains_df=pd.DataFrame({"right": ["C"]}), write_csv=False
    )

    assert out.loc[0, "fwd_maxdd_12w"] == -0.05
    assert out.loc[0, "iv_30d"] == 0.2
    assert not any(c.endswith(("_x", "_y")) for c in out.columns)
