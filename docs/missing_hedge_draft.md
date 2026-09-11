# The Missing Hedge: Cost and Conditional Protection in Listed Bond-ETF Options

Travon Lucius

**Research draft — conditional evidence, September 2026.** This is a separate,
reproducible migration draft, not a replacement for `legacy/unified/docs/draft.md`. Table and
metric placeholders are filled by `scripts/reproduce_hedge_paper.py`; read the
generated copy alongside its figures. Scientific run: `{{metric:run_id}}`.

## Abstract

For a fixed bond-ETF allocation, the existence of listed puts does not establish
that comparable downside protection is available at the desired size and cost.
We measure this distinction using observed option menus and constrained
conditional value-at-risk (CVaR) hedge design. The pinned local panel contains
{{metric:chain_rows}} contract rows across {{metric:etfs}} ETFs and
{{metric:snapshots}} quarterly snapshots. A conditional $100 million LQD
experiment compares direct LQD puts, TLT/IEF substitutes, and their union at
one common expiration. Treasury substitutes reduce historical-model tail loss
more than the observed direct menu, but the available strikes are not
moneyness-matched and recorded-OI constraints materially change the comparison.
A finite-model robust extension exchanges historical-model protection for
protection against specified alternative weights. Its subsequent outcomes are
mixed across menus and access assumptions. These results measure the dependence
of modeled protection on the observed menu, budget and risk model; they neither
establish executable capacity nor demonstrate robust hedge superiority.

## 1. The Investor's Question

An allocator wishing to retain credit exposure cannot solve a hedge problem
simply by liquidating the bond allocation. The practical question is what
downside protection can be added, for a specified expenditure and position size,
without changing the portfolio being protected. Direct options may be available
only at unattractive strikes; Treasury options may be more useful in rate-led
losses but leave relative credit losses insufficiently covered. The relevant
comparison therefore holds the investment, horizon, prices, scenarios, fees and
budget fixed while changing the option menu.

Our contribution is a transparent measurement exercise, not a new optimization
method. The term “missing hedge” describes a possible gap between the protection
an investor wants and what the observed listed menu can deliver under explicit
assumptions. It is not a maintained hypothesis that all bond-ETF downside markets
are missing. Treasury futures/options, OTC instruments and portfolio replacement
are outside this comparison. The local sample does not include HYG, so the
experiment does not characterize the entire credit-ETF market.

## 2. Observed Market Anatomy and the Comparison Set

The identified chain file spans {{metric:first_snapshot}} through
{{metric:last_snapshot}}. Each snapshot is a cross-section, not a daily trading
history. Recorded open interest is a stock: it is not trading volume, a dealer
offer to transact, or evidence of investor motive. Calls and puts are shown
separately rather than treating a large call book as direct evidence of put
protection. The anatomy table retains missing/invalid and zero OI separately;
it does not aggregate repeated snapshot OI into a cumulative capacity measure.

![Recorded calls and puts in the three pilot ETFs](figures/market_anatomy.png)

**Figure 1.** Recorded OI for LQD, TLT and IEF on January 2, 2025, including all
strikes and expirations in the pinned chain. This descriptive book is broader
than the quote-eligible, common-expiration put menu used for hedge design.
`tables/market_anatomy.csv` provides every date/ETF/side, including invalid-OI
counts; the figure is not an execution assessment or a claim about all ETFs.

The main pilot uses January 2, 2025 as the decision date and January 31 as the
expiration. This decision date is selected retrospectively as the latest audited
snapshot supporting all three quote menus under the common-expiration rule.
Historical comparisons use the same deterministic nearest-30-day expiration rule
within 21–60 days. Empty menus remain empty rather than receiving an alternate
expiry or a fabricated near-the-money contract.

{{table:moneyness}}

**Table 1.** Quote-eligible puts at the pilot expiry; strike divided by entry spot
is dimensionless. These are candidates, not all selected contracts. All eligible
LQD puts have zero recorded OI, and their strikes lie well above spot. Consequently,
a baseline direct-versus-Treasury result combines instrument substitution with
observed moneyness differences and cannot identify intrinsic ETF hedge superiority.

![Candidate strike-to-spot ratios](figures/moneyness.png)

**Figure 2.** Each mark is an eligible strike, not a position size or a liquidity
weight. The shaded 0.95–1.05 band is a separate sensitivity. The direct LQD menu
is empty inside that band at this expiry.

