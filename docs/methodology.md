# Hedge-Design Methodology

**Scope:** conditional listed-put protection for a fixed LQD portfolio. Numerical
verification is not contract validation, executable capacity or performance proof.
See [results](results.md) for evidence and [reproduction](../REPRODUCING.md) for commands.

## Inputs and Information Boundary

`study_config.json` identifies the complete experiment. Inputs are
local, hash-pinned chain and unadjusted-price files, plus the explicit Yahoo
price/action snapshot through January 2025. No scientific or reporting command
refreshes them. The broader source audit remains incomplete for cloud-only legacy
files; a successful hedge run does not certify those unrelated contents.

The local chain panel contains 80,521 rows, 36 ETFs and 22 quarterly snapshots,
2020-01-02 through 2025-04-01. It is not a daily execution history; HYG is absent.
Recorded OI is a stock, never cumulative volume or unsigned evidence of investor
intent. Missing/invalid OI and zero OI remain distinct.

The main pilot holds $100 million of LQD from January 2 to January 31, 2025.
The decision date is selected retrospectively for common quote-menu availability,
not performance or positive OI. One expiry is selected nearest 30 calendar days
within 21–60 days. Every menu keeps that expiry, including an empty menu.

Five years of strictly predecision joint historical windows supply the scenarios.
The pilot has 1,239 overlapping 19-session windows, ending no later than
2024-12-31. Joint LQD/TLT/IEF outcomes remain aligned. Overlap means these are not
1,239 independent observations. Historical market-data vintage and retrospective
research choices prevent a fully point-in-time or preregistered backtest claim.

## Cash Accounting

The initial LQD share count stays fixed; the portfolio is not sold to finance
the overlay. Portfolio window return is
`(end_close - start_close + distributions) / start_close`, using unadjusted closes.
Distributions on `(entry, expiration]` are retained without reinvestment or
interest; ex-date entitlements not yet paid at expiry are valued at par.
Historical price and distribution returns are scaled to current exposure.

For each put, intrinsic payoff is
`quantity * 100 * max(strike - terminal_close, 0)`.
The 100-share deliverable is an explicit, unverified contract assumption.
American puts are held to expiry; physical settlement is valued at its economic
intrinsic equivalent. Early exercise, exercise charges, settlement delays and
offsetting stock execution costs are not modeled.

Entry expenditure is `quantity * (100 * ask + 0.65)`. The overlay is externally
financed at an assumed annual simple 5%, actual calendar days divided by 365.
Net loss is unhedged portfolio loss minus put payoff plus financed entry cost.
Premium and financing are each counted once. The budget limits entry expenditure,
not a second deduction of the financed premium. Negative loss means a gain.

## Menus, Budgets and Access

Compare direct LQD puts, TLT/IEF Treasury substitutes and their union on identical
scenarios and expiry. Eligible strikes, bid/ask, entry spots, selected positions
and strike/spot ratios are retained. Spot reconciliation applies to every eligible
candidate, including subsequent-outcome experiments.

Continuous nonnegative contract quantities face budgets of 0, 10, 25, 50, 100 and
200 bps of initial portfolio value. Uncapped quantities are an optimistic model
benchmark. Limits of 1%, 5% or 10% of each contract's recorded OI are imposed
participation sensitivities, **not executable depth**. Unknown/invalid OI makes a
capped candidate unavailable; zero OI sets its cap to zero. Whole-contract
execution and market impact remain unvalidated.

Quote sensitivities keep the expiry fixed: tighten relative spread to 20%; add
only finite zero-bid/positive-ask offers; or restrict strike/spot to 0.95–1.05.
The last rule leaves the pilot's direct menu empty. No synthetic direct put or
different expiry fills that gap. Moneyness differences prevent interpreting the
baseline comparison as intrinsic cross-ETF hedge superiority.

## Nominal and Finite-Model CVaR

Nominal CVaR uses a free loss threshold and nonnegative excess-loss variables:
threshold plus weighted excess divided by `1 - alpha`, with alpha 90% or 95%.
SciPy HiGHS solves the sparse linear program over continuous put quantities.
The [scenario CVaR formulation](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf)
is a measurement tool, not a new methodological contribution.

Robust design shares the same positions and scenarios across three fixed models:

- Uniform historical weights.
- A 50/50 mixture of uniform weights and windows with TLT price return below -2%.
- A 50/50 mixture with windows where LQD return minus 0.5 times TLT return is below -1%.

The relative-underperformance rule is not an identified pure credit shock.
Thresholds and mixing weights are explicit retrospective assumptions, not tuned
against subsequent outcomes. Every model requires at least 30 qualifying windows;
an unsupported family is excluded as a whole.

Separate thresholds and excess variables constrain a common maximum-CVaR
objective. This protects against those three fixed distributions, not all possible
distributions or arbitrary mixtures. Compare both policies under historical and
worst-model CVaR. Effective weight count is a concentration diagnostic, not an
independent sample size.

## Benchmarks, Evaluation and Verification

A frozen duration-rule TLT-put hedge uses past-data return exposure estimates
and the nearest eligible ATM put under the same budget and OI constraints.
A TLT-held direct-put control protects a different portfolio; it is not an LQD
alternative. The no-cap scale control checks a model's percentage invariance,
not practical capacity at different investor sizes.

Six optimizer policies, duration and unhedged benchmarks share 16 supported
subsequent-outcome dates, both uncapped and under a 5%-OI assumption. Positions
are frozen before expiration outcomes are evaluated. Common-date intersections,
exclusions, model support, positions and paired gains/deteriorations are saved.
One outcome per clustered snapshot does not support a realized-CVaR estimate
or establish robust superiority.

Scientific checks independently reconstruct objectives from positions and loss
scenarios; test budgets, bounds and raw inequalities; and enforce menu/budget/OI
monotonicity, one-model equivalence and model-family bounds. Two-sided 0.1%
budget and proportional-OI perturbations validate dual sensitivities, using
subgradient brackets at kinks and a $1 objective tolerance. Duals are local LP
sensitivities, not market prices. Failures prevent publication of a scientific run.

Reporting verifies saved artifacts and reconstructs common-date summary statistics.
The notebook only displays saved tables/figures and never duplicates accounting,
optimization or acquisition. Input/code/version hashes identify each run.

Before stronger claims: verify contract deliverables, quote/OI timing and execution,
and distributions independently; expand empirical coverage and assess data vintage
and practical sizing. Detailed implementation-era specifications remain in the
[recoverable research history](../legacy/unified/docs/archive/README.md), not the main reading path.
