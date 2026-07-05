from __future__ import annotations

import math

import pandas as pd
import pytest

from src.features.options_features import (
    add_duration_exposure_features,
    add_duration_normalized_hedgeability,
    add_latest_duration_exposure_to_panel,
    add_rate_duration_to_panel,
    compute_vrp,
    estimate_rolling_rate_duration,
    summarize_duration_exposure,
    summarize_roll_cost_by_regime,
)


def test_compute_vrp_keeps_ex_ante_gap_separate_from_ex_post_premium():
    df = pd.DataFrame(
        {
            "date": ["2024-01-05"],
            "iv_30d": [0.10],
            "vol_12w_annualized": [0.08],
            "fwd_vol_12w": [0.02],
        }
    )

    out = compute_vrp(df)

    expected_ex_ante = 0.10**2 - 0.08**2
    expected_fwd_vol_annualized = 0.02 * math.sqrt(52)
    expected_ex_post = 0.10**2 - expected_fwd_vol_annualized**2

    assert out.loc[0, "iv_realized_var_gap"] == pytest.approx(expected_ex_ante)
    assert out.loc[0, "vrp"] == pytest.approx(expected_ex_ante)
    assert out.loc[0, "fwd_vol_12w_annualized"] == pytest.approx(
        expected_fwd_vol_annualized
    )
    assert out.loc[0, "vrp_ex_post_12w"] == pytest.approx(expected_ex_post)


def test_estimate_rolling_rate_duration_converts_percentage_point_beta():
    dates = pd.date_range("2024-01-05", periods=60, freq="W-FRI")
    d_yield_pp = ([0.10, -0.05, 0.02, -0.08, 0.04] * 12)[:60]
    duration = 5.0
    returns = [-duration * dy / 100.0 for dy in d_yield_pp]

    core = pd.DataFrame(
        {
            "date": dates,
            "ticker": "TEST",
            "Return": returns,
            "d_DGS10": d_yield_pp,
        }
    )

    out = estimate_rolling_rate_duration(
        core,
        window=52,
        min_obs=40,
        duration_clip=None,
    )

    latest = out.iloc[-1]
    assert latest["duration_nobs"] == 52
    assert latest["rate_beta"] == pytest.approx(-0.05)
    assert latest["realized_rate_duration_raw"] == pytest.approx(duration)
    assert latest["realized_rate_duration"] == pytest.approx(duration)
    assert latest["duration_r2"] == pytest.approx(1.0)


def test_add_duration_exposure_features_uses_latest_prior_estimate():
    chains = pd.DataFrame(
        {
            "ticker": ["TEST", "TEST"],
            "snap_date": pd.to_datetime(["2024-01-10", "2024-01-12"]),
            "dollar_delta": [10.0, 10.0],
            "dollar_vega": [2.0, 2.0],
            "dollar_gamma": [0.5, 0.5],
            "theta_daily": [-0.1, -0.1],
        }
    )
    duration = pd.DataFrame(
        {
            "ticker": ["TEST", "TEST"],
            "date": pd.to_datetime(["2024-01-05", "2024-01-12"]),
            "realized_rate_duration": [5.0, 7.0],
            "duration_r2": [0.25, 0.30],
        }
    )

    out = add_duration_exposure_features(chains, duration)

    assert out.loc[0, "duration_estimate_date"] == pd.Timestamp("2024-01-05")
    assert out.loc[0, "realized_rate_duration"] == pytest.approx(5.0)
    assert out.loc[0, "dollar_duration"] == pytest.approx(50.0)
    assert out.loc[0, "contract_dollar_duration"] == pytest.approx(5000.0)
    assert out.loc[0, "duration_per_vega"] == pytest.approx(25.0)
    assert out.loc[0, "gamma_per_duration"] == pytest.approx(0.01)
    assert out.loc[0, "theta_per_duration"] == pytest.approx(0.002)
    assert out.loc[0, "duration_obs_age_days"] == 5

    assert out.loc[1, "duration_estimate_date"] == pd.Timestamp("2024-01-12")
    assert out.loc[1, "dollar_duration"] == pytest.approx(70.0)