## 3. Fixed-Portfolio Cash Accounting and Hedge Design

The portfolio begins with $100 million of LQD and retains its initial share
count. For each joint scenario, portfolio terminal value uses the unadjusted
price plus explicit distribution cash. Option intrinsic payoff uses unadjusted
underlying prices, not a total-return-adjusted settlement level. Long puts are
held to expiration under an assumed standard 100-share deliverable. Physical
delivery is represented by its economic intrinsic equivalent; early exercise
and operational settlement choices are not modeled.

Entry expenditure is ask premium times the assumed multiplier plus $0.65 per
contract. It is charged once, and financed once at an assumed annual simple 5%
rate on actual calendar days divided by 365. Budgets constrain entry expenditure,
not a second deduction of financed premium. Net loss equals the fixed portfolio's
unhedged loss, less option payoff, plus financed entry expenditure. Negative loss
means a gain. No option dividends or premiums are counted twice. Portfolio
distribution cash follows the pinned accounting convention; independent issuer
validation remains outstanding.

The main design set contains {{metric:scenario_count}} overlapping joint windows
of {{metric:sessions}} trading sessions, with last training end
{{metric:training_end}}, strictly before the decision date. Each window preserves
the joint LQD/TLT/IEF outcome. Overlapping windows are not independent observations,
and a large window count does not guarantee precise tail estimation.

Nominal CVaR uses the scenario threshold/excess-loss formulation of
[Rockafellar and Uryasev, *Optimization of Conditional Value-at-Risk*](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf).
For a tail level alpha, the criterion is a free threshold plus the weighted
positive loss above that threshold divided by one minus alpha. Minimization is
a linear program in nonnegative continuous contract quantities. Budget and
optional per-contract recorded-OI fractions constrain positions. Both 90% and
95% tail levels are retained. SciPy's
[HiGHS interface](https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html)
solves the sparse linear programs; the saved run records the installed versions.

Uncapped allocation is an optimistic design benchmark, not unlimited real access.
The 1%, 5% and 10% OI treatments are imposed participation sensitivities rather
than estimated executable depth. Fractional contracts are a continuous relaxation;
integer execution and price impact are not certified. In the uncapped model,
percentage frontiers are scale-invariant; investor size matters once absolute
contract limits bind. The saved scale-control table checks this mathematical
property, not observed capacity at every investor size.

## 4. Cost–Protection Frontiers and Substitution

![Nominal cost–protection frontiers](figures/nominal_frontiers.png)

**Figure 3.** In-sample historical-model net-loss CVaR versus upfront budget, in
basis points of the same $100 million exposure. Panels retain 90%/95% tails and
uncapped/5%-OI assumptions. All menus use identical scenarios and expiry. The
machine-readable table includes the other OI fractions and both design methods.
Overlapping lines are genuine near-equality, not missing series.

The uncapped Treasury menu substantially improves the historical-model frontier
relative to the observed direct menu. The combined menu can never be worse than
a constituent menu under the same objective because it contains both feasible
sets. That nesting property is checked numerically; it is not empirical evidence
of additional economic value. Conversely, the all-zero recorded OI of eligible
LQD puts makes every positive-OI-fraction direct allocation unavailable under
the imposed caps. This illustrates why quote existence, model protection and
assumed access must be reported separately.

A frozen duration-rule TLT-put hedge supplies a non-optimized reference, using
only past-data return exposure estimates and the nearest eligible ATM contract.
It faces the same expenditure and OI constraints. A separate TLT-held direct-put
positive control tests a portfolio directly spanned by its own options; its loss
levels are not an apples-to-apples alternative to holding LQD. Detailed control
and scale tables accompany the notebook rather than being used to inflate the
main substitution claim.

## 5. Finite-Model Protection Is a Trade-Off

The robust extension uses the same scenarios and contract constraints but three
fixed weight vectors: uniform historical weights; a 50/50 mixture of uniform
weights and windows with TLT price return below -2%; and a 50/50 mixture with
windows where LQD return minus 0.5 times TLT return is below -1%. The latter is
a relative-underperformance proxy, not an identified pure credit shock. These
rules were specified retrospectively for this research, not preregistered by a
historical investor, and are not tuned to subsequent outcomes in this code.

{{table:support}}

**Table 2.** Historical model support and weight-concentration diagnostics.
Effective weight count is not an independent sample size. A minimum of 30
qualifying windows per model is required; unsupported families are excluded as
a whole rather than silently dropping an adverse model.

