"""Finite-model CVaR on shared joint scenarios; no acquisition or fitted regimes."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

from src.hedge_design.optimize import empirical_cvar, nominal_cvar_lp


def model_weights(scenarios: pd.DataFrame, decision: pd.Timestamp, settings: dict):
    """Predeclared mixtures of uniform history and conditional historical windows."""
    if scenarios.empty or not pd.to_datetime(scenarios.window_end).lt(decision).all():
        raise ValueError("Models require strictly predecision scenario windows")
    base = scenarios.weight.to_numpy(float)
    empirical_cvar(np.zeros(len(base)), base, 0.9)
    masks = {
        "historical": np.ones(len(base), dtype=bool),
        "rate_selloff": scenarios.TLT_price_return.to_numpy() < settings["rate_threshold"],
        "lqd_underperformance": (scenarios.LQD_price_return.to_numpy()
                                 - settings["tlt_loading"] * scenarios.TLT_price_return.to_numpy()
                                 < settings["relative_threshold"]),
    }
    rows, weights = [], []
    for name, mask in masks.items():
        support = int(mask.sum())
        supported = support >= settings["minimum_windows"] and base[mask].sum() > 0
        conditional = base * mask / base[mask].sum() if supported else np.zeros_like(base)
        weight = ((1 - settings["stress_mass"]) * base + settings["stress_mass"] * conditional)
        if name == "historical":
            weight = base.copy()
        rows.append({"model": name, "support_windows": support, "supported": supported,
                     "effective_weight_count": float(1 / (weight @ weight)) if supported else np.nan,
                     "last_training_end": str(pd.to_datetime(scenarios.window_end).max().date()),
                     "overlapping_windows_independent": False})
        weights.append(weight)
    return np.array(weights), pd.DataFrame(rows)


def finite_model_cvar_lp(losses, payoffs, upfront_cost, horizon_cost, weights, alpha,
                         budget, upper, *, dollar_scale=1_000_000.0,
                         feasibility_tol_usd=1.0, recompute_rtol=1e-6) -> dict:
    """Minimize max-model CVaR with separate eta and excess-loss variables per model."""
    losses = np.asarray(losses, float)
    payoffs = np.asarray(payoffs, float)
    upfront = np.asarray(upfront_cost, float)
    horizon = np.asarray(horizon_cost, float)
    weights = np.asarray(weights, float)
    upper = np.asarray(upper, float)
    if (losses.ndim != 1 or payoffs.ndim != 2 or weights.ndim != 2
            or not len(weights) or weights.shape[1] != len(losses)
            or upfront.ndim != 1 or horizon.ndim != 1 or upper.ndim != 1):
        raise ValueError("Invalid finite-model dimensions")
    for weight in weights:
        empirical_cvar(losses, weight, alpha)
    baseline = nominal_cvar_lp(losses, payoffs, upfront, horizon, weights[0], alpha,
                               budget, upper, dollar_scale=dollar_scale,
                               feasibility_tol_usd=feasibility_tol_usd,
                               recompute_rtol=recompute_rtol) if (
                                   not len(upfront) or budget == 0 or not np.any(upper > 0)) else None
    if (payoffs.shape != (len(losses), len(upfront)) or horizon.shape != upfront.shape
            or upper.shape != upfront.shape or not np.isfinite(payoffs).all()
            or not np.isfinite(upfront).all() or not np.isfinite(horizon).all()
            or (upfront <= 0).any() or np.isnan(upper).any() or (upper < 0).any()
            or not np.isfinite(budget) or budget < 0
            or not np.isfinite(dollar_scale) or dollar_scale <= 0
            or not np.isfinite(feasibility_tol_usd) or feasibility_tol_usd < 0
            or not 0 < recompute_rtol < 1):
        raise ValueError("Invalid finite-model costs, bounds or tolerances")
    if baseline is not None:
        risks = np.array([empirical_cvar(losses, weight, alpha) for weight in weights])
        baseline.update(cvar_usd=float(risks.max()), lp_objective_usd=float(risks.max()),
                        model_cvar_usd=risks, constraint_violation_usd=0.0,
                        upper_shadow_prices=np.full(len(upfront), np.nan))
        return baseline
    count, contracts, models = len(losses), len(upfront), len(weights)
    width = contracts + 1 + models * (count + 1)
    blocks, rhs = [], []
    for index, weight in enumerate(weights):
        start = contracts + 1 + index * (count + 1)
        block = sparse.hstack([
            sparse.csr_matrix((horizon[None, :] - payoffs) / dollar_scale),
            sparse.csr_matrix((count, 1 + index * (count + 1))),
            -sparse.csr_matrix(np.ones((count, 1))), -sparse.eye(count),
            sparse.csr_matrix((count, (models - index - 1) * (count + 1))),
        ], format="csr")
        epigraph = sparse.lil_matrix((1, width))
        epigraph[0, contracts] = -1
        epigraph[0, start] = 1
        epigraph[0, start + 1:start + 1 + count] = weight / (1 - alpha)
        blocks.extend([block, epigraph.tocsr()])
        rhs.extend([-losses / dollar_scale, np.zeros(1)])
    budget_row = sparse.lil_matrix((1, width))
    budget_row[0, :contracts] = upfront / dollar_scale
    blocks.append(budget_row.tocsr())
    rhs.append(np.array([budget / dollar_scale]))
    matrix, limits = sparse.vstack(blocks, format="csr"), np.concatenate(rhs)
    objective = np.zeros(width)
    objective[contracts] = 1
    bounds = ([(0, None if np.isinf(bound) else float(bound)) for bound in upper]
              + [(None, None)] + ([(None, None)] + [(0, None)] * count) * models)
    result = linprog(objective, A_ub=matrix, b_ub=limits, bounds=bounds, method="highs")
    if not result.success:
        raise ValueError(f"Finite-model solver failed ({result.status}): {result.message}")
    quantities = result.x[:contracts]
    net = losses - payoffs @ quantities + horizon @ quantities
    risks = np.array([empirical_cvar(net, weight, alpha) for weight in weights])
    recomputed = float(risks.max())
    residual = float(max(0, (matrix @ result.x - limits).max()) * dollar_scale)
    bound_error = float(max(0, (-quantities).max(), (quantities - upper).max()))
    excess_error = max(0.0, max(-result.x[contracts + 2 + index * (count + 1):
                                      contracts + 2 + index * (count + 1) + count].min()
                                for index in range(models))) * dollar_scale
    objective_error = abs(recomputed - result.fun * dollar_scale)
    budget_error = max(0.0, float(upfront @ quantities - budget))
    verified = bool(objective_error <= max(feasibility_tol_usd, abs(recomputed) * recompute_rtol)
                    and residual <= feasibility_tol_usd and excess_error <= feasibility_tol_usd
                    and budget_error <= feasibility_tol_usd and bound_error <= 1e-6)
    return {"status": "optimal", "solver_status": int(result.status), "message": result.message,
            "x": quantities, "cvar_usd": recomputed, "model_cvar_usd": risks,
            "lp_objective_usd": float(result.fun * dollar_scale),
            "cvar_abs_error_usd": objective_error, "spent_usd": float(upfront @ quantities),
            "budget_violation_usd": budget_error, "bound_violation_contracts": bound_error,
            "constraint_violation_usd": max(residual, excess_error), "verified": verified,
            "budget_shadow_price": float(-result.ineqlin.marginals[-1]),
            "upper_shadow_prices": -result.upper.marginals[:contracts] * dollar_scale}


def validate_sensitivity(solve, solution: dict, budget: float, upper: np.ndarray,
                         relative_step: float, tolerance_usd: float) -> list[dict]:
    """Two-sided secants bracket LP duals, including non-differentiable optima."""
    if solution["status"] != "optimal" or budget <= 0:
        return []
    probes = [("budget", budget * relative_step, solution["budget_shadow_price"],
               budget * (1 - relative_step), budget * (1 + relative_step), upper, upper)]
    if len(upper) and np.isfinite(upper).all() and (upper > 0).any():
        probes.append(("all_oi_limits_proportional", relative_step,
                       float(solution["upper_shadow_prices"] @ upper), budget, budget,
                       upper * (1 - relative_step), upper * (1 + relative_step)))
    rows = []
    for name, step, dual, lower_budget, higher_budget, lower_upper, higher_upper in probes:
        lower = solve(lower_budget, lower_upper)
        higher = solve(higher_budget, higher_upper)
        if not lower["verified"] or not higher["verified"]:
            raise ValueError("Unverified sensitivity perturbation")
        left = (lower["cvar_usd"] - solution["cvar_usd"]) / step
        right = (solution["cvar_usd"] - higher["cvar_usd"]) / step
        error = max(0.0, right - dual, dual - left, -dual) * step
        valid = bool(np.isfinite([left, right, dual]).all() and error <= tolerance_usd)
        rows.append({"constraint": name, "step": step, "dual_benefit": dual,
                     "left_benefit": left, "right_benefit": right,
                     "bracket_error_usd": error, "verified": valid,
                     "locally_linear": abs(left - right) * step <= tolerance_usd})
        if not valid:
            raise ValueError(f"Dual perturbation verification failed: {name}")
    return rows
