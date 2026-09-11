"""Matched held-out check: policies frozen pre-decision, one realized outcome each."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.data.hedge_inputs import pilot_coverage
from src.hedge_design.experiment import (
    HELD_OUT_POLICIES, load_config, qualifying_dates, run_held_out,
)
from src.hedge_design.optimize import empirical_cvar

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
SNAPSHOTS = [(pd.Timestamp("2021-06-01"), pd.Timestamp("2021-07-01")),
             (pd.Timestamp("2022-09-01"), pd.Timestamp("2022-09-30"))]


def _daily_prices(seed=3):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2015-01-01", "2022-10-14")
    factor = np.cumsum(rng.normal(0, 0.01, len(index)))
    frame = {}
    for ticker, beta, base in (("LQD", 0.45, 110.0), ("TLT", 1.0, 95.0), ("IEF", 0.6, 100.0)):
        idio = np.cumsum(rng.normal(0, 0.004, len(index)))
        frame[ticker] = base * np.exp(-beta * factor + idio)
    prices = pd.DataFrame(frame, index=index)
    cash = pd.DataFrame(0.0, index=index, columns=prices.columns)
    return prices, cash


def _chains(prices):
    rows = []
    for decision, expiry in SNAPSHOTS:
        for ticker in ("LQD", "TLT", "IEF"):
            spot = float(prices.loc[decision, ticker])
            for ratio in (0.92, 0.96, 1.00, 1.04):
                strike = round(spot * ratio, 1)
                ask = max(strike - spot, 0.0) + 0.02 * spot
                rows.append({"ticker": ticker, "snap_date": decision, "expiry": expiry,
                             "right": "P", "strike": strike, "underlying": spot,
                             "bid": ask - 0.05 * ask, "ask": ask, "open_interest": 800.0,
                             "delta": -0.5})
    return pd.DataFrame(rows)


@pytest.fixture
def held_out_env():
    prices, cash = _daily_prices()
    chains = _chains(prices)
    coverage = pilot_coverage(chains, prices)
    config = json.loads(json.dumps(load_config(ROOT / "study_config.json")))
    config["lookback_years"] = 4
    return config, chains, prices, cash, coverage


def test_qualifying_dates_reports_expiration_and_menu_availability(held_out_env):
    _, chains, prices, _, coverage = held_out_env
    dates = qualifying_dates(coverage)
    assert len(dates) == 2
    assert dates["all_menus_available"].all()
    # Drop every IEF put at the first snapshot -> that snapshot loses its menu.
    thin = chains[~((chains["ticker"] == "IEF") & (chains["snap_date"] == SNAPSHOTS[0][0]))]
    thinned = qualifying_dates(pilot_coverage(thin, prices)).set_index("decision_date")
    assert not thinned.loc["2021-06-01", "all_menus_available"]
    assert thinned.loc["2021-06-01", "ief_eligible_puts"] == 0


def test_frozen_positions_ignore_prices_after_the_decision_date(held_out_env):
    config, chains, prices, cash, coverage = held_out_env
    tables, _ = run_held_out(config, chains, prices, cash, coverage)
    # Move every price strictly after the later decision date; its expiration is in that range.
    tampered = prices.copy()
    tampered.loc[tampered.index > SNAPSHOTS[1][0]] *= [0.5, 1.5, 1.2]
    shifted, _ = run_held_out(config, chains, tampered, cash, coverage)

    key = ["decision_date", "policy"]
    a = tables["held_out_outcomes"].set_index(key)
    b = shifted["held_out_outcomes"].set_index(key)
    # Sizing and design CVaR use only pre-decision scenarios and the decision-date spot.
    pd.testing.assert_series_equal(a["contracts"], b["contracts"])
    pd.testing.assert_series_equal(a["design_cvar_bps"], b["design_cvar_bps"])
    # The earlier snapshot's outcome (expiry 2021-07-01) is untouched; the later one moves.
    early = a.xs("2021-06-01", level="decision_date")["realized_net_loss_bps"]
    pd.testing.assert_series_equal(early, b.xs("2021-06-01", level="decision_date")["realized_net_loss_bps"])
    late = a.xs("2022-09-01", level="decision_date")["realized_net_loss_bps"]
    assert not np.allclose(late, b.xs("2022-09-01", level="decision_date")["realized_net_loss_bps"])


def test_unhedged_policy_realized_loss_is_the_portfolio_loss(held_out_env):
    config, chains, prices, cash, coverage = held_out_env
    outcomes = run_held_out(config, chains, prices, cash, coverage)[0]["held_out_outcomes"]
    position = config["position_usd"]
    for row in outcomes[outcomes["policy"] == "unhedged"].itertuples():
        decision, expiry = pd.Timestamp(row.decision_date), pd.Timestamp(row.expiration)
        expected = -position * (prices.loc[expiry, "LQD"] / prices.loc[decision, "LQD"] - 1)
        assert row.realized_net_loss_usd == pytest.approx(expected)
        assert row.spent_usd == 0.0


def test_missing_delta_uses_common_successful_dates(held_out_env):
    config, chains, prices, cash, coverage = held_out_env
    chains.loc[chains.snap_date.eq(SNAPSHOTS[0][0]) & chains.ticker.eq("TLT"), "delta"] = np.nan
    tables, meta = run_held_out(config, chains, prices, cash, coverage)
    assert tables["held_out_summary"]["matched_dates"].eq(1).all()
    assert meta["matched_decision_dates"] == 1
    assert "2021-06-01" in meta["excluded_snapshots"]


def test_held_out_rejects_candidate_spot_mismatch(held_out_env):
    config, chains, prices, cash, coverage = held_out_env
    chains.loc[0, "underlying"] *= 1.1
    with pytest.raises(ValueError, match="spot mismatch"):
        run_held_out(config, chains, prices, cash, coverage)


def test_capped_policies_spend_no_more_than_their_uncapped_form(held_out_env):
    config, chains, prices, cash, coverage = held_out_env
    outcomes = run_held_out(config, chains, prices, cash, coverage)[0]["held_out_outcomes"]
    wide = outcomes.pivot_table(index="decision_date", columns="policy", values="spent_usd")
    assert (wide["duration_hedge_oi_capped"] <= wide["duration_hedge"] + 1e-6).all()
    assert (wide["cvar_treasury_substitute_oi_capped"] <= wide["cvar_treasury_substitute"] + 1e-6).all()


def test_all_frozen_positions_are_independently_verified(held_out_env):
    config, chains, prices, cash, coverage = held_out_env
    tables, meta = run_held_out(config, chains, prices, cash, coverage)
    assert meta["all_frozen_positions_verified"]
    assert tables["held_out_outcomes"].loc[tables["held_out_outcomes"]["evaluable"], "verified"].all()
    summary = tables["held_out_summary"].set_index("policy")
    assert (summary["matched_dates"] == 2).all()
    # Design CVaR of the unhedged policy equals the plain scenario CVaR.
    assert set(summary.index) == {name for name, *_ in HELD_OUT_POLICIES}


def test_require_all_menus_flag_controls_which_dates_are_scored(held_out_env):
    config, chains, prices, cash, coverage = held_out_env
    thin = chains[~((chains["ticker"] == "LQD") & (chains["snap_date"] == SNAPSHOTS[1][0]))]
    thin_coverage = pilot_coverage(thin, prices)
    strict = run_held_out(config, thin, prices, cash, thin_coverage)[0]["held_out_outcomes"]
    scored = strict[(strict["policy"] == "cvar_combined") & strict["evaluable"]]
    assert set(scored["decision_date"]) == {"2021-06-01"}
    assert (strict[(strict["decision_date"] == "2022-09-01")]["evaluable"] == False).all()


@pytest.mark.parametrize("mutate", [
    {"budget_bps": 0}, {"budget_bps": 999}, {"tail_level": 0.5}, {"oi_cap": None}, {"oi_cap": 0.2},
])
def test_config_rejects_incoherent_held_out_settings(mutate, tmp_path):
    config = json.loads((ROOT / "study_config.json").read_text())
    config["held_out"].update(mutate)
    path = tmp_path / "c.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="held_out"):
        load_config(path)