Separate threshold and excess-loss variables for each model constrain a common
epigraph objective. The hedge minimizes the largest of these three model CVaRs,
not CVaR over every possible distribution or arbitrary mixture. Both nominal
and robust policies must therefore be compared under both risk measures.

{{table:design_comparison}}

**Table 3.** Same policies evaluated under historical and worst-model CVaR: 50 bp
budget, 90% tail, uncapped quantities. All risk and expenditure columns are bps
of the initial portfolio, not annualized returns.

![Nominal and robust policies under both risk measures](figures/model_tradeoff.png)

**Figure 4.** The combined robust policy improves its specified worst-model
criterion at the cost of worse historical-model CVaR. A lower robust objective
is a model-specific design result, not a free improvement or a performance claim.

Every solved objective is independently recomputed from positions and scenario
losses. Budget, quantity bounds, raw inequalities, one-model equivalence and
menu/model-family invariants are checked. Two-sided budget and proportional-OI
perturbations validate local dual sensitivities using subgradient brackets at
kinks. Duals are marginal values inside this model, not market prices.

## 6. Common Subsequent Outcomes and Quote Sensitivity

All eight policies—six menu/method combinations, duration and unhedged—are
evaluated on {{metric:matched_dates}} common supported decision dates under both
uncapped and 5%-OI assumptions. Training ends precede each decision; positions
are frozen before subsequent expiration outcomes are evaluated. Exclusions and
support diagnostics remain visible. Common dates prevent policy comparisons
from benefiting merely by dropping different difficult observations.

{{table:outcomes}}

**Table 4.** Common-date net-loss summaries in bps. Negative means gains. Worst
loss is the maximum observed loss in this small sample, not a population bound.
`beats_unhedged` counts dates, not a statistical test. Zero mean expenditure for
unhedged policies does not imply zero portfolio risk.

![Every paired subsequent outcome](figures/paired_outcomes.png)

**Figure 5.** Robust minus nominal loss on every matched date, separated by menu
and OI assumption. Positive differences mean robust design loses more. These
are isolated holding periods, not a compounded wealth series or rolling strategy.

Results are mixed. The uncapped combined policy has a better sample mean and
worst loss under robust design, while the uncapped Treasury-only robust policy
worsens both summaries. Under the 5%-OI assumption, robust combined and Treasury
policies also worsen these summaries. Sparse, regime-clustered snapshots do not
establish robust superiority or provide a defensible realized-CVaR estimate.
The historical data vintage and retrospective research choices also preclude
describing this exercise as a fully point-in-time, preregistered backtest.

![Sensitivity to quote eligibility and moneyness](figures/quote_sensitivity.png)

**Figure 6.** Nominal historical-model CVaR at the same expiry, 50 bp budget,
90% tail and no OI cap. Rules tighten relative spread to 20%, add only finite
zero-bid/positive-ask offers, or restrict strike/spot to 0.95–1.05. The empty
matched-moneyness direct menu reproduces unhedged loss; it is not missing data.
Saved tables also retain robust design, 95% tails and every OI assumption.

## 7. Interpretation, Validation Gates and Reproduction

The practical lesson is to specify the intended hedge, position size and access
assumptions before treating listed-option availability as portfolio protection.
The observed cross-ETF substitution result is conditional on moneyness, quote
eligibility and joint-risk weights. This draft does not infer covered-call intent
from unsigned OI, extrapolate market-wide completeness, or use one snapshot as
performance evidence.

Publication requires contract-level deliverable verification, synchronized quote
and OI timestamps with execution assessment, and independent distribution/action
validation. Broader repeated-date and market coverage, sensitivity to data vintage,
and integer/execution feasibility remain additional research work. The incomplete
legacy source inventory is a separate reproducibility limitation, not repaired by
successful numerical checks. Legacy regression claims are not dependencies of
this draft and are not carried forward as newly verified findings.

One explicit command runs the pinned robust configuration, verifies scientific
inputs/code/dependencies/results, produces this draft and its tables/figures, and
executes a saved-results-only notebook. Each build refuses overwrite and records
source and artifact hashes. The notebook never fetches data, solves a hedge, or
reimplements cash accounting. See the repository's `REPRODUCING.md` for commands
and `docs/methodology.md` for the accounting specification.
The original draft and notebook 05 remain preserved pending a separate narrative
reconciliation after review of this evidence.
