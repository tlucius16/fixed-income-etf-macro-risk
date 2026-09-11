"""Finite-family optimization, ex-ante rules, sensitivities and accounting tests."""
from pathlib import Path
import runpy

import numpy as np
import pandas as pd
import pytest

from src.hedge_design.experiment import load_config
from src.hedge_design.optimize import empirical_cvar, nominal_cvar_lp
from src.hedge_design.phase3 import evaluate_date, quote_candidates, run_phase3, validate_robust_config
from src.data.hedge_inputs import pilot_coverage
from src.hedge_design.robust import finite_model_cvar_lp, model_weights, validate_sensitivity

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def settings():
    return load_config(ROOT / "study_config.json")["robust"]


def solve_tiny(weights, budget=20, upper=100, **kwargs):
    return finite_model_cvar_lp([100, -10], [[50], [0]], [5], [5], weights, 0.5,
                                budget, [upper], dollar_scale=1, **kwargs)


def test_single_model_has_hand_computed_optimum():
    result = solve_tiny([[0.5, 0.5]])
    assert result["x"][0] == pytest.approx(2.2)
    assert result["cvar_usd"] == pytest.approx(1)
    assert result["verified"]


def test_separate_model_thresholds_and_family_expansion():
    args = ([100, 0, -100], [[100], [0], [0]], [10], [10])
    models = np.array([[0.1, 0.2, 0.7], [0.8, 0.1, 0.1]])
    nominal = nominal_cvar_lp(*args, models[0], 0.5, 10, [1], dollar_scale=1)
    single = finite_model_cvar_lp(*args, models[:1], 0.5, 10, [1], dollar_scale=1)
    robust = finite_model_cvar_lp(*args, models, 0.5, 10, [1], dollar_scale=1)
    assert single["cvar_usd"] == pytest.approx(nominal["cvar_usd"])
    assert robust["cvar_usd"] >= single["cvar_usd"] - 1e-8
    quantities = np.linspace(0, 1, 10001)
    brute = min(max(empirical_cvar(np.array(args[0]) - np.array(args[1])[:, 0] * quantity
                                  + 10 * quantity, weight, 0.5) for weight in models)
                for quantity in quantities)
    assert robust["cvar_usd"] == pytest.approx(brute, abs=0.01)
    assert robust["verified"]


@pytest.mark.parametrize("budget,upper,status", [(0, 10, "zero_budget"), (10, 0, "no_available_contracts")])
def test_no_hedge_uses_worst_model(budget, upper, status):
    result = solve_tiny([[0.01, 0.99], [0.99, 0.01]], budget, upper)
    assert result["status"] == status
    assert result["cvar_usd"] == pytest.approx(100)
    assert result["x"][0] == 0


def test_empty_menu_is_unhedged():
    result = finite_model_cvar_lp([100, -10], np.empty((2, 0)), [], [], [[0.5, 0.5]], .5, 10, [])
    assert result["status"] == "empty_menu"
    assert result["cvar_usd"] == 100


def test_robust_percentage_scale_invariance_without_caps():
    risks = []
    for multiple in [.1, 1, 10]:
        result = finite_model_cvar_lp(np.array([100., -10.]) * multiple, [[50], [0]],
                                      [5], [5], [[.5, .5], [.8, .2]], .5,
                                      5 * multiple, [np.inf])
        assert result["verified"]
        risks.append(result["cvar_usd"] / multiple)
    np.testing.assert_allclose(risks, risks[0])


@pytest.mark.parametrize("weights", [[], [[1, 1]], [[np.nan, 1]], [[-1, 2]], [[1]]])
def test_bad_weights_fail(weights):
    with pytest.raises(ValueError):
        solve_tiny(weights)


