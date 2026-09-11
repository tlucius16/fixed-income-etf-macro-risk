"""Pinned-input accounting, nominal frontiers and optional finite-model experiments."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

from src.data.hedge_inputs import (
    CHAIN_PATH, PRICE_PATH, load_chains, load_prices, pilot_coverage, quote_flags, sha256_file,
)
from src.hedge_design.benchmarks import (
    RATE_FACTOR, benchmark_vs_optimizer, duration_hedge_benchmark,
)
from src.hedge_design.market import (
    adjustment_diagnostic, historical_scenarios, holding_return, load_market, market_panels,
)
from src.hedge_design.optimize import empirical_cvar, empirical_var, nominal_cvar_lp

TERMS_STATUS = "assumed_standard_not_contract_verified"
MENUS = {"direct": ["LQD"], "tlt": ["TLT"], "ief": ["IEF"],
         "treasury_equal_budget": ["TLT", "IEF"],
         "combined_equal_budget": ["LQD", "TLT", "IEF"]}
# Optimizer menus: the LP chooses quantities across every eligible strike, so
# these are ticker sets rather than the fixed one-contract benchmark baskets.
FRONTIER_MENUS = {"direct": ["LQD"], "treasury_substitute": ["TLT", "IEF"],
                  "combined": ["LQD", "TLT", "IEF"]}
QUANTITY_FLOOR = 1e-9
INVARIANT_TOL_USD = 10.0


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text())
    if config["schema_version"] != 1 or config["portfolio"] != "LQD":
        raise ValueError("This pilot supports schema 1 and a fixed LQD portfolio only")
    if config["tickers"] != ["LQD", "TLT", "IEF"]:
        raise ValueError("Pilot ticker order is LQD, TLT, IEF")
    terms = config["contract_terms"]
    if terms != {"status": TERMS_STATUS, "multiplier": 100, "deliverable_shares": 100,
                 "exercise": "American_held_to_expiration",
                 "settlement": "physical_delivery_economic_intrinsic_equivalent",
                 "source": "https://www.theocc.com/clearance-and-settlement/clearing/etf-options"}:
        raise ValueError("Only explicitly assumed standard contracts are supported")
    for key in ("position_usd", "budget_bps", "fee_per_contract_usd", "financing_rate_annual",
                "max_spot_relative_gap", "max_adjustment_gap_bps"):
        if not np.isfinite(config[key]) or config[key] < 0:
            raise ValueError(f"Invalid nonnegative parameter: {key}")
    if config["position_usd"] == 0:
        raise ValueError("Position must be positive")
    if type(config["lookback_years"]) is not int or config["lookback_years"] < 1:
        raise ValueError("Lookback must be a positive integer")
    if (not config["tail_levels"] or len(set(config["tail_levels"])) != len(config["tail_levels"])
            or any(not 0 < a < 1 for a in config["tail_levels"])):
        raise ValueError("Tail levels must be unique and strictly between zero and one")
    if (not config["oi_fractions"] or len(set(config["oi_fractions"])) != len(config["oi_fractions"])
            or any(x is not None and not 0 < x <= 1 for x in config["oi_fractions"])):
        raise ValueError("OI fractions must be unique positive fractions or null")
    if config["financing_convention"] != "simple_actual_365_assumed_not_estimated":
        raise ValueError("Unsupported financing convention")
    if config["date_selection"] != "latest_snapshot_with_all_three_quote_menus_under_audit_union_rule":
        raise ValueError("Unsupported date-selection rule")
    if pd.Timestamp(config["expiration"]) <= pd.Timestamp(config["decision_date"]):
        raise ValueError("Expiration must follow decision")
    if set(config["pinned_inputs"]) != {CHAIN_PATH, PRICE_PATH}:
        raise ValueError("Pin both existing chain and price inputs")
    budgets = config["frontier_budgets_bps"]
    if (not isinstance(budgets, list) or len(set(budgets)) != len(budgets) or 0 not in budgets
            or any(isinstance(b, bool) or not isinstance(b, (int, float)) or not 0 <= b < 1e5
                   for b in budgets)):
        raise ValueError("frontier_budgets_bps must be unique bps in [0, 1e5) and include 0")
    multipliers = config["scale_control_multipliers"]
    if (not isinstance(multipliers, list) or not multipliers or 1 not in multipliers
            or any(not np.isfinite(m) or m <= 0 for m in multipliers)):
        raise ValueError("scale_control_multipliers must be positive and include 1")
    optimizer = config["optimizer"]
    if (optimizer.get("method") != "highs"
            or optimizer.get("formulation") != "rockafellar_uryasev_cvar_lp"
            or not np.isfinite(optimizer["dollar_scale"]) or optimizer["dollar_scale"] <= 0
            or not np.isfinite(optimizer["feasibility_tol_usd"]) or optimizer["feasibility_tol_usd"] < 0
            or not 0 < optimizer["cvar_recompute_rtol"] < 1):
        raise ValueError("Unsupported optimizer configuration")
    held_out = config["held_out"]
    if (held_out["budget_bps"] not in config["frontier_budgets_bps"] or held_out["budget_bps"] == 0
            or held_out["tail_level"] not in config["tail_levels"]
            or held_out["oi_cap"] not in config["oi_fractions"] or held_out["oi_cap"] is None
            or not isinstance(held_out["require_all_menus"], bool)):
        raise ValueError("held_out must reference a nonzero frontier budget, a configured tail "
                         "level, and a configured non-null OI fraction")
    robust_enabled = config.get("robust_enabled", "robust" in config)
    if not isinstance(robust_enabled, bool):
        raise ValueError("robust_enabled must be a boolean")
    if robust_enabled and "robust" not in config:
        raise ValueError("Robust analysis requires robust settings")
    if "robust" in config:
        from src.hedge_design.phase3 import validate_robust_config
        validate_robust_config(config["robust"])
    return config


def selected_contracts(chains: pd.DataFrame, decision: pd.Timestamp,
                       expiry: pd.Timestamp, tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = chains.loc[chains.snap_date.eq(decision) & chains.expiry.eq(expiry)
                            & chains.ticker.isin(tickers) & chains.right.eq("P")].copy()
    for column in ("strike", "underlying", "bid", "ask", "open_interest"):
        candidates[column] = pd.to_numeric(candidates[column], errors="coerce")
    flags = quote_flags(candidates)
    diagnostics = pd.concat([candidates, flags], axis=1)
    eligible = candidates.loc[flags.quote_eligible].copy()
    eligible["atm_distance"] = (eligible.strike / eligible.underlying - 1).abs()
    # Same deterministic nearest-ATM contract across OI sensitivities; no outcome-based ranking.
    chosen = eligible.sort_values(["ticker", "atm_distance", "strike"]).groupby("ticker").head(1)
    if set(chosen.ticker) != set(tickers):
        raise ValueError("Selected pilot does not have all three quote menus")
    diagnostics["selected"] = diagnostics.index.isin(chosen.index)
    chosen["terms_status"] = TERMS_STATUS
    return chosen.reset_index(drop=True), diagnostics.reset_index(drop=True)


def put_payoff(strike: float, terminal_price: np.ndarray | float, multiplier: float) -> np.ndarray:
    values = np.asarray(terminal_price, dtype=float)
    if (not np.isfinite(values).all() or (values < 0).any()
            or not np.isfinite(strike) or strike <= 0 or not np.isfinite(multiplier) or multiplier <= 0):
        raise ValueError("Invalid put payoff inputs")
    return multiplier * np.maximum(strike - values, 0)


def budget_quantity(ask: float, multiplier: float, fee: float, allocation: float,
                    oi: float, oi_fraction: float | None) -> tuple[float, str]:
    if not all(np.isfinite(x) for x in (ask, multiplier, fee, allocation)):
        raise ValueError("Nonfinite sizing input")
    if ask <= 0 or multiplier <= 0 or fee < 0 or allocation < 0:
        raise ValueError("Invalid sizing input")
    quantity = allocation / (ask * multiplier + fee)
    if oi_fraction is None:
        return quantity, "uncapped_hypothetical"
    if not np.isfinite(oi_fraction) or not 0 < oi_fraction <= 1:
        raise ValueError("Invalid OI fraction")
    if not np.isfinite(oi) or oi < 0 or oi % 1 != 0:
        return 0.0, "unavailable_oi"
    capped = min(quantity, oi_fraction * oi)
    return capped, "oi_binding" if capped < quantity else "budget_binding"


def evaluate(config: dict, contracts: pd.DataFrame, scenarios: pd.DataFrame,
             prices: pd.DataFrame, cash: pd.DataFrame) -> dict[str, pd.DataFrame]:
    decision, expiry = pd.Timestamp(config["decision_date"]), pd.Timestamp(config["expiration"])
    position, multiplier = config["position_usd"], config["contract_terms"]["multiplier"]
    fee, budget = config["fee_per_contract_usd"], position * config["budget_bps"] / 10000
    financing_factor = 1 + config["financing_rate_annual"] * (expiry - decision).days / 365
    portfolio = config["portfolio"]
    scenario_pnl = position * (scenarios[f"{portfolio}_price_return"].to_numpy()
                              + scenarios[f"{portfolio}_cash_return"].to_numpy())
    realized_pr, realized_cr = holding_return(prices, cash, decision, expiry)
    actual_price_pnl = position * realized_pr[portfolio]
    actual_cash_pnl = position * realized_cr[portfolio]
    contracts = contracts.set_index("ticker")
    strategies = [("unhedged", [], None)] + [
        (f"{name}__{'no_cap' if cap is None else f'oi_{cap:g}'}", tickers, cap)
        for name, tickers in MENUS.items() for cap in config["oi_fractions"]]
    positions, summaries, losses, accounting = [], [], [], []
    for name, tickers, cap in strategies:
        scenario_payoff = np.zeros(len(scenarios))
        actual_payoff, upfront, premium, fees = 0.0, 0.0, 0.0, 0.0
        unavailable = 0
        for ticker in tickers:
            contract = contracts.loc[ticker]
            quantity, status = budget_quantity(contract.ask, multiplier, fee, budget / len(tickers),
                                               contract.open_interest, cap)
            unavailable += status == "unavailable_oi"
            premium_i, fees_i = quantity * multiplier * contract.ask, quantity * fee
            scenario_terminal = prices.loc[decision, ticker] * (1 + scenarios[f"{ticker}_price_return"].to_numpy())
            unit_actual = float(put_payoff(contract.strike, prices.loc[expiry, ticker], multiplier))
            scenario_payoff += quantity * put_payoff(contract.strike, scenario_terminal, multiplier)
            actual_payoff += quantity * unit_actual
            upfront += premium_i + fees_i
            premium += premium_i
            fees += fees_i
            positions.append({"strategy": name, "ticker": ticker, "expiry": expiry,
                "strike": contract.strike, "bid": contract.bid, "ask": contract.ask,
                "strike_spot_ratio": contract.strike / prices.loc[decision, ticker],
                "relative_spread": (contract.ask - contract.bid) / ((contract.ask + contract.bid) / 2),
                "entry_spot": prices.loc[decision, ticker], "expiry_spot": prices.loc[expiry, ticker],
                "multiplier": multiplier, "contracts": quantity, "open_interest": contract.open_interest,
                "oi_fraction": cap, "sizing_status": status, "terms_status": TERMS_STATUS,
                "allocated_budget_usd": budget / len(tickers), "premium_usd": premium_i,
                "fees_usd": fees_i, "unit_intrinsic_usd": unit_actual,
                "realized_payoff_usd": quantity * unit_actual})
        cost = upfront * financing_factor
        net_losses = -scenario_pnl - scenario_payoff + cost
        actual_loss = -actual_price_pnl - actual_cash_pnl - actual_payoff + cost
        summary = {"strategy": name, "status": "partial_or_unavailable_oi" if unavailable else "conditional",
                   "budget_usd": budget, "spent_usd": upfront, "unspent_usd": budget - upfront,
                   "financed_cost_usd": cost, "mean_scenario_loss_usd": float(net_losses.mean()),
                   "worst_scenario_loss_usd": float(net_losses.max()),
                   "realized_loss_usd": actual_loss, "realized_loss_bps": actual_loss / position * 10000}
        for alpha in config["tail_levels"]:
            summary[f"historical_cvar_{alpha:g}_usd"] = empirical_cvar(net_losses, scenarios.weight.to_numpy(), alpha)
        summaries.append(summary)
        losses.append(pd.DataFrame({"strategy": name, "scenario_id": scenarios.scenario_id,
            "weight": scenarios.weight, "portfolio_pnl_usd": scenario_pnl,
            "option_payoff_usd": scenario_payoff, "financed_cost_usd": cost, "net_loss_usd": net_losses}))
        accounting.append({"strategy": name, "portfolio_shares": position / prices.loc[decision, portfolio],
            "entry_price": prices.loc[decision, portfolio], "expiry_price": prices.loc[expiry, portfolio],
            "cash_per_share": actual_cash_pnl / (position / prices.loc[decision, portfolio]),
            "portfolio_price_pnl_usd": actual_price_pnl, "portfolio_cash_pnl_usd": actual_cash_pnl,
            "option_payoff_usd": actual_payoff, "premium_usd": premium, "fees_usd": fees,
            "financing_only_usd": cost - upfront, "net_loss_usd": actual_loss})
    return {"positions": pd.DataFrame(positions), "solutions": pd.DataFrame(summaries),
            "losses": pd.concat(losses, ignore_index=True), "realized_accounting": pd.DataFrame(accounting)}


def candidate_puts(chains: pd.DataFrame, decision: pd.Timestamp, expiry: pd.Timestamp,
                   tickers: list[str]) -> pd.DataFrame:
    """Every quote-eligible put at the single common expiration for a menu's tickers.

    Eligibility is the audit's quote screen only (finite positive spot/strike/bid/ask,
    non-crossed, relative spread <= 35%). No Greek floor, moneyness band, or OI
    requirement is applied; the optimizer chooses quantities across the surviving strikes.
    """
    frame = chains.loc[chains.snap_date.eq(decision) & chains.expiry.eq(expiry)
                       & chains.ticker.isin(tickers) & chains.right.eq("P")].copy()
    for column in ("strike", "underlying", "bid", "ask", "open_interest"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.loc[quote_flags(frame)["quote_eligible"]]
    columns = ["ticker", "strike", "underlying", "bid", "ask", "open_interest"]
    return frame[columns].sort_values(["ticker", "strike"]).reset_index(drop=True)


def validate_candidate_spots(candidates: pd.DataFrame, entry_spot: pd.Series, tolerance: float) -> None:
    if candidates.empty:
        return
    reference = entry_spot.reindex(candidates["ticker"]).to_numpy(float)
    gaps = np.abs(candidates["underlying"].to_numpy(float) / reference - 1)
    if not np.isfinite(gaps).all() or (gaps > tolerance).any():
        raise ValueError("Chain/price spot mismatch in eligible candidate menu")


def require_verified_solution(solution: dict) -> None:
    if (solution["status"] not in {"optimal", "empty_menu", "zero_budget", "no_available_contracts"}
            or not solution["verified"] or solution["x"] is None):
        raise ValueError(f"Optimization failed verification: {solution['status']}")


def _oi_upper_bound(candidates: pd.DataFrame, oi_fraction: float | None) -> np.ndarray:
    """Per-contract quantity ceiling: unbounded when no cap, else a fraction of recorded OI.

    Missing, negative, fractional, or non-finite OI makes a capped contract unavailable
    (ceiling zero) rather than silently unconstrained. OI is a sensitivity input, not
    a statement of executable depth.
    """
    if oi_fraction is None:
        return np.full(len(candidates), np.inf)
    oi = pd.to_numeric(candidates["open_interest"], errors="coerce").to_numpy(float)
    usable = np.isfinite(oi) & (oi >= 0) & (np.mod(oi, 1.0) == 0.0)
    return np.where(usable, oi_fraction * np.where(usable, oi, 0.0), 0.0)


def _scenario_payoffs(candidates: pd.DataFrame, scenarios: pd.DataFrame,
                      entry_spot: pd.Series, multiplier: float) -> np.ndarray:
    """(S, J) per-contract terminal put payoff: historical price returns scaled to entry spot."""
    if candidates.empty:
        return np.zeros((len(scenarios), 0))
    return np.column_stack([
        put_payoff(row.strike,
                   float(entry_spot[row.ticker]) * (1.0 + scenarios[f"{row.ticker}_price_return"].to_numpy()),
                   multiplier)
        for row in candidates.itertuples()])


def _menu_contracts_table(menu_data: dict, entry_spot: pd.Series) -> pd.DataFrame:
    rows = []
    for menu, data in menu_data.items():
        candidates = data["candidates"]
        for j, contract in enumerate(candidates.itertuples()):
            oi = contract.open_interest
            state = ("missing" if pd.isna(oi) else "zero" if oi == 0
                     else "positive" if np.isfinite(oi) and oi >= 0 and float(oi).is_integer()
                     else "invalid")
            rows.append({"menu": menu, "ticker": contract.ticker, "strike": contract.strike,
                         "entry_spot": float(entry_spot[contract.ticker]),
                         "strike_spot_ratio": contract.strike / float(entry_spot[contract.ticker]),
                         "bid": contract.bid, "ask": contract.ask,
                         "upfront_cost_usd": float(data["c0"][j]), "open_interest": oi,
                         "oi_state": state})
    return pd.DataFrame(rows, columns=["menu", "ticker", "strike", "entry_spot",
                                       "strike_spot_ratio", "bid", "ask", "upfront_cost_usd",
                                       "open_interest", "oi_state"])


def _monotone_invariants(frontier: pd.DataFrame, oi_fractions: list) -> pd.DataFrame:
    """Numerical checks of LP-theoretic facts: relaxing a constraint cannot raise CVaR.

    Larger budgets, looser OI caps (with the uncapped case loosest), and the union
    menu each enlarge the feasible set, so none can raise the minimised CVaR.
    """
    checks = []
    frontier = frontier.assign(_oi=frontier["oi_fraction"].map(
        lambda c: "no_cap" if pd.isna(c) else f"{c:g}"))

    for (menu, alpha, cap), group in frontier.groupby(["menu", "tail_level", "_oi"]):
        diffs = np.diff(group.sort_values("budget_bps")["cvar_usd"].to_numpy())
        worst = float(diffs.max()) if diffs.size else 0.0
        checks.append({"invariant": "cvar_nonincreasing_in_budget", "detail": f"{menu}/{alpha}/{cap}",
                       "max_increase_usd": max(worst, 0.0), "ok": worst <= INVARIANT_TOL_USD})

    loosening = [f"{c:g}" for c in sorted(c for c in oi_fractions if c is not None)]
    if None in oi_fractions:
        loosening.append("no_cap")
    for (menu, alpha, bps), group in frontier.groupby(["menu", "tail_level", "budget_bps"]):
        series = group.set_index("_oi")["cvar_usd"].reindex(loosening).dropna()
        diffs = np.diff(series.to_numpy())
        worst = float(diffs.max()) if diffs.size else 0.0
        checks.append({"invariant": "cvar_nonincreasing_as_oi_cap_loosens",
                       "detail": f"{menu}/{alpha}/{bps}bps",
                       "max_increase_usd": max(worst, 0.0), "ok": worst <= INVARIANT_TOL_USD})

    wide = frontier.pivot_table(index=["tail_level", "budget_bps", "_oi"], columns="menu",
                                values="cvar_usd")
    for narrower in ("direct", "treasury_substitute"):
        if "combined" in wide and narrower in wide:
            gap = (wide["combined"] - wide[narrower]).dropna()
            worst = float(gap.max()) if len(gap) else 0.0
            checks.append({"invariant": f"combined_not_worse_than_{narrower}", "detail": "all cells",
                           "max_increase_usd": max(worst, 0.0), "ok": worst <= INVARIANT_TOL_USD})
    return pd.DataFrame(checks)


def run_frontier(config: dict, chains: pd.DataFrame, scenarios: pd.DataFrame,
                 prices: pd.DataFrame, cash: pd.DataFrame, decision: pd.Timestamp,
                 expiry: pd.Timestamp, *, portfolio: str | None = None,
                 menus: dict[str, list[str]] | None = None) -> tuple[dict[str, pd.DataFrame], dict]:
    """Nominal CVaR frontier: for every menu, budget, OI cap, and tail level, minimise
    modeled CVaR of net dollar loss over continuous long-put quantities at the common
    expiration. Objectives are recomputed independently from the solver's positions.

    ``portfolio`` and ``menus`` default to the config portfolio and ``FRONTIER_MENUS``;
    the TLT-held positive control passes ``portfolio="TLT"`` with a TLT-only menu.
    """
    portfolio = portfolio or config["portfolio"]
    menus = menus or FRONTIER_MENUS
    position = float(config["position_usd"])
    multiplier = float(config["contract_terms"]["multiplier"])
    fee = float(config["fee_per_contract_usd"])
    financing_factor = 1.0 + config["financing_rate_annual"] * (expiry - decision).days / 365
    optimizer = config["optimizer"]
    solve_kwargs = {"dollar_scale": optimizer["dollar_scale"],
                    "feasibility_tol_usd": optimizer["feasibility_tol_usd"],
                    "recompute_rtol": optimizer["cvar_recompute_rtol"],
                    "quantity_floor": QUANTITY_FLOOR}

    entry_spot = prices.loc[decision]
    weights = scenarios["weight"].to_numpy()
    losses = -position * (scenarios[f"{portfolio}_price_return"].to_numpy()
                          + scenarios[f"{portfolio}_cash_return"].to_numpy())
    realized_pr, realized_cr = holding_return(prices, cash, decision, expiry)
    realized_portfolio_loss = -position * (realized_pr[portfolio] + realized_cr[portfolio])
    unhedged_cvar = {alpha: empirical_cvar(losses, weights, alpha) for alpha in config["tail_levels"]}

    menu_data = {}
    for menu, tickers in menus.items():
        candidates = candidate_puts(chains, decision, expiry, tickers)
        validate_candidate_spots(candidates, entry_spot, config["max_spot_relative_gap"])
        payoffs = _scenario_payoffs(candidates, scenarios, entry_spot, multiplier)
        c0 = (multiplier * candidates["ask"].to_numpy() + fee) if not candidates.empty else np.zeros(0)
        realized_unit = np.array([put_payoff(row.strike, float(prices.loc[expiry, row.ticker]), multiplier)
                                  for row in candidates.itertuples()]) if not candidates.empty else np.zeros(0)
        strike_spot = ((candidates["strike"].to_numpy() / entry_spot[candidates["ticker"]].to_numpy())
                       if not candidates.empty else np.zeros(0))
        menu_data[menu] = {"candidates": candidates, "payoffs": payoffs, "c0": c0,
                           "cH": c0 * financing_factor, "realized_unit": realized_unit,
                           "strike_spot": strike_spot}

    frontier_rows, position_rows = [], []
    for menu, data in menu_data.items():
        candidates, strike_spot = data["candidates"], data["strike_spot"]
        for alpha in config["tail_levels"]:
            for bps in config["frontier_budgets_bps"]:
                budget = position * bps / 10000.0
                for cap in config["oi_fractions"]:
                    upper = _oi_upper_bound(candidates, cap)
                    solution = nominal_cvar_lp(losses, data["payoffs"], data["c0"], data["cH"],
                                               weights, alpha, budget, upper, **solve_kwargs)
                    require_verified_solution(solution)
                    x = solution["x"]
                    chosen = x > QUANTITY_FLOOR
                    notional = x * multiplier * (candidates["strike"].to_numpy()
                                                 if len(candidates) else np.zeros(0))
                    weighted_moneyness = (float((notional * strike_spot).sum() / notional.sum())
                                          if notional.sum() > 0 else float("nan"))
                    realized_loss = (realized_portfolio_loss - float(data["realized_unit"] @ x)
                                     + float(data["cH"] @ x))
                    frontier_rows.append({
                        "menu": menu, "tail_level": alpha, "budget_bps": bps, "oi_fraction": cap,
                        "solver_status": solution["status"], "n_candidates": len(candidates),
                        "n_available": solution["n_available"], "n_contracts_selected": int(chosen.sum()),
                        "budget_usd": budget, "spent_usd": solution["spent_usd"],
                        "unspent_usd": (budget - solution["spent_usd"]
                                        if np.isfinite(solution["spent_usd"]) else float("nan")),
                        "var_eta_usd": solution["eta_usd"], "cvar_usd": solution["cvar_usd"],
                        "cvar_bps": solution["cvar_usd"] / position * 10000.0,
                        "unhedged_cvar_usd": unhedged_cvar[alpha],
                        "cvar_reduction_usd": unhedged_cvar[alpha] - solution["cvar_usd"],
                        "cvar_reduction_bps": (unhedged_cvar[alpha] - solution["cvar_usd"]) / position * 10000.0,
                        "lp_objective_usd": solution["lp_objective_usd"],
                        "cvar_abs_error_usd": solution["cvar_abs_error_usd"],
                        "budget_violation_usd": solution["budget_violation_usd"],
                        "bound_violation_contracts": solution["bound_violation_contracts"],
                        "budget_shadow_price": solution["budget_shadow_price"],
                        "weighted_strike_spot": weighted_moneyness,
                        "min_selected_strike_spot": float(strike_spot[chosen].min()) if chosen.any() else float("nan"),
                        "max_selected_strike_spot": float(strike_spot[chosen].max()) if chosen.any() else float("nan"),
                        "realized_net_loss_usd": realized_loss,
                        "realized_net_loss_bps": realized_loss / position * 10000.0,
                        "verified": solution["verified"]})
                    for j in np.flatnonzero(chosen):
                        contract = candidates.iloc[j]
                        bound = upper[j]
                        position_rows.append({
                            "menu": menu, "tail_level": alpha, "budget_bps": bps, "oi_fraction": cap,
                            "ticker": contract["ticker"], "strike": contract["strike"],
                            "entry_spot": float(entry_spot[contract["ticker"]]),
                            "strike_spot_ratio": contract["strike"] / float(entry_spot[contract["ticker"]]),
                            "bid": contract["bid"], "ask": contract["ask"],
                            "open_interest": contract["open_interest"],
                            "upper_bound_contracts": (float(bound) if np.isfinite(bound) else None),
                            "contracts": float(x[j]),
                            "premium_usd": float(x[j] * multiplier * contract["ask"]),
                            "fees_usd": float(x[j] * fee),
                            "financed_cost_usd": float(x[j] * data["cH"][j])})

    frontier = pd.DataFrame(frontier_rows)
    invariants = _monotone_invariants(frontier, config["oi_fractions"])

    control_rows = []
    reference_menu, reference_alpha = list(menus)[-1], config["tail_levels"][0]
    reference_bps = max(b for b in config["frontier_budgets_bps"] if b > 0)
    reference = menu_data[reference_menu]
    uncapped = np.full(len(reference["candidates"]), np.inf)
    for multiple in config["scale_control_multipliers"]:
        scaled_position = position * multiple
        solution = nominal_cvar_lp(losses / position * scaled_position, reference["payoffs"],
                                   reference["c0"], reference["cH"], weights, reference_alpha,
                                   scaled_position * reference_bps / 10000.0, uncapped, **solve_kwargs)
        require_verified_solution(solution)
        control_rows.append({"multiplier": multiple, "position_usd": scaled_position,
                             "menu": reference_menu, "tail_level": reference_alpha,
                             "budget_bps": reference_bps, "cvar_usd": solution["cvar_usd"],
                             "cvar_bps": solution["cvar_usd"] / scaled_position * 10000.0,
                             "verified": solution["verified"]})
    scale_control = pd.DataFrame(control_rows)
    scale_invariant = bool(np.ptp(scale_control["cvar_bps"].to_numpy()) <= 1e-2)
    if not scale_invariant or not invariants["ok"].all():
        raise ValueError("Frontier invariant verification failed")

    tables = {"cvar_frontier": frontier,
              "cvar_positions": pd.DataFrame(position_rows, columns=[
                  "menu", "tail_level", "budget_bps", "oi_fraction", "ticker", "strike",
                  "entry_spot", "strike_spot_ratio", "bid", "ask", "open_interest",
                  "upper_bound_contracts", "contracts", "premium_usd", "fees_usd",
                  "financed_cost_usd"]),
              "cvar_invariants": invariants,
              "cvar_scale_control": scale_control,
              "cvar_menu_contracts": _menu_contracts_table(menu_data, entry_spot)}
    summary = {
        "portfolio": portfolio, "menus": list(menus), "budgets_bps": config["frontier_budgets_bps"],
        "oi_fractions": config["oi_fractions"],
        "solves": int(len(frontier)),
        "all_solves_ok": bool(frontier["solver_status"].isin(
            ["optimal", "empty_menu", "zero_budget", "no_available_contracts"]).all()),
        "all_objectives_verified": bool(frontier["verified"].all()),
        "monotonicity_invariants_hold": bool(invariants["ok"].all()),
        "percentage_frontier_scale_invariant_no_cap": scale_invariant}
    return tables, summary


# Held-out policies frozen at each decision date and evaluated at its expiration.
# "duration" = the past-data hedge-ratio TLT-put rule; "cvar" = the nominal LP.
HELD_OUT_POLICIES = [
    ("unhedged", "none", None, False),
    ("duration_hedge", "duration", None, False),
    ("duration_hedge_oi_capped", "duration", None, True),
    ("cvar_treasury_substitute", "cvar", "treasury_substitute", False),
    ("cvar_treasury_substitute_oi_capped", "cvar", "treasury_substitute", True),
    ("cvar_combined", "cvar", "combined", False),
]


def qualifying_dates(coverage: pd.DataFrame) -> pd.DataFrame:
    """One row per option snapshot: the union-rule expiration and menu availability."""
    rows = []
    for snap, group in coverage.groupby("snap_date"):
        by_ticker = group.set_index("ticker")
        counts = {t: int(by_ticker.loc[t, "quote_eligible_puts"]) if t in by_ticker.index else 0
                  for t in ("LQD", "TLT", "IEF")}
        rows.append({
            "decision_date": snap, "expiration": group["expiry"].iloc[0],
            "lqd_eligible_puts": counts["LQD"], "tlt_eligible_puts": counts["TLT"],
            "ief_eligible_puts": counts["IEF"],
            "all_menus_available": all(v > 0 for v in counts.values()),
            "treasury_menu_available": counts["TLT"] > 0 or counts["IEF"] > 0,
            "prices_present": bool(group["decision_price_present"].all()
                                   and group["expiry_price_present"].all())})
    return pd.DataFrame(rows).sort_values("decision_date").reset_index(drop=True)


def _cvar_realized_position(config: dict, chains: pd.DataFrame, scenarios: pd.DataFrame,
                            prices: pd.DataFrame, decision: pd.Timestamp, expiry: pd.Timestamp,
                            tickers: list[str], budget: float, tail: float,
                            oi_fraction: float | None) -> dict:
    multiplier = float(config["contract_terms"]["multiplier"])
    fee = float(config["fee_per_contract_usd"])
    financing_factor = 1.0 + config["financing_rate_annual"] * (expiry - decision).days / 365
    position = float(config["position_usd"])
    portfolio = config["portfolio"]
    candidates = candidate_puts(chains, decision, expiry, tickers)
    validate_candidate_spots(candidates, prices.loc[decision], config["max_spot_relative_gap"])
    payoffs = _scenario_payoffs(candidates, scenarios, prices.loc[decision], multiplier)
    c0 = (multiplier * candidates["ask"].to_numpy() + fee) if not candidates.empty else np.zeros(0)
    losses = -position * (scenarios[f"{portfolio}_price_return"].to_numpy()
                          + scenarios[f"{portfolio}_cash_return"].to_numpy())
    solution = nominal_cvar_lp(
        losses, payoffs, c0, c0 * financing_factor, scenarios["weight"].to_numpy(), tail, budget,
        _oi_upper_bound(candidates, oi_fraction), dollar_scale=config["optimizer"]["dollar_scale"],
        feasibility_tol_usd=config["optimizer"]["feasibility_tol_usd"],
        recompute_rtol=config["optimizer"]["cvar_recompute_rtol"], quantity_floor=QUANTITY_FLOOR)
    require_verified_solution(solution)
    x = solution["x"]
    realized_option = float(sum(
        x[j] * put_payoff(candidates.iloc[j]["strike"],
                          float(prices.loc[expiry, candidates.iloc[j]["ticker"]]), multiplier)
        for j in range(len(candidates))))
    financed = float((c0 * financing_factor) @ x)
    return {"design_cvar_usd": solution["cvar_usd"], "spent_usd": solution["spent_usd"],
            "financed_cost_usd": financed, "realized_option_payoff_usd": realized_option,
            "contracts": float(np.sum(x)), "n_strikes": int(np.sum(x > QUANTITY_FLOOR)),
            "verified": solution["verified"], "solver_status": solution["status"]}


def run_held_out(config: dict, chains: pd.DataFrame, scenarios_prices: pd.DataFrame,
                 scenarios_cash: pd.DataFrame,
                 coverage: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict]:
    """Freeze each policy at every qualifying snapshot using only pre-decision data,
    then record its single realized loss at that snapshot's expiration. The pooled
    result is a small matched held-out sample, not a CVaR estimate or a backtest.
    """
    settings = config["held_out"]
    budget = float(config["position_usd"]) * settings["budget_bps"] / 10000.0
    tail, cap = settings["tail_level"], settings["oi_cap"]
    position = float(config["position_usd"])
    portfolio = config["portfolio"]
    multiplier = float(config["contract_terms"]["multiplier"])
    dates = qualifying_dates(coverage)

    outcomes = []
    for row in dates.itertuples():
        decision, expiry = pd.Timestamp(row.decision_date), pd.Timestamp(row.expiration)
        base = {"decision_date": row.decision_date, "expiration": row.expiration,
                "all_menus_available": row.all_menus_available}
        if not (row.prices_present and (row.all_menus_available or not settings["require_all_menus"])):
            for name, *_ in HELD_OUT_POLICIES:
                outcomes.append({**base, "policy": name, "evaluable": False,
                                 "reason": "menu_or_price_unavailable"})
            continue
        try:
            scenarios = historical_scenarios(scenarios_prices, scenarios_cash, decision, expiry,
                                             config["lookback_years"])
        except ValueError as exc:
            for name, *_ in HELD_OUT_POLICIES:
                outcomes.append({**base, "policy": name, "evaluable": False, "reason": str(exc)})
            continue
        realized_pr, realized_cr = holding_return(scenarios_prices, scenarios_cash, decision, expiry)
        validate_candidate_spots(candidate_puts(chains, decision, expiry, config["tickers"]),
                                 scenarios_prices.loc[decision], config["max_spot_relative_gap"])
        portfolio_loss = -position * (realized_pr[portfolio] + realized_cr[portfolio])
        portfolio_return = realized_pr[portfolio] + realized_cr[portfolio]
        try:
            tlt_selected, _ = selected_contracts(chains, decision, expiry, [RATE_FACTOR])
            duration_table, duration_meta = duration_hedge_benchmark(
                config, tlt_selected.iloc[0], scenarios, scenarios_prices, scenarios_cash,
                decision, expiry, portfolio=portfolio)
        except (ValueError, IndexError):
            duration_table, duration_meta = None, {}

        for name, kind, menu, capped in HELD_OUT_POLICIES:
            record = {**base, "policy": name, "evaluable": True, "reason": "",
                      "portfolio_return_pct": portfolio_return * 100.0,
                      "scenario_count": len(scenarios),
                      "training_end": str(scenarios["window_end"].max().date())}
            if kind == "none":
                record.update(realized_net_loss_usd=portfolio_loss, spent_usd=0.0,
                              design_cvar_bps=empirical_cvar(
                                  -position * (scenarios[f"{portfolio}_price_return"].to_numpy()
                                               + scenarios[f"{portfolio}_cash_return"].to_numpy()),
                                  scenarios["weight"].to_numpy(), tail) / position * 10000.0,
                              contracts=0.0, verified=True)
            elif kind == "duration":
                if duration_table is None:
                    record.update(evaluable=False, reason="no_tlt_contract")
                    outcomes.append(record)
                    continue
                mask = ((duration_table["tail_level"] == tail)
                        & (duration_table["budget_bps"] == settings["budget_bps"])
                        & (duration_table["oi_fraction"].isna() if not capped
                           else duration_table["oi_fraction"] == cap))
                cell = duration_table.loc[mask].iloc[0]
                record.update(realized_net_loss_usd=cell["realized_net_loss_usd"],
                              spent_usd=cell["spent_usd"], design_cvar_bps=cell["cvar_bps"],
                              contracts=cell["contracts"], hedge_ratio_beta=duration_meta["hedge_ratio_beta"],
                              binding_constraint=cell["binding_constraint"], verified=True)
            else:
                sized = _cvar_realized_position(config, chains, scenarios, scenarios_prices,
                                                decision, expiry, FRONTIER_MENUS[menu], budget, tail,
                                                cap if capped else None)
                realized = (portfolio_loss - sized["realized_option_payoff_usd"]
                            + sized["financed_cost_usd"])
                record.update(realized_net_loss_usd=realized, spent_usd=sized["spent_usd"],
                              design_cvar_bps=sized["design_cvar_usd"] / position * 10000.0,
                              contracts=sized["contracts"], n_strikes=sized["n_strikes"],
                              verified=sized["verified"], solver_status=sized["solver_status"])
            record["realized_net_loss_bps"] = record["realized_net_loss_usd"] / position * 10000.0
            record["spent_bps"] = record["spent_usd"] / position * 10000.0
            outcomes.append(record)

    outcomes = pd.DataFrame(outcomes)
    evaluable = outcomes[outcomes["evaluable"]].copy()
    successful = evaluable[evaluable["verified"].eq(True)]
    common_dates = successful.groupby("decision_date")["policy"].nunique()
    common_dates = common_dates.index[common_dates.eq(len(HELD_OUT_POLICIES))]
    outcomes["matched"] = outcomes["decision_date"].isin(common_dates)
    dates["matched"] = dates["decision_date"].isin(common_dates)
    matched = successful[successful["decision_date"].isin(common_dates)]
    unhedged_by_date = matched.loc[matched["policy"] == "unhedged"].set_index("decision_date")["realized_net_loss_bps"]

    summary_rows = []
    for name, *_ in HELD_OUT_POLICIES:
        policy = matched[matched["policy"] == name]
        if policy.empty:
            continue
        losses_bps = policy["realized_net_loss_bps"].to_numpy()
        helped = policy.set_index("decision_date")["realized_net_loss_bps"].lt(
            unhedged_by_date.reindex(policy["decision_date"]).to_numpy() - 1e-9).sum()
        summary_rows.append({
            "policy": name, "matched_dates": len(policy),
            "mean_realized_loss_bps": float(np.mean(losses_bps)),
            "median_realized_loss_bps": float(np.median(losses_bps)),
            "worst_realized_loss_bps": float(np.max(losses_bps)),
            "best_realized_loss_bps": float(np.min(losses_bps)),
            "pooled_p90_realized_loss_bps_exploratory": float(np.quantile(losses_bps, 0.90)),
            "mean_spent_bps": float(policy["spent_bps"].mean()),
            "dates_better_than_unhedged": int(helped)})
    summary = pd.DataFrame(summary_rows)

    meta = {
        "budget_bps": settings["budget_bps"], "tail_level": tail, "oi_cap": cap,
        "snapshots_total": int(len(dates)),
        "matched_decision_dates": int(matched["decision_date"].nunique()),
        "matched_date_list": sorted(matched["decision_date"].unique().tolist()),
        "excluded_snapshots": sorted(dates.loc[~dates["decision_date"].isin(common_dates), "decision_date"].tolist()),
        "all_frozen_positions_verified": bool(evaluable["verified"].all()),
        "note": "one realized outcome per date; the pooled percentile is exploratory, not a CVaR "
                "estimate; dates cluster by rate regime and are not independent draws"}
    return {"held_out_outcomes": outcomes, "held_out_summary": summary,
            "held_out_dates": dates}, meta


def run_pilot(root: Path, config_path: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", run_id):
        raise ValueError("Use a simple run ID, not a path")
    destination = root / "results/hedge_design" / run_id
    if destination.exists():
        raise FileExistsError(f"Run already exists: {destination}; use --verify or a new ID")
    config = load_config(config_path)
    market_manifest_path = root / config["market_manifest"]
    market_manifest = json.loads(market_manifest_path.read_text())
    expected = dict(config["pinned_inputs"])
    expected[market_manifest["path"]] = market_manifest["sha256"]
    for name, digest in expected.items():
        if sha256_file(root / name) != digest:
            raise ValueError(f"Pinned input changed: {name}")
    sources = {**expected, config_path.relative_to(root).as_posix(): sha256_file(config_path),
               config["input_audit"]: sha256_file(root / config["input_audit"]),
               config["market_manifest"]: sha256_file(market_manifest_path)}
    chains, legacy_prices = load_chains(root / CHAIN_PATH), load_prices(root / PRICE_PATH)
    coverage = pilot_coverage(chains, legacy_prices)
    availability = coverage.groupby("snap_date").quote_eligible_puts.min()
    latest = availability.loc[availability > 0].index.max()
    if latest != config["decision_date"]:
        raise ValueError("Configured date is not the latest all-menu snapshot under the audit rule")
    decision, expiry = pd.Timestamp(config["decision_date"]), pd.Timestamp(config["expiration"])
    if set(coverage.loc[coverage.snap_date.eq(latest), "expiry"]) != {config["expiration"]}:
        raise ValueError("Configured expiration differs from the audit union rule")
    market = load_market(root / market_manifest["path"], config["tickers"])
    prices, cash = market_panels(market)
    relevant_dates = legacy_prices.index[(legacy_prices.index >= decision - pd.DateOffset(years=config["lookback_years"]))
                                        & (legacy_prices.index <= expiry)]
    available_dates = prices.index[(prices.index >= relevant_dates.min()) & (prices.index <= expiry)]
    if not relevant_dates.equals(available_dates):
        raise ValueError("Market calendar does not match the pinned legacy price calendar")
    gaps = (prices.loc[available_dates] / legacy_prices.loc[available_dates, prices.columns] - 1).abs()
    if gaps.isna().any().any() or gaps.max().max() > config["max_spot_relative_gap"]:
        raise ValueError("New Close history differs materially from pinned unadjusted prices")
    adjustment = adjustment_diagnostic(market)
    if adjustment.max_daily_return_gap_bps.gt(config["max_adjustment_gap_bps"]).any():
        raise ValueError("Vendor distribution/adjustment consistency check failed")
    chosen, exclusions = selected_contracts(chains, decision, expiry, config["tickers"])
    for row in chosen.itertuples():
        if abs(row.underlying / prices.loc[decision, row.ticker] - 1) > config["max_spot_relative_gap"]:
            raise ValueError(f"Chain/price spot mismatch: {row.ticker}")
    scenarios = historical_scenarios(prices, cash, decision, expiry, config["lookback_years"])
    tables = evaluate(config, chosen, scenarios, prices, cash)
    frontier_tables, frontier_summary = run_frontier(
        config, chains, scenarios, prices, cash, decision, expiry)

    tlt_contract = chosen.loc[chosen["ticker"] == RATE_FACTOR].iloc[0]
    duration_bench, duration_meta = duration_hedge_benchmark(
        config, tlt_contract, scenarios, prices, cash, decision, expiry, portfolio=config["portfolio"])
    duration_comparison = benchmark_vs_optimizer(
        duration_bench, frontier_tables["cvar_frontier"], "treasury_substitute")

    control_tables, control_summary = run_frontier(
        config, chains, scenarios, prices, cash, decision, expiry,
        portfolio=RATE_FACTOR, menus={"tlt_direct": [RATE_FACTOR]})
    control_bench, control_meta = duration_hedge_benchmark(
        config, tlt_contract, scenarios, prices, cash, decision, expiry, portfolio=RATE_FACTOR)
    control_comparison = benchmark_vs_optimizer(
        control_bench, control_tables["cvar_frontier"], "tlt_direct")

    held_out_tables, held_out_meta = run_held_out(config, chains, prices, cash, coverage)

    tables.update(scenarios=scenarios, coverage=coverage, contract_diagnostics=exclusions,
                  market_diagnostics=adjustment,
                  price_reconciliation=pd.DataFrame({"ticker": gaps.columns,
                      "max_relative_close_gap": gaps.max().values}),
                  distribution_events=market.loc[(market.date > decision) & (market.date <= expiry)
                      & (market.dividends + market.capital_gains).gt(0)])
    tables.update(frontier_tables)
    tables.update(duration_benchmark=duration_bench, duration_benchmark_comparison=duration_comparison)
    tables.update({f"control_{name}": frame for name, frame in control_tables.items()})
    tables.update(control_duration_benchmark=control_bench,
                  control_duration_benchmark_comparison=control_comparison)
    tables.update(held_out_tables)

    robust_summary = None
    if config.get("robust_enabled", "robust" in config):
        from src.hedge_design.phase3 import run_phase3
        robust_tables, robust_summary = run_phase3(config, chains, prices, cash, coverage)
        tables.update(robust_tables)

    benchmarks_summary = {
        "duration_hedge": duration_meta,
        "optimizer_matches_or_beats_duration_rule":
            bool(duration_comparison["optimizer_at_least_as_good"].all()),
        "max_optimizer_improvement_over_duration_bps":
            float(duration_comparison["optimizer_improvement_bps"].max()),
        "positive_control": {
            "portfolio": RATE_FACTOR,
            "direct_menu": "TLT puts (a genuine direct hedge of the held asset)",
            "duration_hedge_ratio_beta": control_meta["hedge_ratio_beta"],
            "control_invariants_hold": control_summary["monotonicity_invariants_hold"],
            "control_objectives_verified": control_summary["all_objectives_verified"],
            "direct_cvar_reduction_at_max_budget_no_cap_bps": float(
                control_tables["cvar_frontier"].pipe(
                    lambda f: f.loc[f["oi_fraction"].isna() & (f["tail_level"] == config["tail_levels"][0])
                                    & (f["budget_bps"] == max(config["frontier_budgets_bps"])),
                                    "cvar_reduction_bps"].iloc[0]))}}
    if (not duration_comparison["optimizer_at_least_as_good"].all()
            or not control_comparison["optimizer_at_least_as_good"].all()
            or not held_out_meta["all_frozen_positions_verified"]):
        raise ValueError("Benchmark or held-out verification failed; no results published")
    destination.mkdir(parents=True)
    for name, frame in tables.items():
        frame.to_csv(destination / f"{name}.csv", index=False)
    report = build_report(config, tables)
    (destination / "report.md").write_text(report)
    code_paths = [*sorted((root / "src/hedge_design").glob("*.py")),
                  root / "src/data/hedge_inputs.py", root / "scripts/run_hedge_design.py",
                  root / "scripts/fetch_hedge_market.py"]
    manifest = {"schema_version": 1, "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "config": config,
        "status": ("conditional_finite_model_design" if robust_summary else
                   "conditional_pilot_with_nominal_cvar_frontier_and_matched_held_out_check"),
        "optimizer": {
            "method": "scipy.optimize.linprog(method='highs')",
            "formulation": "rockafellar_uryasev_scenario_cvar_lp",
            "positions": "continuous_nonnegative_contract_counts",
            "objective_recomputed_from_positions": True,
            **frontier_summary,
            "budget_duals": "recorded as local continuous-LP sensitivities; not perturbation-validated (Phase 3)",
            "robust_finite_model_optimization": "run_in_phase3" if robust_summary else "not_requested",
            "evaluation_scope": "in-sample design-model CVaR over the optimization scenario set"},
        "benchmarks": benchmarks_summary,
        "phase3": robust_summary,
        "held_out": held_out_meta,
        "sources": sources, "code": {p.relative_to(root).as_posix(): sha256_file(p) for p in code_paths},
        "versions": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scipy")},
        "scenario_count": len(scenarios), "last_training_end": str(scenarios.window_end.max().date()),
        "trading_sessions": int(scenarios.trading_sessions.iloc[0]),
        "tail_observation_mass": {str(a): len(scenarios) * (1 - a) for a in config["tail_levels"]},
        "overlapping_scenarios_are_independent": False,
        "contract_terms_verified": False, "execution_timestamps_verified": False,
        "independent_distribution_verification": False,
        "outputs": {p.name: sha256_file(p) for p in sorted(destination.iterdir())}}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return destination


def _frontier_report_section(config: dict, tables: dict[str, pd.DataFrame]) -> list[str]:
    frontier = tables.get("cvar_frontier")
    if frontier is None or frontier.empty:
        return []
    alpha = min(config["tail_levels"])
    view = frontier[(frontier["oi_fraction"].isna()) & (frontier["tail_level"] == alpha)]
    menus = [m for m in FRONTIER_MENUS if m in set(view["menu"])]
    budgets = sorted(view["budget_bps"].unique())
    lines = ["", f"## Nominal CVaR Frontier ({alpha:g}, in-sample design model)", "",
        "SciPy HiGHS minimises Rockafellar-Uryasev scenario CVaR of net dollar loss over",
        "continuous, non-negative long-put quantities at the single common expiration, with",
        "the fixed LQD portfolio, the same premium/financing conventions, and OI-fraction",
        "upper bounds. Each objective is recomputed independently from the solver positions.",
        "These are tail losses under the scenario set used for optimisation, not out-of-sample",
        "results. Optional finite-model results are reported separately.", "",
        "No OI cap, CVaR as bps of the $%.0fM portfolio:" % (config["position_usd"] / 1e6), "",
        "| Menu | " + " | ".join(f"{b:g} bps" for b in budgets) + " |",
        "|---|" + "---:|" * len(budgets)]
    for menu in menus:
        cells = []
        for budget in budgets:
            hit = view[(view["menu"] == menu) & (view["budget_bps"] == budget)]
            cells.append(f"{hit['cvar_bps'].iloc[0]:,.1f}" if len(hit) else "-")
        lines.append(f"| {menu} | " + " | ".join(cells) + " |")
    invariants = tables.get("cvar_invariants")
    control = tables.get("cvar_scale_control")
    menu_contracts = tables.get("cvar_menu_contracts")
    lines += ["",
        "- Larger budgets, looser OI caps, and the combined menu never raise modeled CVaR: "
        f"**{'holds' if invariants is not None and bool(invariants['ok'].all()) else 'VIOLATED'}** "
        "(`cvar_invariants.csv`, numerical check of an LP-theoretic fact).",
        "- Percentage frontier invariant to portfolio size with no OI cap: "
        f"**{'holds' if control is not None and np.ptp(control['cvar_bps'].to_numpy()) <= 1e-2 else 'check'}** "
        "(`cvar_scale_control.csv`).",
        "- Objectives independently recomputed from positions: max abs error "
        f"${frontier['cvar_abs_error_usd'].max():,.2f}; all budget/bound residuals within tolerance.",
        "- `cvar_positions.csv` lists every selected strike; `cvar_frontier.csv` carries the "
        "notional-weighted strike/spot ratio per cell. Cross-menu CVaR differences still mix "
        "moneyness, premium, and cross-ETF dependence and do not isolate hedge effectiveness."]
    if menu_contracts is not None and not menu_contracts.empty:
        direct = menu_contracts[menu_contracts["menu"] == "direct"]
        if len(direct):
            lines.append(
                f"- Eligible listed LQD puts span strike/spot "
                f"{direct['strike_spot_ratio'].min():.3f}-{direct['strike_spot_ratio'].max():.3f} "
                f"({int((direct['oi_state'] == 'positive').sum())} of {len(direct)} with positive OI); "
                "near-the-money direct protection is not in the eligible set.")
    lines += ["- Budget shadow prices in `cvar_frontier.csv` are local continuous-LP sensitivities, "
        "recorded but not yet perturbation-validated, and are not market prices."]
    return lines


def _benchmark_report_section(config: dict, tables: dict[str, pd.DataFrame]) -> list[str]:
    comparison = tables.get("duration_benchmark_comparison")
    control_frontier = tables.get("control_cvar_frontier")
    if comparison is None or comparison.empty:
        return []
    alpha = min(config["tail_levels"])
    view = comparison[(comparison["oi_fraction"].isna()) & (comparison["tail_level"] == alpha)]
    beta = tables["duration_benchmark"]["hedge_ratio_beta"].iloc[0]
    strike_spot = tables["duration_benchmark"]["strike_spot_ratio"].iloc[0]
    lines = ["", f"## Duration Benchmark and Positive Control ({alpha:g}, in-sample)", "",
        "The duration benchmark is a frozen rule, not an optimisation: size a nearest-ATM",
        f"eligible TLT-put overlay so its rate delta-notional offsets beta = {beta:.3f} of the",
        "portfolio (past-data OLS of LQD price returns on TLT), then cap by the same premium",
        "budget and OI fractions. Its position is always feasible for the optimiser's",
        "Treasury-substitute menu, so the optimiser can only match or beat it.", "",
        "No OI cap, CVaR as bps of the portfolio:", "",
        "| Budget (bps) | Duration rule | Optimised TLT/IEF | Optimiser gain |",
        "|---:|---:|---:|---:|"]
    for budget in sorted(view["budget_bps"].unique()):
        row = view[view["budget_bps"] == budget].iloc[0]
        lines.append(f"| {budget:g} | {row['benchmark_cvar_bps']:,.1f} | "
                     f"{row['optimizer_cvar_bps']:,.1f} | {row['optimizer_improvement_bps']:,.1f} |")
    ok = bool(comparison["optimizer_at_least_as_good"].all())
    lines += ["",
        f"- Optimiser matches or beats the duration rule in every cell: **{'holds' if ok else 'VIOLATED'}** "
        "(`duration_benchmark_comparison.csv`).",
        f"- Benchmark TLT put strike/spot {strike_spot:.3f}; `duration_benchmark.csv` records the "
        "binding constraint (rate-delta match, budget, or OI cap) for each cell."]
    if control_frontier is not None and not control_frontier.empty:
        control_view = control_frontier[(control_frontier["oi_fraction"].isna())
                                        & (control_frontier["tail_level"] == alpha)]
        base = control_view["unhedged_cvar_usd"].iloc[0]
        top = control_view.sort_values("budget_bps").iloc[-1]
        lines += ["",
            "**Positive control** -- same machinery, portfolio = TLT, hedged with TLT puts "
            "(a genuine direct hedge). The direct menu cuts the "
            f"{alpha:g} tail from {base / config['position_usd'] * 1e4:,.0f} bps to "
            f"{top['cvar_bps']:,.0f} bps at {top['budget_bps']:g} bps of budget "
            f"(reduction {top['cvar_reduction_bps']:,.0f} bps), versus the ~"
            f"{tables['cvar_frontier'].pipe(lambda f: f.loc[f['menu'].eq('direct') & f['oi_fraction'].isna() & f['tail_level'].eq(alpha) & f['budget_bps'].eq(top['budget_bps']), 'cvar_reduction_bps'].iloc[0]):,.0f}"
            " bps the unavailable direct LQD hedge delivers. The optimiser correctly rewards a "
            "hedge that matches the exposure and correctly finds almost nothing when it does not."]
    return lines


def _held_out_report_section(config: dict, tables: dict[str, pd.DataFrame]) -> list[str]:
    summary = tables.get("held_out_summary")
    dates = tables.get("held_out_dates")
    if summary is None or summary.empty:
        return []
    settings = config["held_out"]
    matched = int(summary["matched_dates"].max())
    excluded = int((~dates["matched"]).sum()) if dates is not None else 0
    lines = ["", "## Matched Held-Out Check", "",
        f"Each policy is frozen at {matched} option snapshots (2020-2025) using only that",
        "snapshot's pre-decision scenarios, then evaluated at its single ~1-month expiration.",
        f"Budget {settings['budget_bps']:g} bps, {settings['tail_level']:g} tail, "
        f"{settings['oi_cap']:g} OI cap on the capped variants. "
        f"{excluded} snapshots lack a complete successful policy comparison (`held_out_outcomes.csv`).",
        "One realized loss per date is not a CVaR estimate; the pooled percentile is exploratory",
        "and the dates cluster by rate regime. Positive = loss.", "",
        "| Policy | Mean | Median | Worst | Beat unhedged | Mean spent |",
        "|---|---:|---:|---:|---:|---:|"]
    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['policy']} | {row['mean_realized_loss_bps']:,.0f} | "
            f"{row['median_realized_loss_bps']:,.0f} | {row['worst_realized_loss_bps']:,.0f} | "
            f"{row['dates_better_than_unhedged']}/{row['matched_dates']} | "
            f"{row['mean_spent_bps']:,.1f} bps |")
    lines += ["",
        "- All frozen positions independently verified: "
        f"**{tables['held_out_outcomes'].pipe(lambda o: bool(o.loc[o['evaluable'], 'verified'].all()))}**.",
        "- `held_out_outcomes.csv` has the per-date realized loss, design CVaR, and sizing for "
        "every policy; `held_out_dates.csv` records why each excluded snapshot was dropped.",
        "- Realized losses are one draw per date; this is a small matched sample, not a rolling "
        "backtest, and does not model execution, roll, or path-dependent exercise."]
    return lines


def build_report(config: dict, tables: dict[str, pd.DataFrame]) -> str:
    scenarios = tables["scenarios"]
    rows = ["# Single-Expiration Hedge Accounting Pilot", "",
        "Status: conditional quote-based design experiment; not an executable backtest.", "",
        f"Fixed ${config['position_usd']:,.0f} LQD position; {config['decision_date']} to {config['expiration']}.",
        f"Budget: {config['budget_bps']:g} bps. Nearest-ATM eligible put per ETF; equal budget across basket legs.",
        "No weight fitting, strike optimization, or reallocation of OI-capped budget.", "",
        f"Historical evaluation: {len(scenarios):,} overlapping joint windows, "
        f"{int(scenarios.trading_sessions.iloc[0])} trading sessions each; latest end "
        f"{scenarios.window_end.max().date()} (strictly before decision).",
        "Historical CVaR below describes the fixed benchmark, not optimized or out-of-sample CVaR.",
        "There is one subsequent realized outcome, not a performance test sample.", "",
        "## Results", "",
        "Positive loss means a loss; negative loss means a gain. Dollar amounts rounded here only.", "",
        "| Strategy | Spent | Historical CVaR 90% | Realized net loss |",
        "|---|---:|---:|---:|"]
    for row in tables["solutions"].to_dict("records"):
        cvar = row.get("historical_cvar_0.9_usd")
        cvar_text = f"${cvar:,.0f}" if cvar is not None else "not configured"
        rows.append(f"| {row['strategy']} | ${row['spent_usd']:,.0f} | {cvar_text} | ${row['realized_loss_usd']:,.0f} |")
    rows += _frontier_report_section(config, tables)
    rows += _benchmark_report_section(config, tables)
    rows += _held_out_report_section(config, tables)
    if "robust_frontier" in tables:
        from src.hedge_design.phase3 import phase3_report
        rows += phase3_report(config, tables)
    rows += ["", "## Hand Check", "", "For each row in `realized_accounting.csv`:", "",
        "```text", "shares = initial_position / entry_price",
        "portfolio_price_pnl = shares * (expiry_price - entry_price)",
        "portfolio_cash_pnl = shares * distributions_per_share on (entry, expiry]",
        "put_payoff = contracts * 100 * max(strike - unadjusted_expiry_close, 0)",
        "upfront = contracts * (100 * ask + fee)",
        "net_loss = -portfolio_price_pnl - portfolio_cash_pnl - put_payoff",
        "           + upfront + financing_only", "```", "",
        "`positions.csv` provides per-contract prices, quantities, and intrinsic values.",
        "`distribution_events.csv` gives vendor ex-date amounts; unpaid entitlements are valued at par.", "",
        "## Assumptions and Limits", "",
        "- Standard 100-share deliverables are assumed, not verified per cached contract. "
        "[OCC specifications](https://www.theocc.com/clearance-and-settlement/clearing/etf-options) "
        "describe standard ETF options and warn that corporate actions can change deliverables.",
        "- American puts are held to expiration. Intrinsic value represents the economic equivalent "
        "of physical exercise and offsetting ETF trades, not cash settlement. Early exercise, "
        "settlement lags, stock trading costs, and exercise charges are not modeled.",
        "- Current-vintage Yahoo Close/actions agree internally with adjusted returns and with "
        "pinned Close history within configured tolerances; this is not independent issuer verification.",
        "- Fixed-share distributions are retained without reinvestment or interest. Entry ex-date "
        "payments are excluded; expiration ex-date entitlements are included. Splits are rejected.",
        f"- ${config['fee_per_contract_usd']:g} per contract and {config['financing_rate_annual']:.1%} "
        "simple annual financing are explicit assumptions. Premium and fees are financed once, "
        "ACT/365. The $100M holding is unchanged; hedge costs are an external financed overlay.",
        "- Fractional quantities and no-cap sizing are hypothetical. OI fractions are sensitivity "
        "constraints, not available depth. Unknown OI cannot be used in capped sizing.",
        "- Cached quote/OI timestamps do not establish same-day executable information. "
        "No market impact, position limits, or a realizable $100M execution is asserted.",
        "- Nearest eligible does not necessarily mean near the money. `positions.csv` records "
        "strike/spot ratios. Cross-menu comparisons can mix different moneyness and protection "
        "amounts; they do not isolate underlying hedge effectiveness.",
        "- Joint price and cash-return windows preserve contemporaneous ETF dependence. "
        "Their trading-session count is fixed; calendar lengths and distribution timing vary. "
        "Overlapping windows are not independent observations or uncertainty estimates.",
        "- The snapshot was chosen for all-menu availability, not randomly. Empty menus at "
        "other dates remain in `coverage.csv`; this pilot cannot estimate market-wide hedge availability.",
        "- The CVaR frontier optimises and reports on the same scenario set (design-model risk). "
        "The realized January column in `cvar_frontier.csv` is one subsequent outcome, not a "
        "held-out performance sample. Optional finite-model results are separate.",
        "", "## Next Gate", "",
        "Nominal CVaR frontiers are implemented and self-checked. Still open before publication: "
        "verify contract identifiers/deliverables, execution timing and issuer distributions. "
        "Finite-model design and dual checks are controlled by robust_enabled in study_config.json. "
        "Legacy cleanup remains deferred.", ""]
    return "\n".join(rows)


def verify_run(root: Path, run_id: str) -> None:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", run_id):
        raise ValueError("Invalid run ID")
    destination = root / "results/hedge_design" / run_id
    manifest = json.loads((destination / "manifest.json").read_text())
    if manifest["run_id"] != run_id or not manifest["outputs"]:
        raise ValueError("Invalid run manifest")
    for group in ("sources", "code", "outputs"):
        for name, expected in manifest[group].items():
            path = (destination if group == "outputs" else root) / name
            if sha256_file(path) != expected:
                raise ValueError(f"Changed {group}: {name}")
    for name, version in manifest["versions"].items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f"Changed dependency version: {name}")
