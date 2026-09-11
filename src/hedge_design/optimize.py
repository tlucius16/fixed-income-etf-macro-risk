"""Nominal scenario CVaR optimization (Rockafellar-Uryasev LP) via SciPy HiGHS.

The problem is a linear program with fixed scenario coefficients and continuous,
non-negative contract quantities. Dollar quantities are scaled for conditioning;
contract counts are returned in native units. Every solved objective is
independently recomputed from the returned positions with :func:`empirical_cvar`,
and explicit budget/bound residuals are reported. This module performs no data
loading and no robust (finite-model) optimization.
"""
from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

_SOLVER_STATUS = {0: "optimal", 1: "iteration_limit", 2: "infeasible",
                  3: "unbounded", 4: "numerical_difficulty"}


def empirical_cvar(losses: np.ndarray, weights: np.ndarray, alpha: float) -> float:
    """Upper-tail loss mean with fractional boundary mass, including loss ties."""
    losses, weights = np.asarray(losses, float), np.asarray(weights, float)
    if (losses.ndim != 1 or losses.shape != weights.shape or not len(losses)
            or not np.isfinite(losses).all() or not np.isfinite(weights).all()
            or (weights < 0).any() or not np.isclose(weights.sum(), 1, rtol=0, atol=1e-10)
            or not 0 < alpha < 1):
        raise ValueError("Invalid CVaR evaluation inputs")
    order = np.argsort(-losses)
    mass = weights[order]
    before = np.cumsum(mass) - mass
    used = np.minimum(mass, np.maximum(1 - alpha - before, 0))
    return float(np.dot(used, losses[order]) / (1 - alpha))


def empirical_var(losses: np.ndarray, weights: np.ndarray, alpha: float) -> float:
    """Weighted alpha-quantile of the loss distribution (the RU VaR at the CVaR optimum)."""
    losses, weights = np.asarray(losses, float), np.asarray(weights, float)
    if (losses.ndim != 1 or losses.shape != weights.shape or not len(losses)
            or not np.isfinite(losses).all() or (weights < 0).any()
            or not np.isclose(weights.sum(), 1, rtol=0, atol=1e-10) or not 0 < alpha < 1):
        raise ValueError("Invalid VaR evaluation inputs")
    order = np.argsort(losses)
    cumulative = np.cumsum(weights[order])
    return float(losses[order][min(int(np.searchsorted(cumulative, alpha)), len(losses) - 1)])


def _unhedged(reason: str, n_contract: int, cvar: float, var: float) -> dict:
    return {"status": reason, "solver_status": None, "message": "no optimization performed",
            "x": np.zeros(max(n_contract, 0)), "eta_usd": var, "cvar_usd": cvar,
            "lp_objective_usd": cvar, "cvar_abs_error_usd": 0.0, "spent_usd": 0.0,
            "budget_violation_usd": 0.0, "bound_violation_contracts": 0.0,
            "budget_shadow_price": float("nan"), "verified": True,
            "unhedged_cvar_usd": cvar, "unhedged_var_usd": var,
            "n_contracts": n_contract, "n_available": 0}