def test_add_duration_exposure_features_fills_missing_dollar_delta_and_quality():
    chains = pd.DataFrame(
        {
            "ticker": ["TEST", "NOISY"],
            "snap_date": pd.to_datetime(["2024-01-12", "2024-01-12"]),
            "underlying": [100.0, 100.0],
            "delta": [0.5, 0.5],
            "dollar_delta": [float("nan"), float("nan")],
            "dollar_vega": [2.0, 2.0],
            "dollar_gamma": [0.5, 0.5],
            "theta_daily": [-0.1, -0.1],
        }
    )
    duration = pd.DataFrame(
        {
            "ticker": ["TEST", "NOISY"],
            "date": pd.to_datetime(["2024-01-05", "2024-01-05"]),
            "realized_rate_duration": [5.0, 0.5],
            "duration_r2": [0.25, 0.01],
        }
    )

    out = add_duration_exposure_features(chains, duration)

    assert out.loc[0, "dollar_delta"] == pytest.approx(50.0)
    assert out.loc[0, "dollar_duration"] == pytest.approx(250.0)
    assert bool(out.loc[0, "duration_quality"]) is True
    assert out.loc[0, "abs_duration_per_vega_quality"] == pytest.approx(125.0)
    assert out.loc[0, "gamma_per_100_duration"] == pytest.approx(0.2)
    assert out.loc[0, "theta_bp_per_duration"] == pytest.approx(4.0)

    assert out.loc[1, "dollar_delta"] == pytest.approx(50.0)
    assert bool(out.loc[1, "duration_quality"]) is False
    assert pd.isna(out.loc[1, "abs_duration_per_vega_quality"])


def test_add_rate_duration_to_panel_adds_duration_scaled_vrp():
    panel = pd.DataFrame(
        {
            "ticker": ["TEST", "NOISY"],
            "date": pd.to_datetime(["2024-01-12", "2024-01-12"]),
            "vrp": [0.02, 0.02],
        }
    )
    duration = pd.DataFrame(
        {
            "ticker": ["TEST", "NOISY"],
            "date": pd.to_datetime(["2024-01-05", "2024-01-05"]),
            "realized_rate_duration": [5.0, 0.5],
            "duration_r2": [0.25, 0.01],
        }
    )

    out = add_rate_duration_to_panel(panel, duration)

    assert out.loc[0, "duration_estimate_date"] == pd.Timestamp("2024-01-05")
    assert bool(out.loc[0, "duration_quality"]) is True
    assert out.loc[0, "vrp_per_duration"] == pytest.approx(0.004)
    assert out.loc[0, "vrp_x_duration"] == pytest.approx(0.10)
    assert out.loc[0, "vrp_per_duration_quality"] == pytest.approx(0.004)

    assert bool(out.loc[1, "duration_quality"]) is False
    assert pd.isna(out.loc[1, "vrp_per_duration_quality"])


