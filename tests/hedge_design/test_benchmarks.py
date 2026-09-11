"""Duration-hedge benchmark and TLT positive control: rules that bound the optimizer."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.hedge_design.benchmarks import (
    benchmark_vs_optimizer, duration_hedge_benchmark, ols_hedge_ratio,
)
from src.hedge_design.experiment import load_config, run_frontier
from src.hedge_design.optimize import empirical_cvar

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def test_ols_hedge_ratio_recovers_a_known_slope_and_handles_a_constant_factor():
    rng = np.random.default_rng(0)
    factor = rng.normal(0, 0.02, 500)
    slope, intercept = ols_hedge_ratio(1.7 * factor + 0.001, factor)
    assert slope == pytest.approx(1.7) and intercept == pytest.approx(0.001)
    flat, mean = ols_hedge_ratio(np.array([0.03, -0.01, 0.02]), np.zeros(3))
    assert flat == 0.0 and mean == pytest.approx(0.04 / 3)


@pytest.fixture
def bench_inputs():
    decision, expiry = pd.Timestamp("2021-01-04"), pd.Timestamp("2021-02-01")
    index = pd.DatetimeIndex([decision, expiry])
    prices = pd.DataFrame({"LQD": [100.0, 97.0], "TLT": [90.0, 92.0], "IEF": [95.0, 95.3]}, index=index)
    cash = pd.DataFrame(0.0, index=index, columns=["LQD", "TLT", "IEF"])
    rng = np.random.default_rng(11)
    n = 260
    tlt = rng.normal(0.0, 0.03, n)
    tlt[:14] = rng.uniform(-0.11, -0.06, 14)
    lqd = 0.45 * tlt + rng.normal(0.0, 0.012, n)
    ief = 0.6 * tlt + rng.normal(0.0, 0.004, n)
    scenarios = pd.DataFrame({"scenario_id": np.arange(n), "weight": np.full(n, 1 / n),
                              "trading_sessions": 20, "window_start": pd.Timestamp("2020-01-02"),
                              "window_end": pd.Timestamp("2020-02-03"),
                              "LQD_price_return": lqd, "LQD_cash_return": 0.0,
                              "TLT_price_return": tlt, "TLT_cash_return": 0.0,
                              "IEF_price_return": ief, "IEF_cash_return": 0.0})
    chains = []
    for ticker, spot in (("LQD", 100.0), ("TLT", 90.0), ("IEF", 95.0)):
        for ratio in (0.90, 0.95, 1.00, 1.05, 1.10):
            strike = round(spot * ratio, 1)
            ask = max(strike - spot, 0.0) + 1.5
            chains.append({"ticker": ticker, "snap_date": decision, "expiry": expiry, "right": "P",
                           "strike": strike, "underlying": spot, "bid": ask - 0.2, "ask": ask,
                           "open_interest": 500.0, "delta": -0.5})
    config = json.loads(json.dumps(load_config(ROOT / "study_config.json")))
    tlt_put = pd.Series({"ticker": "TLT", "strike": 90.0, "underlying": 90.0, "bid": 1.4,
                         "ask": 1.5, "open_interest": 500.0, "delta": -0.5})
    return config, chains, scenarios, prices, cash, decision, expiry, tlt_put


def test_duration_benchmark_zero_budget_is_unhedged(bench_inputs):
    config, chains, scenarios, prices, cash, decision, expiry, tlt_put = bench_inputs
    bench, meta = duration_hedge_benchmark(config, tlt_put, scenarios, prices, cash,
                                           decision, expiry, portfolio="LQD")
    zero = bench[bench["budget_bps"] == 0]
    assert (zero["contracts"] == 0).all()
    assert np.allclose(zero["cvar_usd"], zero["unhedged_cvar_usd"])
    assert meta["hedge_ratio_beta"] == pytest.approx(
        ols_hedge_ratio(scenarios["LQD_price_return"], scenarios["TLT_price_return"])[0])


def test_optimizer_treasury_menu_never_underperforms_the_duration_rule(bench_inputs):
    config, chains, scenarios, prices, cash, decision, expiry, tlt_put = bench_inputs
    chains_df = pd.DataFrame(chains)
    bench, _ = duration_hedge_benchmark(config, tlt_put, scenarios, prices, cash,
                                        decision, expiry, portfolio="LQD")
    frontier = run_frontier(config, chains_df, scenarios, prices, cash, decision, expiry)[0]["cvar_frontier"]
    comparison = benchmark_vs_optimizer(bench, frontier, "treasury_substitute")
    assert comparison["optimizer_at_least_as_good"].all()
    # The rule buys a feasible position, so at some budgets the optimizer strictly improves.
    assert (comparison["optimizer_improvement_bps"] > 1.0).any()


def test_binding_constraint_moves_from_budget_to_delta_match_to_oi_cap(bench_inputs):
    config, chains, scenarios, prices, cash, decision, expiry, tlt_put = bench_inputs
    bench, _ = duration_hedge_benchmark(config, tlt_put, scenarios, prices, cash,
                                        decision, expiry, portfolio="LQD")
    at_90 = bench[bench["tail_level"] == 0.9]
    small = at_90[(at_90["budget_bps"] == 10) & (at_90["oi_fraction"].isna())].iloc[0]
    large = at_90[(at_90["budget_bps"] == 200) & (at_90["oi_fraction"].isna())].iloc[0]
    tight = at_90[(at_90["budget_bps"] == 200) & (at_90["oi_fraction"] == 0.01)].iloc[0]
    assert small["binding_constraint"] == "budget"
    assert large["binding_constraint"] == "rate_delta_match"
    assert tight["binding_constraint"] == "oi_cap"


def test_positive_control_direct_hedge_removes_most_of_the_tail_a_proxy_hedge_cannot(bench_inputs):
    config, chains, scenarios, prices, cash, decision, expiry, tlt_put = bench_inputs
    chains_df = pd.DataFrame(chains)
    lqd_frontier = run_frontier(config, chains_df, scenarios, prices, cash, decision, expiry)[0]["cvar_frontier"]
    tlt_control = run_frontier(config, chains_df, scenarios, prices, cash, decision, expiry,
                               portfolio="TLT", menus={"tlt_direct": ["TLT"]})[0]["cvar_frontier"]

    def fraction_remaining(frontier, menu):
        row = frontier[(frontier["menu"] == menu) & (frontier["oi_fraction"].isna())
                       & (frontier["tail_level"] == 0.9) & (frontier["budget_bps"] == 200)].iloc[0]
        return row["cvar_usd"] / row["unhedged_cvar_usd"]

    # A put on the held asset (beta 1) nearly clears the tail; the same budget spent on a
    # 0.45-beta proxy plus idiosyncratic risk leaves most of it.
    assert fraction_remaining(tlt_control, "tlt_direct") < 0.35
    assert fraction_remaining(lqd_frontier, "treasury_substitute") > 0.60
    assert tlt_control["verified"].all()


@pytest.mark.parametrize("delta", [0.0, -1.0, 1.2, np.nan])
def test_duration_benchmark_rejects_a_non_put_delta(bench_inputs, delta):
    config, chains, scenarios, prices, cash, decision, expiry, tlt_put = bench_inputs
    tlt_put = tlt_put.copy()
    tlt_put["delta"] = delta
    with pytest.raises(ValueError, match="negative put delta"):
        duration_hedge_benchmark(config, tlt_put, scenarios, prices, cash, decision, expiry, portfolio="LQD")
