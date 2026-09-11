"""Rule-based hedge benchmarks: no optimization, frozen before held-out evaluation.

The duration benchmark is a standard desk rule -- size a listed TLT-put overlay to
offset the fixed portfolio's rate exposure, using a past-data hedge ratio and the
nearest-at-the-money eligible put, subject to the same budget, open-interest, and
cost conventions as the optimizer. It exists to answer "does CVaR optimization
improve on a naive duration hedge?", so it must be a feasible point for the
optimizer's Treasury-substitute menu at every budget and cap.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.hedge_design.market import holding_return
from src.hedge_design.optimize import empirical_cvar

RATE_FACTOR = "TLT"


def ols_hedge_ratio(target_returns, factor_returns) -> tuple[float, float]:
    """Slope and intercept of an OLS regression of ``target`` on ``factor`` (with a constant).

    A constant factor carries no hedgeable exposure, so the slope is defined as zero.
    """
    factor = np.asarray(factor_returns, float)
    target = np.asarray(target_returns, float)
    if factor.ndim != 1 or factor.shape != target.shape or factor.size < 2:
        raise ValueError("Hedge-ratio inputs must be equal-length 1-D return vectors")
    if not (np.isfinite(factor).all() and np.isfinite(target).all()):
        raise ValueError("Hedge-ratio inputs must be finite")
    if np.ptp(factor) == 0:
        return 0.0, float(target.mean())
    design = np.column_stack([np.ones_like(factor), factor])
    (intercept, slope), *_ = np.linalg.lstsq(design, target, rcond=None)
    return float(slope), float(intercept)


def duration_hedge_benchmark(config: dict, tlt_contract: pd.Series, scenarios: pd.DataFrame,
                             prices: pd.DataFrame, cash: pd.DataFrame, decision: pd.Timestamp,
                             expiry: pd.Timestamp, *, portfolio: str) -> tuple[pd.DataFrame, dict]:
    """Past-data hedge-ratio TLT-put overlay on ``portfolio``, swept over budgets and OI caps."""
    position = float(config["position_usd"])
    multiplier = float(config["contract_terms"]["multiplier"])
    fee = float(config["fee_per_contract_usd"])
    financing_factor = 1.0 + config["financing_rate_annual"] * (expiry - decision).days / 365
    entry_spot = float(prices.loc[decision, RATE_FACTOR])

    beta, intercept = ols_hedge_ratio(scenarios[f"{portfolio}_price_return"].to_numpy(),
                                      scenarios[f"{RATE_FACTOR}_price_return"].to_numpy())
    delta = float(pd.to_numeric(tlt_contract["delta"], errors="coerce"))
    if not -1.0 < delta < 0.0:
        raise ValueError("Duration benchmark needs a finite negative put delta")
    strike = float(tlt_contract["strike"])
    ask = float(tlt_contract["ask"])
    open_interest = pd.to_numeric(tlt_contract["open_interest"], errors="coerce")
    upfront_cost = multiplier * ask + fee
    horizon_cost = upfront_cost * financing_factor

    # One contract offsets |delta| * spot * multiplier of TLT delta-notional; match beta * position.
    per_contract_notional = abs(delta) * entry_spot * multiplier
    target_contracts = max(beta, 0.0) * position / per_contract_notional

    losses = -position * (scenarios[f"{portfolio}_price_return"].to_numpy()
                          + scenarios[f"{portfolio}_cash_return"].to_numpy())
    weights = scenarios["weight"].to_numpy()
    terminal = entry_spot * (1.0 + scenarios[f"{RATE_FACTOR}_price_return"].to_numpy())
    scenario_payoff = multiplier * np.maximum(strike - terminal, 0.0)
    realized_unit = multiplier * max(strike - float(prices.loc[expiry, RATE_FACTOR]), 0.0)
    realized_pr, realized_cr = holding_return(prices, cash, decision, expiry)
    realized_portfolio_loss = -position * (realized_pr[portfolio] + realized_cr[portfolio])

    rows = []
    for tail in config["tail_levels"]:
        unhedged = empirical_cvar(losses, weights, tail)
        for bps in config["frontier_budgets_bps"]:
            budget = position * bps / 10000.0
            for cap in config["oi_fractions"]:
                budget_limit = budget / upfront_cost
                if cap is None:
                    oi_limit = np.inf
                elif np.isfinite(open_interest) and open_interest >= 0 and float(open_interest).is_integer():
                    oi_limit = cap * float(open_interest)
                else:
                    oi_limit = 0.0
                caps = {"rate_delta_match": target_contracts, "budget": budget_limit, "oi_cap": oi_limit}
                binding = min(caps, key=caps.get)
                contracts = max(0.0, min(caps.values()))
                net = losses - contracts * scenario_payoff + contracts * horizon_cost
                cvar = empirical_cvar(net, weights, tail)
                realized = (realized_portfolio_loss - contracts * realized_unit
                            + contracts * horizon_cost)
                spent = contracts * upfront_cost
                rows.append({
                    "portfolio": portfolio, "tail_level": tail, "budget_bps": bps,
                    "oi_fraction": cap, "hedge_ticker": RATE_FACTOR, "strike": strike,
                    "strike_spot_ratio": strike / entry_spot, "put_delta": delta,
                    "hedge_ratio_beta": beta, "target_contracts": target_contracts,
                    "contracts": contracts, "binding_constraint": binding,
                    "budget_usd": budget, "spent_usd": spent,
                    "unspent_usd": budget - spent, "financed_cost_usd": contracts * horizon_cost,
                    "cvar_usd": cvar, "cvar_bps": cvar / position * 10000.0,
                    "unhedged_cvar_usd": unhedged,
                    "cvar_reduction_bps": (unhedged - cvar) / position * 10000.0,
                    "realized_net_loss_usd": realized,
                    "realized_net_loss_bps": realized / position * 10000.0})
    meta = {"rule": "past-data OLS hedge ratio of portfolio price returns on TLT; "
                    "nearest-ATM eligible TLT put, rate-delta-matched; same budget/OI/cost "
                    "caps as the optimizer; frozen, not fitted to outcomes",
            "portfolio": portfolio, "hedge_ratio_beta": beta, "hedge_ratio_intercept": intercept,
            "put_strike": strike, "put_delta": delta, "put_strike_spot_ratio": strike / entry_spot,
            "target_contracts_full_size": target_contracts}
    return pd.DataFrame(rows), meta


def benchmark_vs_optimizer(benchmark: pd.DataFrame, frontier: pd.DataFrame,
                           optimizer_menu: str, tol_usd: float = 10.0) -> pd.DataFrame:
    """Match the duration rule against the optimizer's best use of the comparable menu.

    The benchmark position is a feasible point for ``optimizer_menu`` at every budget
    and cap, so ``optimizer_cvar <= benchmark_cvar`` must hold up to solver tolerance.
    """
    optimized = frontier.loc[frontier["menu"] == optimizer_menu,
                             ["tail_level", "budget_bps", "oi_fraction", "cvar_usd", "cvar_bps"]]
    optimized = optimized.rename(columns={"cvar_usd": "optimizer_cvar_usd",
                                          "cvar_bps": "optimizer_cvar_bps"})
    merged = benchmark.merge(optimized, on=["tail_level", "budget_bps", "oi_fraction"], how="left")
    merged["optimizer_menu"] = optimizer_menu
    merged["benchmark_cvar_bps"] = merged["cvar_bps"]
    merged["optimizer_improvement_bps"] = merged["benchmark_cvar_bps"] - merged["optimizer_cvar_bps"]
    merged["optimizer_at_least_as_good"] = (
        merged["optimizer_cvar_usd"] <= merged["cvar_usd"] + tol_usd)
    return merged[["portfolio", "tail_level", "budget_bps", "oi_fraction", "optimizer_menu",
                   "benchmark_cvar_bps", "optimizer_cvar_bps", "optimizer_improvement_bps",
                   "binding_constraint", "contracts", "optimizer_at_least_as_good"]]