def nominal_cvar_lp(losses, payoffs, upfront_cost, horizon_cost, weights, alpha, budget,
                    upper, *, dollar_scale: float = 1_000_000.0,
                    feasibility_tol_usd: float = 1.0, recompute_rtol: float = 1e-6,
                    quantity_floor: float = 1e-9) -> dict:
    """Minimise scenario CVaR of net dollar loss for a fixed portfolio hedged with long puts.

        loss_s(x) = losses[s] - sum_j payoffs[s, j] x_j + sum_j horizon_cost[j] x_j
        minimise  eta + (1 / (1 - alpha)) sum_s weights[s] z_s
        s.t.      z_s >= loss_s(x) - eta,   z_s >= 0
                  sum_j upfront_cost[j] x_j <= budget
                  0 <= x_j <= upper[j]                      (upper[j] may be +inf)

    ``losses`` is the fixed unhedged loss per scenario, ``payoffs`` the per-contract
    terminal payoff (S, J), ``upfront_cost`` the acquisition ask plus fees, and
    ``horizon_cost`` that cost financed to the expiration. The zero hedge is always
    feasible, so the LP is bounded and feasible whenever the inputs are well formed.

    Returns the solver solution, an independent CVaR recomputation from the
    returned positions, feasibility residuals, and the budget-constraint dual
    (a local LP sensitivity, not a market price).
    """
    losses = np.asarray(losses, float).reshape(-1)
    payoffs = np.asarray(payoffs, float)
    if payoffs.ndim != 2:
        payoffs = payoffs.reshape(losses.size, -1)
    n_scen, n_contract = payoffs.shape
    c0 = np.asarray(upfront_cost, float).reshape(-1)
    cH = np.asarray(horizon_cost, float).reshape(-1)
    ub = np.asarray(upper, float).reshape(-1)
    weights = np.asarray(weights, float).reshape(-1)

    if n_scen != losses.size or weights.size != n_scen:
        raise ValueError("Scenario dimensions disagree")
    if c0.size != n_contract or cH.size != n_contract or ub.size != n_contract:
        raise ValueError("Contract dimensions disagree")
    if not (np.isfinite(losses).all() and np.isfinite(payoffs).all()
            and np.isfinite(c0).all() and np.isfinite(cH).all() and np.isfinite(weights).all()):
        raise ValueError("Nonfinite optimization input")
    if n_contract and (c0 <= 0).any():
        raise ValueError("Upfront contract cost must be positive")
    if (ub < 0).any() or np.isnan(ub).any():
        raise ValueError("Contract upper bounds must be non-negative")
    if not np.isfinite(budget) or budget < 0:
        raise ValueError("Budget must be finite and non-negative")
    if not 0 < alpha < 1:
        raise ValueError("Tail level must be strictly between zero and one")
    if not np.isclose(weights.sum(), 1, rtol=0, atol=1e-10) or (weights < 0).any():
        raise ValueError("Scenario weights must be non-negative and sum to one")
    if not (np.isfinite(dollar_scale) and dollar_scale > 0):
        raise ValueError("dollar_scale must be positive")

    unhedged_cvar = empirical_cvar(losses, weights, alpha)
    unhedged_var = empirical_var(losses, weights, alpha)
    available = ub > 0
    if n_contract == 0 or budget <= 0 or not available.any():
        reason = ("empty_menu" if n_contract == 0
                  else "zero_budget" if budget <= 0 else "no_available_contracts")
        return _unhedged(reason, n_contract, unhedged_cvar, unhedged_var)

    scale = float(dollar_scale)
    payoff_s = payoffs / scale
    cost_up = c0 / scale
    cost_h = cH / scale

    # Variables: [x_0 .. x_{J-1}, eta, z_0 .. z_{S-1}]
    objective = np.concatenate([np.zeros(n_contract), [1.0], weights / (1.0 - alpha)])
    scenario_block = sparse.hstack([
        sparse.csr_matrix(cost_h[None, :] - payoff_s),
        sparse.csr_matrix(-np.ones((n_scen, 1))),
        -sparse.eye(n_scen, format="csr"),
    ], format="csr")
    budget_block = sparse.hstack([
        sparse.csr_matrix(cost_up[None, :]),
        sparse.csr_matrix((1, 1 + n_scen)),
    ], format="csr")
    a_ub = sparse.vstack([scenario_block, budget_block], format="csr")
    b_ub = np.concatenate([-losses / scale, [budget / scale]])

    bounds = ([(0.0, (None if not np.isfinite(u) else float(u))) for u in ub]
              + [(None, None)] + [(0.0, None)] * n_scen)
    res = linprog(objective, A_ub=a_ub, b_ub=b_ub, bounds=bounds, method="highs")

    if res.status != 0:
        return {"status": _SOLVER_STATUS.get(res.status, "unknown"),
                "solver_status": int(res.status), "message": str(res.message),
                "x": None, "eta_usd": float("nan"), "cvar_usd": float("nan"),
                "lp_objective_usd": float("nan"), "cvar_abs_error_usd": float("nan"),
                "spent_usd": float("nan"), "budget_violation_usd": float("nan"),
                "bound_violation_contracts": float("nan"),
                "budget_shadow_price": float("nan"), "verified": False,
                "unhedged_cvar_usd": unhedged_cvar, "unhedged_var_usd": unhedged_var,
                "n_contracts": n_contract, "n_available": int(available.sum())}

    raw_x = np.asarray(res.x[:n_contract], float)
    finite_ub = np.where(np.isfinite(ub), ub, np.inf)
    x = np.clip(np.where(np.abs(raw_x) < quantity_floor, 0.0, raw_x), 0.0, finite_ub)
    eta = float(res.x[n_contract]) * scale
    lp_objective = float(res.fun) * scale

    net = losses - payoffs @ x + float(cH @ x)
    recomputed = empirical_cvar(net, weights, alpha)
    spent = float(c0 @ x)
    budget_violation = max(0.0, spent - budget)
    over = np.where(np.isfinite(ub), x - ub, 0.0)
    bound_violation = float(max(over.max(initial=0.0), -x.min(initial=0.0), 0.0))

    marginals = getattr(getattr(res, "ineqlin", None), "marginals", None)
    shadow_price = (float(-np.asarray(marginals, float)[-1])
                    if marginals is not None and np.size(marginals) else float("nan"))

    tol = max(feasibility_tol_usd, abs(recomputed) * recompute_rtol)
    verified = bool(abs(recomputed - lp_objective) <= tol
                    and budget_violation <= feasibility_tol_usd
                    and bound_violation <= 1e-6)
    return {"status": "optimal", "solver_status": 0, "message": str(res.message),
            "x": x, "eta_usd": eta, "cvar_usd": recomputed, "lp_objective_usd": lp_objective,
            "cvar_abs_error_usd": abs(recomputed - lp_objective), "spent_usd": spent,
            "budget_violation_usd": budget_violation,
            "bound_violation_contracts": bound_violation,
            "budget_shadow_price": shadow_price, "verified": verified,
            "upper_shadow_prices": -np.asarray(res.upper.marginals[:n_contract]) * scale,
            "unhedged_cvar_usd": unhedged_cvar, "unhedged_var_usd": unhedged_var,
            "n_contracts": n_contract, "n_available": int(available.sum())}
