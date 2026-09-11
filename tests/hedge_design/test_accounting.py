"""Synthetic accounting, information-cutoff, and immutable-run checks."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from src.data.hedge_inputs import CHAIN_PATH, PRICE_PATH, sha256_file
from src.hedge_design.experiment import (
    budget_quantity, empirical_cvar, evaluate, load_config, put_payoff, run_pilot,
    selected_contracts, verify_run,
)
from src.hedge_design.market import (
    adjustment_diagnostic, historical_scenarios, holding_return, market_panels, validate_market,
)

ROOT = Path(__file__).resolve().parents[2]


def market_fixture():
    dates = pd.bdate_range("2024-01-01", "2024-11-01")
    return pd.DataFrame([{"date": date, "ticker": ticker, "close": 100.0,
                         "adj_close": 100.0, "dividends": 0.0, "capital_gains": 0.0, "splits": 0.0}
                         for date in dates for ticker in ["LQD", "TLT", "IEF"]])


def contract_fixture():
    return pd.DataFrame([{"ticker": ticker, "snap_date": pd.Timestamp("2024-10-01"),
                         "expiry": pd.Timestamp("2024-11-01"), "strike": 100.0,
                         "right": "P", "underlying": 100.0, "bid": 1.9, "ask": 2.0,
                         "open_interest": 100, "delta": -0.5}
                        for ticker in ["LQD", "TLT", "IEF"]])


def config_fixture():
    config = load_config(ROOT / "study_config.json")
    config.update(decision_date="2024-10-01", expiration="2024-11-01", robust_enabled=False)
    return config


def test_put_payoff_is_intrinsic_per_contract_not_adjusted_return():
    np.testing.assert_allclose(put_payoff(100, np.array([90, 100, 110]), 100), [1000, 0, 0])


@pytest.mark.parametrize("price", [-1, np.nan, np.inf])
def test_invalid_payoff_rejected(price):
    with pytest.raises(ValueError):
        put_payoff(100, price, 100)


def test_ex_date_boundaries_fixed_shares_and_no_reinvestment():
    dates = pd.date_range("2024-01-01", periods=3)
    prices = pd.DataFrame({"LQD": [100, 90, 80]}, index=dates)
    cash = pd.DataFrame({"LQD": [10, 2, 3]}, index=dates)
    pr, cr = holding_return(prices, cash, dates[0], dates[-1])
    assert pr.LQD == pytest.approx(-0.2)
    assert cr.LQD == pytest.approx(0.05)


def test_joint_scenarios_are_strictly_historical_and_ignore_later_values():
    data = market_fixture()
    data["close"] += data.date.rank(method="dense") * 0.01
    prices, cash = market_panels(data)
    decision, expiry = pd.Timestamp("2024-10-01"), pd.Timestamp("2024-11-01")
    first = historical_scenarios(prices, cash, decision, expiry, 5)
    assert first.window_end.max() < decision
    assert first.weight.sum() == pytest.approx(1)
    assert first.trading_sessions.nunique() == 1
    assert (first.LQD_price_return == first.TLT_price_return).all()
    prices.loc[prices.index >= decision] *= 10
    cash.loc[cash.index >= decision] += 999
    pd.testing.assert_frame_equal(first, historical_scenarios(prices, cash, decision, expiry, 5))


def test_exact_expiration_required():
    prices, cash = market_panels(market_fixture())
    with pytest.raises(ValueError, match="exact"):
        historical_scenarios(prices, cash, pd.Timestamp("2024-10-01"), pd.Timestamp("2024-11-02"), 5)


@pytest.mark.parametrize("failure", ["duplicate", "unaligned", "nan", "split", "missing_field"])
def test_market_failures_do_not_become_zero_actions_or_filled_prices(failure):
    frame = market_fixture()
    if failure == "duplicate":
        frame = pd.concat([frame, frame.iloc[[0]]])
    elif failure == "unaligned":
        frame = frame.iloc[1:]
    elif failure == "nan":
        frame.loc[0, "dividends"] = np.nan
    elif failure == "split":
        frame.loc[0, "splits"] = 2
    else:
        frame = frame.drop(columns="capital_gains")
    with pytest.raises(ValueError):
        validate_market(frame, ["LQD", "TLT", "IEF"])


def test_adjustment_check_matches_explicit_one_day_cash_return():
    frame = market_fixture().iloc[:6].copy()
    frame.loc[frame.date.eq(frame.date.max()), "close"] = 99
    frame.loc[frame.date.eq(frame.date.max()), "dividends"] = 1
    assert adjustment_diagnostic(frame).max_daily_return_gap_bps.eq(0).all()


def test_nearest_atm_selected_without_oi_floor_or_outcome_data():
    frame = contract_fixture()
    frame.loc[0, "open_interest"] = np.nan
    worse = frame.copy()
    worse["strike"] = 95
    chosen, diagnostics = selected_contracts(pd.concat([frame, worse], ignore_index=True),
                pd.Timestamp("2024-10-01"), pd.Timestamp("2024-11-01"), ["LQD", "TLT", "IEF"])
    assert chosen.strike.eq(100).all()
    assert diagnostics.selected.sum() == 3
    assert diagnostics.oi_missing.sum() == 2


def test_quote_exclusion_leaves_empty_menu_instead_of_switching_expiry():
    frame = contract_fixture()
    frame.loc[0, "bid"] = 0
    with pytest.raises(ValueError, match="all three"):
        selected_contracts(frame, pd.Timestamp("2024-10-01"), pd.Timestamp("2024-11-01"),
                           ["LQD", "TLT", "IEF"])


def test_text_numeric_quotes_and_unknown_oi_are_normalized():
    frame = contract_fixture().astype({"strike": str, "ask": str, "underlying": str, "open_interest": str})
    frame.loc[0, "open_interest"] = "unknown"
    chosen, _ = selected_contracts(frame, pd.Timestamp("2024-10-01"), pd.Timestamp("2024-11-01"),
                                  ["LQD", "TLT", "IEF"])
    assert np.isnan(chosen.set_index("ticker").loc["LQD", "open_interest"])
    assert chosen.strike.eq(100).all()


def test_zero_oi_does_not_remove_a_quote_menu():
    frame = contract_fixture()
    frame.loc[0, "open_interest"] = 0
    chosen, _ = selected_contracts(frame, pd.Timestamp("2024-10-01"), pd.Timestamp("2024-11-01"),
                                  ["LQD", "TLT", "IEF"])
    assert len(chosen) == 3


@pytest.mark.parametrize("oi", [np.nan, np.inf, -1, 1.5])
def test_invalid_oi_unavailable_in_capped_case_but_not_quote_baseline(oi):
    assert budget_quantity(2, 100, 1, 2010, oi, 0.1) == (0, "unavailable_oi")
    assert budget_quantity(2, 100, 1, 2010, oi, None)[0] == 10


def test_budget_and_oi_constraint_sizing():
    assert budget_quantity(2, 100, 1, 2010, 100, 0.01) == (1, "oi_binding")
    assert budget_quantity(2, 100, 1, 2010, 1000, 0.1) == (10, "budget_binding")
    assert budget_quantity(2, 100, 1, 2010, 0, 0.1) == (0, "oi_binding")


def test_cvar_uses_fractional_boundary_mass_and_accepts_negative_losses():
    assert empirical_cvar(np.array([0, 10, 20]), np.array([0.5, 0.3, 0.2]), 0.75) == pytest.approx(18)
    assert empirical_cvar(np.array([-3, -2, -1]), np.ones(3) / 3, 0.5) == pytest.approx(-4 / 3)
    with pytest.raises(ValueError):
        empirical_cvar(np.array([1, 2]), np.ones(2), 0.9)


def test_hand_calculated_pnl_fees_and_financing_counted_once():
    config = config_fixture()
    config.update(position_usd=10000, budget_bps=201, fee_per_contract_usd=1,
                  financing_rate_annual=0.1)
    prices, cash = market_panels(market_fixture())
    prices.loc[pd.Timestamp("2024-11-01"), "LQD"] = 90
    cash.loc[pd.Timestamp("2024-11-01"), "LQD"] = 1
    scenarios = historical_scenarios(prices, cash, pd.Timestamp("2024-10-01"), pd.Timestamp("2024-11-01"), 5)
    tables = evaluate(config, contract_fixture(), scenarios, prices, cash)
    direct = tables["realized_accounting"].set_index("strategy").loc["direct__no_cap"]
    assert direct.portfolio_shares == 100
    assert direct.portfolio_price_pnl_usd == pytest.approx(-1000)
    assert direct.portfolio_cash_pnl_usd == 100
    assert direct.option_payoff_usd == 1000
    assert direct.premium_usd == 200
    assert direct.fees_usd == 1
    assert direct.financing_only_usd == pytest.approx(201 * 0.1 * 31 / 365)
    assert direct.net_loss_usd == pytest.approx(-100 + 201 * (1 + 0.1 * 31 / 365))
    no_hedge = tables["realized_accounting"].set_index("strategy").loc["unhedged"]
    assert no_hedge.net_loss_usd == pytest.approx(900)
    assert tables["solutions"].spent_usd.le(201 + 1e-8).all()
    assert tables["losses"].groupby("strategy").scenario_id.nunique().eq(len(scenarios)).all()
    leg_budgets = tables["positions"].query("strategy == 'combined_equal_budget__no_cap'").allocated_budget_usd
    assert leg_budgets.eq(67).all()


@pytest.fixture
def pilot_root(tmp_path):
    config = config_fixture()
    for folder in ("data/manifests", "data/processed/options_screen",
                   "data/raw/hedge_design", "src/data", "scripts"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    frame = market_fixture()
    market_path = tmp_path / "data/raw/hedge_design/synthetic.csv"
    frame.to_csv(market_path, index=False)
    contract_fixture().to_csv(tmp_path / CHAIN_PATH, index=False)
    prices, _ = market_panels(frame)
    prices.rename_axis("Date").to_csv(tmp_path / PRICE_PATH)
    config["pinned_inputs"] = {name: sha256_file(tmp_path / name) for name in (CHAIN_PATH, PRICE_PATH)}
    (tmp_path / config["market_manifest"]).write_text(json.dumps({
        "path": market_path.relative_to(tmp_path).as_posix(), "sha256": sha256_file(market_path)}))
    (tmp_path / config["input_audit"]).write_text("{}")
    (tmp_path / "study_config.json").write_text(json.dumps(config))
    shutil.copytree(ROOT / "src/hedge_design", tmp_path / "src/hedge_design", ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("src/data/hedge_inputs.py", "scripts/run_hedge_design.py", "scripts/fetch_hedge_market.py"):
        shutil.copy2(ROOT / name, tmp_path / name)
    return tmp_path


def test_offline_run_is_reproducible_and_refuses_overwrite(pilot_root):
    config = pilot_root / "study_config.json"
    first = run_pilot(pilot_root, config, "first")
    second = run_pilot(pilot_root, config, "second")
    assert json.loads((first / "manifest.json").read_text())["phase3"] is None
    for path in first.glob("*.csv"):
        assert path.read_bytes() == (second / path.name).read_bytes()
    verify_run(pilot_root, "first")
    with pytest.raises(FileExistsError):
        run_pilot(pilot_root, config, "first")
    with (first / "positions.csv").open("a") as stream:
        stream.write("tamper")
    with pytest.raises(ValueError, match="Changed outputs"):
        verify_run(pilot_root, "first")


def test_input_changes_rejected_before_run_output(pilot_root):
    with (pilot_root / CHAIN_PATH).open("a") as stream:
        stream.write("\n")
    with pytest.raises(ValueError, match="Pinned input changed"):
        run_pilot(pilot_root, pilot_root / "study_config.json", "bad")
    assert not (pilot_root / "results/hedge_design/bad").exists()


def test_date_selection_cannot_be_changed_silently(pilot_root):
    path = pilot_root / "study_config.json"
    config = json.loads(path.read_text())
    config["decision_date"] = "2024-09-30"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="latest all-menu"):
        run_pilot(pilot_root, path, "bad")


def test_terms_cannot_be_silently_promoted_to_verified(tmp_path):
    config = config_fixture()
    config["contract_terms"]["status"] = "verified"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="explicitly assumed"):
        load_config(path)


@pytest.mark.parametrize("enabled", [True, False])
def test_robust_switch_preserves_settings(tmp_path, enabled):
    config = config_fixture()
    config["robust_enabled"] = enabled
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    assert load_config(path) == config


@pytest.mark.parametrize("enabled", ["false", 0, None])
def test_robust_switch_rejects_non_booleans(tmp_path, enabled):
    config = config_fixture()
    config["robust_enabled"] = enabled
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="must be a boolean"):
        load_config(path)


def test_enabled_robust_requires_settings(tmp_path):
    config = config_fixture()
    config["robust_enabled"] = True
    del config["robust"]
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="requires robust settings"):
        load_config(path)
