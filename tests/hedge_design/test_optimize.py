"""Nominal CVaR LP: hand-computable optima, feasibility, and LP-monotonicity invariants."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.hedge_design.experiment import (
    QUANTITY_FLOOR, _oi_upper_bound, candidate_puts, load_config, run_frontier,
)
from src.hedge_design.optimize import empirical_cvar, empirical_var, nominal_cvar_lp

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


# --- pure LP ---------------------------------------------------------------

def test_two_scenario_optimum_is_the_analytic_crossing_point():
    # loss_0(x) = 100 - 45x, loss_1(x) = -10 + 5x; alpha 0.5 -> CVaR = max of the two.
    # Minimised where they cross: x* = 2.2, CVaR* = 1.0, well inside the budget cap x <= 4.
    sol = nominal_cvar_lp(np.array([100.0, -10.0]), np.array([[50.0], [0.0]]),
                          np.array([5.0]), np.array([5.0]), np.array([0.5, 0.5]),
                          0.5, 20.0, np.array([np.inf]), dollar_scale=1.0,
                          feasibility_tol_usd=1e-6)
    assert sol["status"] == "optimal"
    assert sol["x"][0] == pytest.approx(2.2, abs=1e-6)
    assert sol["cvar_usd"] == pytest.approx(1.0, abs=1e-6)
    assert sol["eta_usd"] == pytest.approx(1.0, abs=1e-6)
    assert sol["verified"]


def test_reported_cvar_is_the_independent_recompute_not_the_raw_objective():
    rng = np.random.default_rng(1)
    losses = np.sort(rng.normal(0, 1e5, 400))
    payoffs = np.clip(rng.normal(3e3, 1e3, (400, 5)), 0, None)
    c0 = np.array([1500.0, 1800.0, 900.0, 2200.0, 700.0])
    sol = nominal_cvar_lp(losses, payoffs, c0, c0 * 1.004, np.full(400, 1 / 400),
                          0.9, 250_000.0, np.full(5, np.inf))
    net = losses - payoffs @ sol["x"] + float(c0 * 1.004 @ sol["x"])
    assert sol["cvar_usd"] == pytest.approx(empirical_cvar(net, np.full(400, 1 / 400), 0.9))
    assert sol["cvar_abs_error_usd"] <= 1e-4
    assert sol["verified"]


def test_zero_budget_empty_menu_and_no_capacity_all_reduce_to_unhedged():
    losses, weights = np.array([100.0, -10.0, 40.0]), np.full(3, 1 / 3)
    unhedged = empirical_cvar(losses, weights, 0.6)
    payoffs, c0 = np.array([[50.0], [0.0], [10.0]]), np.array([5.0])
    zero = nominal_cvar_lp(losses, payoffs, c0, c0, weights, 0.6, 0.0, np.array([np.inf]))
    empty = nominal_cvar_lp(losses, np.zeros((3, 0)), np.zeros(0), np.zeros(0), weights, 0.6, 9.0, np.zeros(0))
    capped = nominal_cvar_lp(losses, payoffs, c0, c0, weights, 0.6, 9.0, np.array([0.0]))
    assert zero["status"] == "zero_budget" and empty["status"] == "empty_menu"
    assert capped["status"] == "no_available_contracts"
    for sol in (zero, empty, capped):
        assert sol["cvar_usd"] == pytest.approx(unhedged)
        assert np.all(np.asarray(sol["x"]) == 0.0) and sol["verified"]


def test_more_budget_looser_cap_never_raise_the_optimised_cvar():
    rng = np.random.default_rng(2)
    losses = rng.normal(0, 1e5, 300)
    payoffs = np.clip(rng.normal(2e3, 8e2, (300, 4)), 0, None)
    c0 = np.array([1200.0, 1600.0, 800.0, 2000.0])
    oi = np.array([50.0, 40.0, 90.0, 30.0])
    prev_budget = np.inf
    for budget in (0.0, 5e4, 1e5, 2e5, 5e5):
        cvar = nominal_cvar_lp(losses, payoffs, c0, c0 * 1.01, np.full(300, 1 / 300),
                               0.9, budget, np.full(4, np.inf))["cvar_usd"]
        if np.isfinite(prev_budget):
            assert cvar <= prev_cvar + 1e-6
        prev_budget, prev_cvar = budget, cvar
    prev_cvar = np.inf
    for fraction in (0.1, 0.5, 1.0, np.inf):
        upper = np.full(4, np.inf) if not np.isfinite(fraction) else fraction * oi
        cvar = nominal_cvar_lp(losses, payoffs, c0, c0 * 1.01, np.full(300, 1 / 300),
                               0.9, 3e5, upper)["cvar_usd"]
        assert cvar <= prev_cvar + 1e-6
        prev_cvar = cvar


def test_solution_respects_budget_and_upper_bounds():
    rng = np.random.default_rng(3)
    losses = rng.normal(0, 1e5, 250)
    payoffs = np.clip(rng.normal(2e3, 9e2, (250, 3)), 0, None)
    c0 = np.array([1000.0, 1400.0, 700.0])
    upper = np.array([12.0, np.inf, 30.0])
    sol = nominal_cvar_lp(losses, payoffs, c0, c0 * 1.02, np.full(250, 1 / 250),
                          0.9, 8e4, upper)
    assert sol["spent_usd"] <= 8e4 + 1e-6
    assert sol["x"][0] <= 12.0 + 1e-9 and sol["x"][2] <= 30.0 + 1e-9
    assert (sol["x"] >= -1e-9).all()
    assert sol["budget_violation_usd"] <= 1e-6 and sol["bound_violation_contracts"] <= 1e-6


def test_percentage_frontier_is_invariant_to_portfolio_size_without_a_cap():
    rng = np.random.default_rng(4)
    base_returns = rng.normal(0, 0.015, 500)
    payoffs = np.clip(rng.normal(2e3, 7e2, (500, 3)), 0, None)
    c0 = np.array([1100.0, 1500.0, 850.0])
    bps = []
    for position in (1e7, 1e8, 7e8):
        sol = nominal_cvar_lp(-position * base_returns, payoffs, c0, c0 * 1.004,
                              np.full(500, 1 / 500), 0.9, position * 50 / 1e4, np.full(3, np.inf))
        bps.append(sol["cvar_usd"] / position * 1e4)
    assert np.ptp(bps) <= 1e-6


def test_budget_shadow_price_has_the_right_sign_and_finite_difference():
    rng = np.random.default_rng(5)
    losses = rng.normal(0, 1e5, 400)
    payoffs = np.clip(rng.normal(2.5e3, 9e2, (400, 4)), 0, None)
    c0 = np.array([1300.0, 1700.0, 900.0, 2100.0])
    budget = 6e4  # small enough to bind with no OI cap
    base = nominal_cvar_lp(losses, payoffs, c0, c0 * 1.01, np.full(400, 1 / 400),
                           0.9, budget, np.full(4, np.inf), dollar_scale=1.0)
    bump = budget * 1e-4
    up = nominal_cvar_lp(losses, payoffs, c0, c0 * 1.01, np.full(400, 1 / 400),
                         0.9, budget + bump, np.full(4, np.inf), dollar_scale=1.0)
    assert base["spent_usd"] == pytest.approx(budget, rel=1e-6)
    assert base["budget_shadow_price"] > 0
    finite_difference = -(up["cvar_usd"] - base["cvar_usd"]) / bump
    assert base["budget_shadow_price"] == pytest.approx(finite_difference, rel=5e-2)


@pytest.mark.parametrize("bad", ["weights", "alpha", "budget", "nonfinite", "cost"])
def test_ill_posed_inputs_are_rejected(bad):
    losses, payoffs = np.array([1.0, 2.0, 3.0]), np.array([[1.0], [1.0], [1.0]])
    c0, weights = np.array([2.0]), np.full(3, 1 / 3)
    kw = dict(losses=losses, payoffs=payoffs, upfront_cost=c0, horizon_cost=c0,
              weights=weights, alpha=0.9, budget=10.0, upper=np.array([np.inf]))
    if bad == "weights":
        kw["weights"] = np.array([0.5, 0.5, 0.5])
    elif bad == "alpha":
        kw["alpha"] = 1.0
    elif bad == "budget":
        kw["budget"] = -1.0
    elif bad == "nonfinite":
        kw["losses"] = np.array([np.nan, 2.0, 3.0])
    else:
        kw["upfront_cost"] = np.array([0.0])
    with pytest.raises(ValueError):
        nominal_cvar_lp(**kw)


def test_empirical_var_is_the_weighted_quantile():
    losses, weights = np.array([10.0, -5.0, 3.0]), np.array([0.2, 0.5, 0.3])
    assert empirical_var(losses, weights, 0.4) == pytest.approx(-5.0)   # CDF(-5) = 0.5 >= 0.4
    assert empirical_var(losses, weights, 0.8) == pytest.approx(3.0)    # CDF(3) = 0.8 >= 0.8
    assert empirical_var(losses, weights, 0.85) == pytest.approx(10.0)  # only CDF(10) = 1.0 >= 0.85


# --- candidate selection and OI ceilings ---------------------------------

def test_oi_upper_bound_marks_unknown_or_fractional_oi_unavailable_under_a_cap():
    frame = pd.DataFrame({"open_interest": [100.0, np.nan, -5.0, 10.5, 0.0]})
    np.testing.assert_array_equal(_oi_upper_bound(frame, None), np.full(5, np.inf))
    np.testing.assert_allclose(_oi_upper_bound(frame, 0.1), [10.0, 0.0, 0.0, 0.0, 0.0])


def test_candidate_puts_applies_the_quote_screen_only():
    decision, expiry = pd.Timestamp("2025-01-02"), pd.Timestamp("2025-01-31")
    chains = pd.DataFrame([
        {"ticker": "LQD", "snap_date": decision, "expiry": expiry, "right": "P",
         "strike": 130.0, "underlying": 100.0, "bid": 30.0, "ask": 31.0, "open_interest": 0.0},
        {"ticker": "LQD", "snap_date": decision, "expiry": expiry, "right": "P",
         "strike": 95.0, "underlying": 100.0, "bid": 4.0, "ask": 3.0, "open_interest": 5.0},
        {"ticker": "LQD", "snap_date": decision, "expiry": expiry, "right": "C",
         "strike": 100.0, "underlying": 100.0, "bid": 2.0, "ask": 2.1, "open_interest": 9.0},
    ])
    out = candidate_puts(chains, decision, expiry, ["LQD"])
    # Deep in the money with zero OI survives; the crossed put and the call do not.
    assert out["strike"].tolist() == [130.0]


# --- frontier orchestration end to end ----------------------------------

def _frontier_config(position=1e8):
    config = load_config(ROOT / "study_config.json")
    config = json.loads(json.dumps(config))
    config["position_usd"] = position
    return config


def _synthetic_scenarios(n=240, seed=7):
    rng = np.random.default_rng(seed)
    lqd = rng.normal(0.001, 0.02, n)
    lqd[:12] = rng.uniform(-0.13, -0.07, 12)          # embedded left tail
    tlt = 0.35 * lqd + rng.normal(0.0, 0.03, n)
    ief = 0.20 * lqd + rng.normal(0.0, 0.012, n)
    return pd.DataFrame({"scenario_id": np.arange(n), "weight": np.full(n, 1 / n),
                         "trading_sessions": 20, "window_start": pd.Timestamp("2020-01-02"),
                         "window_end": pd.Timestamp("2020-02-03"),
                         "LQD_price_return": lqd, "LQD_cash_return": 0.0,
                         "TLT_price_return": tlt, "TLT_cash_return": 0.0,
                         "IEF_price_return": ief, "IEF_cash_return": 0.0})


def _synthetic_chains(decision, expiry):
    spots = {"LQD": 100.0, "TLT": 90.0, "IEF": 95.0}
    rows = []
    for ticker, spot in spots.items():
        for ratio in (0.90, 0.95, 1.00, 1.05, 1.10):
            strike = round(spot * ratio, 1)
            ask = max(strike - spot, 0.0) + 1.6
            rows.append({"ticker": ticker, "snap_date": decision, "expiry": expiry,
                         "right": "P", "strike": strike, "underlying": spot,
                         "bid": ask - 0.25, "ask": ask, "open_interest": 400.0})
    return pd.DataFrame(rows)


@pytest.fixture
def frontier_inputs():
    decision, expiry = pd.Timestamp("2021-01-04"), pd.Timestamp("2021-02-01")
    index = pd.DatetimeIndex([decision, expiry])
    prices = pd.DataFrame({"LQD": [100.0, 97.0], "TLT": [90.0, 91.5], "IEF": [95.0, 95.2]}, index=index)
    cash = pd.DataFrame(0.0, index=index, columns=["LQD", "TLT", "IEF"])
    return _frontier_config(), _synthetic_chains(decision, expiry), _synthetic_scenarios(), prices, cash, decision, expiry


def test_run_frontier_verifies_objectives_invariants_and_scale_control(frontier_inputs):
    config, chains, scenarios, prices, cash, decision, expiry = frontier_inputs
    tables, summary = run_frontier(config, chains, scenarios, prices, cash, decision, expiry)
    assert summary["all_solves_ok"]
    assert summary["all_objectives_verified"]
    assert summary["monotonicity_invariants_hold"]
    assert summary["percentage_frontier_scale_invariant_no_cap"]
    assert tables["cvar_invariants"]["ok"].all()

    frontier = tables["cvar_frontier"]
    assert set(frontier["menu"]) == {"direct", "treasury_substitute", "combined"}
    losses = -config["position_usd"] * scenarios["LQD_price_return"].to_numpy()
    for alpha in config["tail_levels"]:
        unhedged = empirical_cvar(losses, scenarios["weight"].to_numpy(), alpha)
        zero = frontier[(frontier["budget_bps"] == 0) & (frontier["tail_level"] == alpha)]
        assert np.allclose(zero["cvar_usd"], unhedged)
    assert frontier["cvar_abs_error_usd"].max() <= 1e-3


def test_frontier_rejects_nonselected_candidate_spot_mismatch(frontier_inputs):
    config, chains, scenarios, prices, cash, decision, expiry = frontier_inputs
    chains.loc[0, "underlying"] *= 1.1
    with pytest.raises(ValueError, match="spot mismatch"):
        run_frontier(config, chains, scenarios, prices, cash, decision, expiry)


@pytest.mark.parametrize("status,verified", [("numerical_difficulty", False), ("optimal", False)])
def test_frontier_aborts_failed_verification(frontier_inputs, monkeypatch, status, verified):
    monkeypatch.setattr("src.hedge_design.experiment.nominal_cvar_lp",
                        lambda *args, **kwargs: {"status": status, "verified": verified, "x": None})
    with pytest.raises(ValueError, match="failed verification"):
        run_frontier(*frontier_inputs)


def test_run_frontier_combined_menu_dominates_each_sub_menu(frontier_inputs):
    config, chains, scenarios, prices, cash, decision, expiry = frontier_inputs
    frontier = run_frontier(config, chains, scenarios, prices, cash, decision, expiry)[0]["cvar_frontier"]
    wide = frontier.assign(oi=frontier["oi_fraction"].map(lambda c: "none" if pd.isna(c) else f"{c:g}")).pivot_table(
        index=["tail_level", "budget_bps", "oi"], columns="menu", values="cvar_usd")
    assert (wide["combined"] <= wide["direct"] + 1e-6).all()
    assert (wide["combined"] <= wide["treasury_substitute"] + 1e-6).all()


def test_run_frontier_positions_stay_within_budget_and_named_bounds(frontier_inputs):
    config, chains, scenarios, prices, cash, decision, expiry = frontier_inputs
    tables = run_frontier(config, chains, scenarios, prices, cash, decision, expiry)[0]
    positions, frontier = tables["cvar_positions"], tables["cvar_frontier"]
    spent = positions.groupby(["menu", "tail_level", "budget_bps", "oi_fraction"], dropna=False)["premium_usd"].sum()
    for keys, total in spent.items():
        budget = config["position_usd"] * keys[2] / 1e4
        assert total <= budget + 1.0
    capped = positions[positions["oi_fraction"].notna()]
    assert (capped["contracts"] <= capped["upper_bound_contracts"] + 1e-9).all()
    assert (frontier["n_contracts_selected"] > 0).any()