def test_summarize_duration_exposure_and_latest_prior_panel_merge():
    chains = pd.DataFrame(
        {
            "ticker": ["TEST", "TEST", "TEST"],
            "snap_date": pd.to_datetime(
                ["2024-01-05", "2024-01-12", "2024-01-12"]
            ),
            "dollar_delta": [10.0, 10.0, 20.0],
            "dollar_vega": [2.0, 2.0, 4.0],
            "dollar_gamma": [0.5, 0.5, 1.0],
            "theta_daily": [-0.1, -0.1, -0.2],
        }
    )
    duration = pd.DataFrame(
        {
            "ticker": ["TEST", "TEST"],
            "date": pd.to_datetime(["2024-01-05", "2024-01-12"]),
            "realized_rate_duration": [5.0, 7.0],
            "duration_r2": [0.25, 0.30],
        }
    )
    chains_duration = add_duration_exposure_features(chains, duration)
    chains_duration["duration_bucket"] = "intermediate"

    by_bucket, by_ticker, by_date_bucket, by_ticker_date = (
        summarize_duration_exposure(chains_duration, bucket_order=["intermediate"])
    )

    assert by_bucket.loc[0, "duration_bucket"] == "intermediate"
    assert by_bucket.loc[0, "contracts"] == 3
    assert by_bucket.loc[0, "quality_contracts"] == 3
    assert by_ticker.loc[0, "ticker"] == "TEST"
    assert len(by_date_bucket) == 2
    assert len(by_ticker_date) == 2

    panel = pd.DataFrame(
        {
            "ticker": ["TEST", "TEST"],
            "date": pd.to_datetime(["2024-01-10", "2024-01-20"]),
        }
    )
    out = add_latest_duration_exposure_to_panel(
        panel,
        by_ticker_date,
        exposure_cols=["vega_per_100_duration_quality_median"],
    )

    assert out.loc[0, "exposure_snap_date"] == pd.Timestamp("2024-01-05")
    assert out.loc[1, "exposure_snap_date"] == pd.Timestamp("2024-01-12")


def test_add_duration_normalized_hedgeability_requires_quality_coverage():
    hedge = pd.DataFrame(
        {
            "ticker": ["GOOD", "THIN"],
            "mean_pass_rate": [0.8, 0.9],
        }
    )
    exposure = pd.DataFrame(
        {
            "ticker": ["GOOD", "THIN"],
            "vega_per_100_duration_quality_median": [0.03, 0.10],
            "gamma_per_100_duration_quality_median": [0.01, 0.04],
            "theta_bp_per_duration_quality_median": [0.5, 0.6],
            "quality_contracts": [100, 10],
            "quality_share": [0.8, 0.8],
        }
    )

    out = add_duration_normalized_hedgeability(
        hedge,
        exposure,
        min_quality_contracts=50,
        min_quality_share=0.25,
    )

    assert out.loc[out["ticker"] == "GOOD", "H_dur"].notna().all()
    assert out.loc[out["ticker"] == "THIN", "H_dur"].isna().all()


def test_summarize_roll_cost_by_regime_uses_quality_ticker_snapshots():
    exposure = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "THIN"],
            "snap_date": pd.to_datetime(
                ["2021-12-31", "2022-01-03", "2022-01-03", "2022-01-03"]
            ),
            "duration_bucket": ["short", "short", "long", "short"],
            "theta_bp_per_duration_quality_median": [0.2, 0.5, 0.8, 9.0],
            "vega_per_100_duration_quality_median": [0.04, 0.05, 0.02, 0.50],
            "quality_contracts": [100, 100, 100, 10],
            "quality_share": [1.0, 1.0, 1.0, 1.0],
        }
    )

    summary, time_series, tradeoff = summarize_roll_cost_by_regime(
        exposure,
        bucket_order=["short", "long"],
        min_quality_contracts=50,
        min_quality_share=0.25,
    )

    short_tightening = summary[
        (summary["rate_regime"].astype(str) == "tightening")
        & (summary["duration_bucket"].astype(str) == "short")
    ].iloc[0]
    assert short_tightening["theta_median"] == pytest.approx(0.5)
    assert short_tightening["theta_change_vs_pre"] == pytest.approx(0.3)
    assert short_tightening["theta_ratio_vs_pre"] == pytest.approx(2.5)
    assert short_tightening["ticker_snap_obs"] == 1

    assert time_series["ticker_snap_obs"].sum() == 3
    short_tradeoff = tradeoff[
        (tradeoff["rate_regime"].astype(str) == "tightening")
        & (tradeoff["duration_bucket"].astype(str) == "short")
    ].iloc[0]
    assert short_tradeoff["theta_cost_per_vega_capacity"] == pytest.approx(10.0)
