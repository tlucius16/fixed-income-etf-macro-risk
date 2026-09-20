"""Offline finite-model frontiers, paired subsequent outcomes and assumption checks."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.hedge_inputs import quote_flags
from src.hedge_design.benchmarks import duration_hedge_benchmark
from src.hedge_design.experiment import (
    FRONTIER_MENUS, _monotone_invariants, _oi_upper_bound, _put_chain_slice, _scenario_payoffs,
    qualifying_dates, require_verified_solution, selected_contracts, validate_candidate_spots,
)
from src.hedge_design.market import historical_scenarios, holding_return
from src.hedge_design.optimize import empirical_cvar, nominal_cvar_lp
from src.hedge_design.robust import finite_model_cvar_lp, model_weights, validate_sensitivity


def validate_robust_config(settings: dict) -> None:
    expected = {"minimum_windows", "stress_mass", "rate_threshold", "tlt_loading",
                "relative_threshold", "dual_relative_step", "dual_tolerance_usd", "quote_rules"}
    if (set(settings) != expected or type(settings["minimum_windows"]) is not int
            or settings["minimum_windows"] < 2 or not 0 < settings["stress_mass"] < 1
            or not -1 < settings["rate_threshold"] < 0
            or not -1 < settings["relative_threshold"] < 0
            or not np.isfinite(settings["tlt_loading"]) or settings["tlt_loading"] < 0
            or not 0 < settings["dual_relative_step"] < 0.1
            or not np.isfinite(settings["dual_tolerance_usd"]) or settings["dual_tolerance_usd"] < 0
            or settings["quote_rules"] != ["baseline", "tight_spread", "zero_bid", "matched_moneyness"]):
        raise ValueError("Invalid robust configuration")


def quote_candidates(chains, decision, expiry, tickers, rule):
    frame = _put_chain_slice(chains, decision, expiry, tickers)
    if rule not in {"baseline", "tight_spread", "zero_bid", "matched_moneyness"}:
        raise ValueError("Unknown quote rule")
    spread_limit = 0.20 if rule == "tight_spread" else 0.35
    flags = quote_flags(frame, max_rel_spread=spread_limit)
    eligible = flags.quote_eligible.copy()
    if rule == "zero_bid":
        alternative = quote_flags(frame, max_rel_spread=2.0)
        columns = list(alternative.columns[:alternative.columns.get_loc("quote_eligible")])
        columns.remove("nonpositive_bid")
        eligible |= frame.bid.eq(0) & ~alternative[columns].any(axis=1)
    if rule == "matched_moneyness":
        eligible &= (frame.strike / frame.underlying).between(0.95, 1.05)
    frame = frame.loc[eligible]
    return frame.sort_values(["ticker", "strike"]).reset_index(drop=True)


def evaluate_date(config, chains, prices, cash, decision, expiry, budgets, tails, caps,
                  rules, *, check_duals=False):
    scenarios = historical_scenarios(prices, cash, decision, expiry, config["lookback_years"])
    weights, support = model_weights(scenarios, decision, config["robust"])
    support.insert(0, "decision_date", str(decision.date()))
    if not support.supported.all():
        return {"support": support}, False
    names = support.model.tolist()
    position = float(config["position_usd"])
    multiplier = float(config["contract_terms"]["multiplier"])
    losses = -position * (scenarios[f"{config['portfolio']}_price_return"].to_numpy()
                          + scenarios[f"{config['portfolio']}_cash_return"].to_numpy())
    factor = 1 + config["financing_rate_annual"] * (expiry - decision).days / 365
    optimizer = config["optimizer"]
    kwargs = {"dollar_scale": optimizer["dollar_scale"],
              "feasibility_tol_usd": optimizer["feasibility_tol_usd"],
              "recompute_rtol": optimizer["cvar_recompute_rtol"]}
    rows, positions, risks, probes, candidates_rows = [], [], [], [], []
    for rule in rules:
        for menu, tickers in FRONTIER_MENUS.items():
            candidates = quote_candidates(chains, decision, expiry, tickers, rule)
            validate_candidate_spots(candidates, prices.loc[decision], config["max_spot_relative_gap"])
            payoffs = _scenario_payoffs(candidates, scenarios, prices.loc[decision], multiplier)
            upfront = candidates.ask.to_numpy() * multiplier + config["fee_per_contract_usd"]
            horizon = upfront * factor
            candidates_rows.append(candidates.assign(decision_date=str(decision.date()), menu=menu,
                quote_rule=rule, strike_spot_ratio=candidates.strike / candidates.underlying))
            for tail in tails:
                for bps in budgets:
                    budget = position * bps / 10000
                    for cap in caps:
                        upper = _oi_upper_bound(candidates, cap)
                        solutions = {}
                        for method in ("nominal", "robust"):
                            def solve(changed_budget, changed_upper):
                                if method == "nominal":
                                    solution = nominal_cvar_lp(losses, payoffs, upfront, horizon,
                                        weights[0], tail, changed_budget, changed_upper, **kwargs)
                                else:
                                    solution = finite_model_cvar_lp(losses, payoffs, upfront, horizon,
                                        weights, tail, changed_budget, changed_upper, **kwargs)
                                require_verified_solution(solution)
                                return solution

                            solution = solve(budget, upper)
                            quantities = solution["x"]
                            net = losses - payoffs @ quantities + horizon @ quantities
                            model_risks = [empirical_cvar(net, weight, tail) for weight in weights]
                            key = {"decision_date": str(decision.date()), "expiration": str(expiry.date()),
                                   "quote_rule": rule, "menu": menu, "tail_level": tail,
                                   "budget_bps": bps, "oi_fraction": cap, "method": method}
                            selected = quantities > 1e-9
                            rows.append({**key, "objective_usd": solution["cvar_usd"],
                                "nominal_cvar_usd": model_risks[0], "worst_model_cvar_usd": max(model_risks),
                                "unhedged_worst_model_cvar_usd": max(empirical_cvar(losses, weight, tail) for weight in weights),
                                "spent_usd": float(upfront @ quantities),
                                "financed_cost_usd": float(horizon @ quantities),
                                "budget_slack_usd": budget - float(upfront @ quantities),
                                "n_candidates": len(candidates), "n_selected": int(selected.sum()),
                                "min_strike_spot": float((candidates.strike / candidates.underlying)[selected].min()),
                                "max_strike_spot": float((candidates.strike / candidates.underlying)[selected].max()),
                                "status": solution["status"], "verified": solution["verified"],
                                "objective_error_usd": solution["cvar_abs_error_usd"],
                                "budget_violation_usd": solution["budget_violation_usd"],
                                "bound_violation_contracts": solution["bound_violation_contracts"],
                                "constraint_violation_usd": solution.get("constraint_violation_usd", np.nan)})
                            for name, risk, weight in zip(names, model_risks, weights):
                                risks.append({**key, "model": name, "cvar_usd": risk,
                                              "tail_effective_weight_count": (1 - tail) / (weight @ weight)})
                            for index in np.flatnonzero(selected):
                                contract = candidates.iloc[index]
                                positions.append({**key, "ticker": contract.ticker, "strike": contract.strike,
                                    "strike_spot_ratio": contract.strike / contract.underlying,
                                    "contracts": quantities[index], "ask": contract.ask,
                                    "upfront_unit_usd": upfront[index], "horizon_unit_usd": horizon[index],
                                    "upper_contracts": upper[index], "open_interest": contract.open_interest})
                            if check_duals:
                                for probe in validate_sensitivity(solve, solution, budget, upper,
                                        config["robust"]["dual_relative_step"], config["robust"]["dual_tolerance_usd"]):
                                    probes.append({**key, **probe})
                            solutions[method] = (solution, model_risks)
                        nominal, robust = solutions["nominal"], solutions["robust"]
                        tolerance = max(10.0, abs(robust[0]["cvar_usd"]) * kwargs["recompute_rtol"])
                        if (robust[0]["cvar_usd"] < nominal[0]["cvar_usd"] - tolerance
                                or robust[0]["cvar_usd"] > max(nominal[1]) + tolerance):
                            raise ValueError("Model-family expansion or robust dominance invariant failed")
                        if check_duals:
                            single = finite_model_cvar_lp(losses, payoffs, upfront, horizon, weights[:1],
                                                          tail, budget, upper, **kwargs)
                            require_verified_solution(single)
                            if abs(single["cvar_usd"] - nominal[0]["cvar_usd"]) > tolerance:
                                raise ValueError("One-model robust/nominal equivalence failed")
    frontier = pd.DataFrame(rows)
    checks = []
    for (rule, method), group in frontier.groupby(["quote_rule", "method"]):
        check = _monotone_invariants(group.rename(columns={"objective_usd": "cvar_usd"}), caps)
        checks.append(check.assign(quote_rule=rule, method=method))
    invariants = pd.concat(checks, ignore_index=True)
    if not invariants.ok.all():
        raise ValueError("Robust frontier menu/budget/access invariants failed")
    position_table = pd.DataFrame(positions, columns=[
        "decision_date", "expiration", "quote_rule", "menu", "tail_level", "budget_bps", "oi_fraction",
        "method", "ticker", "strike", "strike_spot_ratio", "contracts", "ask", "upfront_unit_usd",
        "horizon_unit_usd", "upper_contracts", "open_interest"])
    realized_pr, realized_cr = holding_return(prices, cash, decision, expiry)
    unhedged_realized = -position * (realized_pr[config["portfolio"]] + realized_cr[config["portfolio"]])
    for index, row in frontier.iterrows():
        mask = position_table.method.eq(row.method) & position_table.menu.eq(row.menu)
        for column in ("quote_rule", "tail_level", "budget_bps"):
            mask &= position_table[column].eq(row[column])
        mask &= position_table.oi_fraction.isna() if pd.isna(row.oi_fraction) else position_table.oi_fraction.eq(row.oi_fraction)
        chosen = position_table.loc[mask]
        payoff = sum(contract.contracts * multiplier * max(
            contract.strike - prices.loc[expiry, contract.ticker], 0) for contract in chosen.itertuples())
        frontier.loc[index, "realized_net_loss_usd"] = unhedged_realized - payoff + row.financed_cost_usd
        frontier.loc[index, "unhedged_realized_loss_usd"] = unhedged_realized
    weight_table = pd.concat([scenarios.assign(model=name, model_weight=weight,
                                 decision_date=str(decision.date())) for name, weight in zip(names, weights)],
                              ignore_index=True)
    return {"frontier": frontier, "positions": position_table, "model_risks": pd.DataFrame(risks),
            "duals": pd.DataFrame(probes), "support": support, "weights": weight_table,
            "candidates": pd.concat(candidates_rows, ignore_index=True), "invariants": invariants}, True


def run_phase3(config, chains, prices, cash, coverage):
    validate_robust_config(config["robust"])
    decision, expiry = pd.Timestamp(config["decision_date"]), pd.Timestamp(config["expiration"])
    pilot, available = evaluate_date(config, chains, prices, cash, decision, expiry,
        config["frontier_budgets_bps"], config["tail_levels"], config["oi_fractions"], ["baseline"], check_duals=True)
    if not available:
        raise ValueError("Pilot lacks required robust-model support")
    sensitivity, _ = evaluate_date(config, chains, prices, cash, decision, expiry,
        [config["held_out"]["budget_bps"]], config["tail_levels"], config["oi_fractions"],
        config["robust"]["quote_rules"][1:])
    tables = {f"robust_{name}": table for name, table in pilot.items()}
    tables.update({f"quote_sensitivity_{name}": sensitivity[name]
                   for name in ("frontier", "positions", "candidates", "model_risks", "invariants")})
    date_rows, held_rows, held_positions, held_weights, held_support = [], [], [], [], []
    for row in qualifying_dates(coverage).itertuples():
        decision, expiry = pd.Timestamp(row.decision_date), pd.Timestamp(row.expiration)
        record = {"decision_date": row.decision_date, "expiration": row.expiration,
                  "matched": False, "reason": "menu_or_price_unavailable"}
        if not row.all_menus_available or not row.prices_present:
            date_rows.append(record)
            continue
        if decision not in prices.index or expiry not in prices.index:
            date_rows.append({**record, "reason": "market_snapshot_price_unavailable"})
            continue
        settings = config["held_out"]
        result, available = evaluate_date(config, chains, prices, cash, decision, expiry,
            [settings["budget_bps"]], [settings["tail_level"]], [None, settings["oi_cap"]], ["baseline"])
        held_support.append(result["support"])
        if not available:
            date_rows.append({**record, "reason": "insufficient_model_support"})
            continue
        scenarios = historical_scenarios(prices, cash, decision, expiry, config["lookback_years"])
        selected, _ = selected_contracts(chains, decision, expiry, ["TLT"])
        try:
            benchmark, _ = duration_hedge_benchmark(config, selected.iloc[0], scenarios, prices, cash,
                                                  decision, expiry, portfolio=config["portfolio"])
        except ValueError:
            date_rows.append({**record, "reason": "duration_benchmark_unavailable"})
            continue
        outcomes = result["frontier"].copy()
        outcomes["policy"] = outcomes.method + "__" + outcomes.menu
        benchmark = benchmark.loc[benchmark.tail_level.eq(settings["tail_level"])
            & benchmark.budget_bps.eq(settings["budget_bps"])
            & (benchmark.oi_fraction.isna() | benchmark.oi_fraction.eq(settings["oi_cap"]))].copy()
        for cell in benchmark.itertuples():
            outcomes = pd.concat([outcomes, pd.DataFrame([{
                "decision_date": row.decision_date, "expiration": row.expiration, "policy": "duration",
                "oi_fraction": cell.oi_fraction, "realized_net_loss_usd": cell.realized_net_loss_usd,
                "spent_usd": cell.spent_usd, "verified": True,
                "contracts": cell.contracts, "hedge_ratio_beta": cell.hedge_ratio_beta,
                "strike": cell.strike, "put_delta": cell.put_delta,
                "strike_spot_ratio": cell.strike_spot_ratio,
                "unhedged_realized_loss_usd": result["frontier"].unhedged_realized_loss_usd.iloc[0]}])], ignore_index=True)
        for cap in (None, settings["oi_cap"]):
            outcomes = pd.concat([outcomes, pd.DataFrame([{
                "decision_date": row.decision_date, "expiration": row.expiration, "policy": "unhedged",
                "oi_fraction": cap, "realized_net_loss_usd": result["frontier"].unhedged_realized_loss_usd.iloc[0],
                "spent_usd": 0.0, "verified": True,
                "unhedged_realized_loss_usd": result["frontier"].unhedged_realized_loss_usd.iloc[0]}])], ignore_index=True)
        held_rows.append(outcomes)
        held_positions.append(result["positions"])
        held_weights.append(result["weights"])
        date_rows.append({**record, "matched": True, "reason": ""})
    if not held_rows:
        raise ValueError("No common held-out dates with required model support")
    outcomes = pd.concat(held_rows, ignore_index=True)
    summary = []
    for (policy, cap), group in outcomes.groupby(["policy", "oi_fraction"], dropna=False):
        loss = group.realized_net_loss_usd / config["position_usd"] * 10000
        summary.append({"policy": policy, "oi_fraction": cap, "matched_dates": len(group),
                        "mean_loss_bps": float(loss.mean()), "worst_loss_bps": float(loss.max()),
                        "mean_spent_bps": float(group.spent_usd.mean() / config["position_usd"] * 10000),
                        "beats_unhedged": int(group.realized_net_loss_usd.lt(group.unhedged_realized_loss_usd).sum())})
    summary = pd.DataFrame(summary)
    if summary.matched_dates.nunique() != 1 or not outcomes.verified.all():
        raise ValueError("Unmatched or unverified robust held-out comparison")
    paired = outcomes.loc[outcomes.method.isin(["nominal", "robust"])].copy()
    paired["oi_label"] = paired.oi_fraction.fillna(-1)
    paired = paired.pivot(index=["decision_date", "menu", "oi_label"], columns="method",
                          values="realized_net_loss_usd").reset_index()
    paired["robust_minus_nominal_bps"] = (paired.robust - paired.nominal) / config["position_usd"] * 10000
    paired["robust_improved"] = paired.robust < paired.nominal - 1e-6
    paired["robust_worsened"] = paired.robust > paired.nominal + 1e-6
    paired["oi_fraction"] = paired.oi_label.replace(-1, np.nan)
    paired = paired.drop(columns="oi_label")
    tables.update(robust_held_out_outcomes=outcomes, robust_held_out_summary=summary,
                  robust_held_out_paired=paired,
                  robust_held_out_dates=pd.DataFrame(date_rows),
                  robust_held_out_positions=pd.concat(held_positions, ignore_index=True),
                  robust_held_out_weights=pd.concat(held_weights, ignore_index=True),
                  robust_held_out_support=pd.concat(held_support, ignore_index=True))
    return tables, {"formulation": "finite_model_max_cvar_separate_eta_and_excess_per_model",
                   "models": ["historical", "rate_selloff", "lqd_underperformance"],
                   "frontier_rows": len(pilot["frontier"]), "dual_checks": len(pilot["duals"]),
                   "matched_dates": int(summary.matched_dates.iloc[0]),
                   "model_family_invariants_verified": True, "duals_verified": True,
                   "scope": "conditional retrospective fixed-rule experiments, not executable performance"}


def phase3_report(config, tables):
    frontier = tables["robust_frontier"]
    settings = config["held_out"]
    view = frontier.loc[frontier.budget_bps.eq(settings["budget_bps"])
                        & frontier.tail_level.eq(settings["tail_level"]) & frontier.oi_fraction.isna()]
    scale = config["position_usd"] / 10000
    lines = ["", "## Phase 3: Finite-Model Design", "",
        "Conditional quote-based experiments; not executable depth or performance evidence.",
        "Uniform history plus fixed rate-selloff and LQD-relative-underperformance weights.",
        "Separate CVaR thresholds per model; robustness is only over these three models,",
        "not arbitrary distributions or mixtures. All windows end strictly before each decision.",
        "Rules are retrospective research assumptions, not historically preregistered policies.", "",
        f"Pilot {settings['budget_bps']:g}-bp budget, {settings['tail_level']:g} tail, no OI cap:", "",
        "| Menu | Method | Historical CVaR bps | Worst-model CVaR bps |",
        "|---|---|---:|---:|"]
    for row in view.itertuples():
        lines.append(f"| {row.menu} | {row.method} | {row.nominal_cvar_usd / scale:.2f} | "
                     f"{row.worst_model_cvar_usd / scale:.2f} |")
    lines += ["", "### Common Subsequent Outcomes", "",
        "One loss per expiration, no realized CVaR claim. All methods use the same successful dates.",
        "Positive robust-minus-nominal means robust did worse, including in ordinary periods.", "",
        "| Menu | OI cap | Dates | Robust improved | Robust worsened | Mean difference bps |",
        "|---|---|---:|---:|---:|---:|"]
    for (menu, cap), group in tables["robust_held_out_paired"].groupby(["menu", "oi_fraction"], dropna=False):
        label = "none" if pd.isna(cap) else f"{cap:g}"
        lines.append(f"| {menu} | {label} | {len(group)} | {group.robust_improved.sum()} | "
                     f"{group.robust_worsened.sum()} | {group.robust_minus_nominal_bps.mean():.2f} |")
    lines += ["", "### Verification and Sensitivities", "",
        f"- {len(tables['robust_duals'])} two-sided budget/OI-limit perturbation checks passed.",
        "- One-model equality, model-family bounds and menu/budget/access monotonicity checked.",
        "- Per-model objectives are recomputed from cash flows; LP residuals and feasibility are retained.",
        "- Quote sensitivities keep the baseline expiration: 20% spread, added zero-bid offers,",
        "  and 0.95–1.05 strike/spot. Empty direct menus remain unhedged, not reassigned a horizon.",
        "- OI constraints and duals are assumptions of a continuous LP, not market prices or executable depth.",
        "- Model support and weight concentration are reported; overlapping windows are not independent.",
        "- Deliverables, execution timing, and independent distribution validation remain unresolved.", ""]
    return lines