def test_solver_failure_is_not_a_zero_hedge(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("src.hedge_design.robust.linprog", lambda *args, **kwargs:
                        SimpleNamespace(success=False, status=4, message="synthetic failure"))
    with pytest.raises(ValueError, match="solver failed"):
        solve_tiny([[0.5, 0.5]])


def test_duals_have_correct_sign_and_units():
    def solve(budget, upper):
        return finite_model_cvar_lp([100, -10], [[50], [0]], [5], [5], [[.5, .5]], .5,
                                    budget, upper, dollar_scale=1e6)
    for budget, upper in [(5., np.array([100.])), (20., np.array([1.])), (11., np.array([100.]))]:
        result = solve(budget, upper)
        checks = validate_sensitivity(solve, result, budget, upper, .001, 1e-5)
        assert all(row["verified"] for row in checks)
    assert solve(5, [100])["budget_shadow_price"] == pytest.approx(9)
    assert solve(20, [1])["upper_shadow_prices"][0] == pytest.approx(45)


def test_wrong_dual_is_rejected():
    def solve(budget, upper):
        return solve_tiny([[.5, .5]], budget, upper[0])
    result = solve(5, [100])
    result["budget_shadow_price"] = -99
    with pytest.raises(ValueError, match="Dual perturbation"):
        validate_sensitivity(solve, result, 5, np.array([100]), .001, 1e-5)


def test_weights_cutoff_support_and_normalization(settings):
    scenarios = pd.DataFrame({"window_end": pd.date_range("2020-01-01", periods=100),
                              "weight": .01, "TLT_price_return": -.04,
                              "LQD_price_return": -.08})
    weights, support = model_weights(scenarios, pd.Timestamp("2021-01-01"), settings)
    np.testing.assert_allclose(weights.sum(axis=1), 1)
    assert support.supported.all()
    scenarios.LQD_price_return = 0
    _, support = model_weights(scenarios, pd.Timestamp("2021-01-01"), settings)
    assert not support.supported.all()
    with pytest.raises(ValueError, match="predecision"):
        model_weights(scenarios, pd.Timestamp("2020-02-01"), settings)


@pytest.mark.parametrize("key,value", [("stress_mass", 1), ("minimum_windows", 0),
                                      ("rate_threshold", np.nan), ("dual_relative_step", 0)])
def test_invalid_rules_rejected(settings, key, value):
    settings[key] = value
    with pytest.raises(ValueError):
        validate_robust_config(settings)


@pytest.fixture
def date_inputs():
    helpers = runpy.run_path(str(ROOT / "tests/hedge_design/test_held_out.py"))
    prices, cash = helpers["_daily_prices"]()
    chains = helpers["_chains"](prices)
    config = load_config(ROOT / "study_config.json")
    config["robust"]["minimum_windows"] = 2
    decision, expiry = helpers["SNAPSHOTS"][-1]
    return config, chains, prices, cash, decision, expiry


def test_quote_rules_keep_horizon_and_distinguish_zero_bid(date_inputs):
    _, chains, _, _, decision, expiry = date_inputs
    index = chains.index[chains.snap_date.eq(decision)][0]
    chains.loc[index, "bid"] = 0
    baseline = quote_candidates(chains, decision, expiry, ["LQD"], "baseline")
    zero = quote_candidates(chains, decision, expiry, ["LQD"], "zero_bid")
    assert len(zero) == len(baseline) + 1
    assert zero.expiry.eq(expiry).all()
    matched = quote_candidates(chains, decision, expiry, ["LQD"], "matched_moneyness")
    assert (matched.strike / matched.underlying).between(.95, 1.05).all()


def test_frozen_robust_positions_and_explicit_realized_accounting(date_inputs):
    config, chains, prices, cash, decision, expiry = date_inputs
    kwargs = dict(budgets=[0, 50], tails=[.9], caps=[None, .05], rules=["baseline"])
    first, supported = evaluate_date(*date_inputs, **kwargs)
    assert supported
    prices = prices.copy()
    cash = cash.copy()
    prices.loc[prices.index > decision] *= .8
    cash.loc[expiry, "LQD"] = 1
    changed, supported = evaluate_date(config, chains, prices, cash, decision, expiry, **kwargs)
    assert supported
    pd.testing.assert_frame_equal(first["positions"], changed["positions"])
    pd.testing.assert_frame_equal(first["weights"], changed["weights"])
    pd.testing.assert_series_equal(first["frontier"].objective_usd, changed["frontier"].objective_usd)
    for row in changed["frontier"].itertuples():
        positions = changed["positions"]
        chosen = positions.loc[positions.menu.eq(row.menu) & positions.method.eq(row.method)
            & positions.budget_bps.eq(row.budget_bps)
            & (positions.oi_fraction.isna() if pd.isna(row.oi_fraction) else positions.oi_fraction.eq(row.oi_fraction))]
        shares = config["position_usd"] / prices.loc[decision, "LQD"]
        pnl = shares * (prices.loc[expiry, "LQD"] - prices.loc[decision, "LQD"] + 1)
        pnl += sum(contract.contracts * 100 * max(contract.strike - prices.loc[expiry, contract.ticker], 0)
                   for contract in chosen.itertuples())
        pnl -= row.financed_cost_usd
        assert row.realized_net_loss_usd == pytest.approx(-pnl)


def test_phase3_replay_and_common_policy_dates(date_inputs):
    config, chains, prices, cash, decision, expiry = date_inputs
    config.update(decision_date=str(decision.date()), expiration=str(expiry.date()),
                  frontier_budgets_bps=[0, 50], tail_levels=[.9], oi_fractions=[None, .05])
    coverage = pilot_coverage(chains, prices)
    first, meta = run_phase3(config, chains, prices, cash, coverage)
    second, replay_meta = run_phase3(config, chains, prices, cash, coverage)
    assert meta == replay_meta
    assert meta["matched_dates"] == 2
    assert meta["duals_verified"]
    for name in first:
        pd.testing.assert_frame_equal(first[name], second[name])
    summary = first["robust_held_out_summary"]
    assert summary.matched_dates.eq(2).all()
    assert {"duration", "unhedged", "nominal__direct", "robust__direct"} <= set(summary.policy)
    assert first["robust_held_out_paired"].groupby(["menu", "oi_fraction"], dropna=False).size().eq(2).all()


def test_unverified_robust_solution_aborts(date_inputs, monkeypatch):
    monkeypatch.setattr("src.hedge_design.phase3.finite_model_cvar_lp", lambda *args, **kwargs:
                        {"status": "optimal", "verified": False, "x": np.array([0.])})
    with pytest.raises(ValueError, match="failed verification"):
        evaluate_date(*date_inputs, budgets=[50], tails=[.9], caps=[None], rules=["baseline"])


def test_insufficient_support_has_no_silent_model_fallback(date_inputs):
    config, chains, prices, cash, decision, expiry = date_inputs
    config["robust"]["minimum_windows"] = 100000
    tables, supported = evaluate_date(config, chains, prices, cash, decision, expiry,
                                      budgets=[50], tails=[.9], caps=[None], rules=["baseline"])
    assert not supported
    assert not tables["support"].supported.any()
    assert "frontier" not in tables
