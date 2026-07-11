# Paper Sketch — The Missing Hedge Market

Revision of 2026-07-10. Supersedes the chat-circulated draft: incorporates the
wild-cluster bootstrap results (Section 7 second act, abstract), corrects the
TLT AUM figure ($54B, not $80B), and adds the JNK accounting detail, the LQD
depth-evaporation paragraph, the √-notional liquidity screen, and the American
repricing robustness note.

---

## Title

*The Missing Hedge Market: Listed Option Capacity in Fixed-Income ETFs*

Alternative (retains prior working title): *Hedge Capacity and Drawdown Risk in
Fixed-Income ETFs*

---

## Abstract

Listed options on fixed-income ETFs are the only exchange-traded instrument
offering limited-loss, basis-specific protection against bond ETF price risk.
We ask whether this market can actually perform that function. Using quarterly
option chain snapshots for 36 bond ETFs (2020–2025, calls and puts with open
interest), we translate option Greeks into rate-space exposures and construct a
hedge capacity ratio: the fraction of each fund's aggregate rate DV01 that the
quality-screened option book could offset. The answer is that the hedge market
largely does not exist. The entire put book on TLT — the single
institutional-scale venue — covers approximately 3.5% of TLT's own fund DV01;
at realistic open-interest participation, listed puts could hedge a $100–200
million position against a $54 billion fund. LQD carries zero quality put-side
depth against $25 million per basis point of fund exposure; credit and
aggregate ETF hedging via listed options is effectively unavailable. Moreover,
the depth that does exist is not hedging demand: call-side DV01 exceeds
put-side by 2.6:1 on TLT and by two orders of magnitude on some funds,
consistent with covered-call and yield-enhancement flow. Consistent with a
market this shallow and one-sided, option-derived variables carry no
forward-looking information: implied volatility gaps do not predict drawdowns
or returns, and within-fund variation in hedge capacity does not predict
outcomes. A naive cross-sectional regression does produce a significant
capacity–drawdown association, but it fails twice under scrutiny. A Mundlak
decomposition shows it is entirely between-fund composition — deep option
markets sit on long-duration funds that drew down hardest in the 2022 rate
cycle — and it vanishes under ticker or even duration-bucket fixed effects.
And even the between-fund association does not survive inference that respects
the small number of funds: wild-cluster bootstrap p-values (32 ticker
clusters) rise to approximately 0.25 for both the pooled and between-fund
coefficients. The only estimate robust to both decomposition and few-cluster
inference is the call-side capacity channel (bootstrap p ≈ 0.03) — the
signature of yield-enhancement flow, not protection. The listed bond ETF
options market is best understood not as a risk-transfer mechanism awaiting
measurement, but as a yield-enhancement venue whose hedging function is
largely notional.

---

## 1. Introduction

The fixed-income ETF market holds several trillion dollars of duration and
credit exposure, and its fragility during stress episodes — most acutely the
2022 rate cycle — is well documented. For investors whose exposure is to the
ETF price itself, listed options on these funds are the only exchange-traded
instrument offering limited-loss, basis-specific protection: futures hedge
rates but not the ETF basis; swaptions are OTC and rate-only; credit
derivatives require ISDA infrastructure and hedge only the spread component.
If bond ETF tail risk is insurable on-exchange at all, it is insurable here.

This paper asks a question that is prior to any pricing or prediction
question: does this market have the capacity to perform its nominal function?
The question has not been answered because the natural measurement — how much
of a fund's rate exposure the standing option book could absorb — requires
translating option Greeks into the units of the underlying bond exposure,
which the literature has not done for this market.

We construct that translation. Using empirical rate durations estimated from
each ETF's return sensitivity to Treasury yields, we convert per-contract
dollar Greeks into rate-space exposures (rate DV01, rate convexity, rate
carry) and aggregate the quality-screened, open-interest-weighted chain into a
hedge capacity ratio: chain rate DV01 as a fraction of fund rate DV01. An
algebraic property makes this measure unusually robust: because the options
are written on the same ETF whose duration defines the hedge target, the
duration estimate cancels in the ratio, which reduces to delta-adjusted
open-interest notional as a share of fund AUM. The ratio is therefore immune
to duration-estimation noise — the noisiest input survives only in the
absolute exposure measures, not in the headline capacity metric.

Three findings emerge, and together they invert the premise of the exercise.

First, measured capacity is negligible almost everywhere (Section 4). TLT is
the only institutional-scale venue, and even there the entire quality put book
covers roughly 3.5% of the fund's own DV01. Outside TLT, put-side depth is
retail-scale (IEF, TIP) or literally zero (LQD, AGG, BND, EMB). For credit and
aggregate ETFs — precisely the categories where alternative instruments are
weakest — listed option hedging does not exist.

Second, the depth that exists is the wrong kind (Section 5). The standing book
is heavily call-sided — 2.6:1 by DV01 on TLT, approaching 100:1 on MBB — which
is the signature of covered-call and yield-enhancement writing, not protective
demand. The market's anatomy reveals its function: it is a venue where ETF
holders sell upside for income, not where they buy downside protection.

Third, consistent with a market too shallow and mis-composed to aggregate risk
information, option-derived variables are uninformative (Section 6). The
implied–realized variance gap predicts neither forward drawdowns nor returns
in any specification. Within-fund variation in hedge capacity predicts
nothing. A naive pooled regression does yield a significant capacity–drawdown
association, but we dissect it in Section 7 and it fails on two independent
grounds: identification (a Mundlak decomposition shows it is entirely
between-fund composition, and it disappears under ticker or even coarse
duration-bucket fixed effects) and inference (wild-cluster bootstrap p-values,
which respect the fact that there are only 32 funds, eliminate both the pooled
and the between-fund significance). The single coefficient that survives both
is call-side capacity — corroborating the anatomy, not the hedging
hypothesis. We report this autopsy in full because the naive specification is
the one a researcher would run first, and both failure modes are instructive.

[Instrument-landscape paragraph — retain the existing TLT five-instrument
discussion from the current draft introduction, lightly trimmed; its role is
now to establish that listed ETF options are the *only* candidate venue for
basis-specific protection, which is what makes the capacity finding
consequential rather than merely descriptive.]

The paper proceeds as follows. Section 2 describes the data, the quality
screen, and empirical duration estimation. Section 3 develops the rate-space
translation and the hedge capacity ratio, including the cancellation identity.
Section 4 presents the capacity accounting. Section 5 documents book
composition. Section 6 presents the informational nulls. Section 7 dissects
the between-fund association. Section 8 concludes.

---

## 2. Data and Measurement

### 2.1 Sample

Quarterly option chain snapshots for 36 fixed-income ETFs, 2020-Q1 through
2025-Q2 (22 snapshot dates), calls and puts with per-contract open interest,
from ThetaData. A weekly ATM 30-day IV panel (2020–present) supports the
informational tests, constructed with a combined call/put method validated on
231 matched quarterly call/put pairs (median absolute IV gap 0.0086, p90
0.0233). Underlying returns, forward outcomes (fwd_maxdd_12w, fwd_ret_4w,
fwd_vol_12w), and macro controls come from the companion 347-ETF bond
fragility panel (read-only join).

The universe spans long/intermediate/short Treasury, investment-grade
corporate, high yield, broad aggregate, emerging market, and specialty
categories. [Universe table: `tables/universe.csv`.]

### 2.2 Quality screen and liquidity classification

A contract enters the analysis only if it is plausibly tradeable and
economically meaningful: relative bid-ask spread ≤ 0.35, DTE in [14, 90], |Δ|
in [0.10, 0.90], and dollar-Greek floors on dollar delta, dollar gamma, and
dollar vega. Thresholds are held constant across the sample. The screened
chain file contains 80,521 contract-rows. All capacity results are therefore
upper bounds with respect to tradeability in a specific sense: every quality
contract's full open interest is treated as usable, with no price impact —
the true hedgeable amount is smaller.

Ticker-level liquidity classification (used to scope the IV panel and the
hedgeability scores; the capacity accounting always covers all 36 funds) uses
a family of screeners each of the form √N × g, where N is quality
open-interest premium notional and g ∈ (0, 1] is a depth-free quality
multiplier: pure depth √N; cost-adjusted depth √N × (1 − median spread); and
balance-adjusted depth √N × 2·min(putN, callN)/(putN + callN). Every screener
is monotone increasing in √N — deeper standing books never classify as less
liquid — while the composite gate (all three multipliers) prevents large but
stale, wide, or one-sided books from qualifying. Eight funds pass: TLT, LQD,
IEF, EMB, TIP, EDV, ZROZ, VCLT.

Robustness note (American exercise): all IVs and Greeks are computed under
European BSM although ETF options are American-style with 3–5% dividend-yield
underlyings. Repricing all 80,521 contracts on a 751-step CRR tree shows the
median European-assumption IV bias is approximately zero across ticker × right
× moneyness buckets; the apparent tail cases trace to stale deep-ITM quotes
below the American early-exercise bound rather than systematic model bias
[`tables/american_bias.csv`]. One footnote in the final draft.

### 2.3 Empirical rate duration

For each ticker, weekly returns are regressed on weekly changes in the 10-year
Treasury yield; D_i is the negated slope, positive for long-duration funds. A
quality gate (regression R² ≥ 0.20 and |D_i| ≥ 1.0) governs the absolute
exposure measures; 104 of 521 ticker-snapshot pairs fail and receive NaN in
the absolute DV01/convexity/carry fields. The capacity ratio is unaffected by
gate failures via the cancellation identity below. Estimated durations
validate against published effective durations with correlation 0.98
[`figures/26_duration_validation.png`].

---

## 3. From Dollar Greeks to Hedge Capacity

### 3.1 Rate-space translation

Because dS/S = −D_i · dy for an ETF with empirical duration D_i, each
contract's price-space Greeks map to rate-space exposures:

    rate_dv01_c  = D_i · S · |Δ_c| · 0.0001 · 100          (dollars per 1bp, per contract)
    rate_conv_c  = 0.5 · D_i² · S · (Δ_c + S·Γ_c) · (0.0001)² · 100
    rate_carry_c = |θ_daily,c| / rate_dv01_c

The fund-level hedge target is fund_dv01_i = D_i · AUM_i · 0.0001.

### 3.2 The hedge capacity ratio and the cancellation identity

Aggregating quality contracts with open-interest weights, by side:

    hedge_capacity_ratio = Σ_c (rate_dv01_c · OI_c) / fund_dv01_i
                         = 100 · S · Σ_c (|Δ_c| · OI_c) / AUM_i

The second equality is the cancellation identity: D_i appears in both
numerator and denominator because the options are written on the same ETF
whose duration defines the target, so the ratio reduces to delta-adjusted
open-interest notional as a share of AUM. This is the correct "fraction of
duration exposure hedgeable" and is robust to duration-estimation noise. D_i
does not cancel in the absolute exposures (rate_dv01, rate_conv) or in carry,
which is where duration structure remains informative. Measured carry across
the chain is approximately $0.0025 per day per dollar-per-basis-point of
protection — kinder than an ATM put roll, since the chain-wide figure includes
cheaper wings.

[Methodological note: this identity also clarifies what the measure is and is
not. It is a depth measure — how much delta-notional stands open relative to
fund size — given economic meaning by the rate-space derivation. It is not a
model-dependent quantity. In the replication package the identity is enforced
by the type system: the Julia implementation types rate DV01 as USD·bp⁻¹ and
the capacity ratio is dimensionless and provably D_i-invariant.]

---

## 4. The Capacity Accounting: A Market That Mostly Is Not There

This section is the core of the paper: a fund-by-fund accounting of put-side
hedge capacity at a representative recent snapshot (2025-04-01), quality
contracts only, with cross-snapshot min/median/max columns establishing that
the shape is stable across all 22 snapshots.

TLT is the only institutional venue. Its put-side chain rate DV01 is $2.93
million per basis point — the entire quality put book, if fully deployed,
hedges approximately a $1.9 billion position. At a realistic 5–10%
participation in standing open interest, the hedgeable position is $100–200
million — against a fund with $83 million per basis point of aggregate DV01.
The entire put book represents about 3.5% of TLT's own fund DV01. Median
quality-put spread: 4.9% of premium.

Everything else is retail-scale or zero. IEF put-side depth of $27 thousand
per basis point supports roughly a $36 million hedged position; TIP, $13
thousand per basis point (~$33 million); spreads run 9–13% of premium. JNK — a
$10 billion high-yield fund — has a put book whose entirety hedges a position
of approximately $15,000. LQD — a fund with $25 million per basis point of
rate exposure — has zero quality put-side DV01 at the snapshot. AGG, BND, and
EMB are likewise approximately zero. The categories where the
instrument-substitution argument of Section 1 is weakest, credit and
aggregate, are exactly where listed hedging capacity is absent entirely.

**[Table: `tables/capacity_accounting.csv` — put-side chain rate DV01, implied
hedgeable position at 100% and at 10% OI participation, fund DV01, capacity
ratio, median spread, cross-snapshot put-DV01 min/median/max — sorted by fund
DV01.]**

**[Figure: `figures/24_missing_market.png` — hedgeable position vs fund AUM,
log-log with 100%/10%/1%/0.1%-of-fund reference diagonals.]**

Interpretation is deliberately conservative in both directions: capacity as
measured is an optimistic upper bound (full OI usable, no price impact, EOD
quotes), and OI is a stock rather than a flow. Even the upper bound is
negligible.

---

## 5. Anatomy of the Book: Yield Enhancement, Not Hedging

If the option market existed to insure bond ETF risk, put depth should
dominate or at least match call depth. The opposite holds. On TLT, call-side
DV01 exceeds put-side 2.6:1; on MBB the ratio approaches 100:1. No fund with a
two-sided book is put-dominant. Across the universe, standing depth is
concentrated on the call side in patterns consistent with covered-call and
yield-enhancement writing by ETF holders — supply of upside, not demand for
downside.

The composition is also unstable where it matters most for the hedging
interpretation. LQD classifies as liquid on the 2020–2025 median — its option
market was genuinely active mid-sample — yet carries zero quality put-side
depth at the 2025-04-01 snapshot: the one credit fund with a real options
market saw its put side evaporate within the sample. Depth that exists on
average cannot be presumed available when needed.

This composition finding does interpretive work in both directions. Backward:
it explains why the market's depth sits where it does (on large, widely-held
funds whose holders sell calls for income) rather than where hedging demand
would put it (on fragile credit funds). Forward: it sets up the informational
nulls — a book composed of yield-enhancement flow has no mechanism for
impounding forward-looking risk information, and Section 6 confirms none is
impounded. It also anticipates Section 7's resolution: the only regression
coefficient that survives full scrutiny is the call-side channel, which is
what a yield-enhancement market should produce.

Caveat, stated plainly: composition is inferred from the standing book's skew,
not from signed volume; OI is a stock. The inference is strong because the
skew is large and systematic, but it is an inference.

**[Table/Figure: `tables/call_put_dv01_ratio.csv`,
`figures/25_call_put_ratio.png` — call-to-put DV01 ratio by fund; call-only
and put-only books listed separately.]**

---

## 6. Informational Nulls: Prices and Capacity Predict Nothing

Two families of option-derived variables, two clean nulls, presented
compactly. Inference throughout uses CGM (2011) two-way clustered errors
(ticker × date); the headline specifications additionally report wild-cluster
bootstrap p-values (Rademacher weights, 9,999 replications, ticker clusters),
which are the appropriate inference with 32 funds.

Prices: the implied–realized variance gap (IVRVG) predicts neither forward
12-week maximum drawdown, forward 4-week returns, nor forward realized
volatility, in any specification (levels, duration interactions,
duration-scaled). [Condensed table, specs 1–7 from the notebook.]

Capacity, within fund: changes in hedge capacity over time within a fund carry
no predictive content for forward outcomes (the within component of the
decomposition in Section 7: +0.063, CGM p=0.34, bootstrap p=0.73).
Fresh-capacity-only (snapshot age ≤ 30 days) and snapshot-week-only subsamples
are likewise null.

These nulls are presented not as failed hypotheses but as corroboration: a
market of this scale and composition has neither the depth to aggregate
dispersed risk information nor a participant base positioned to trade on it.
The absence of signal is what the anatomy predicts.

Caveat: 22 quarterly snapshots limit within-fund power. The within-null is "no
detectable signal," not proof of zero.

---

## 7. The Between-Fund Artifact: An Autopsy in Two Acts

A researcher who regressed forward drawdowns on hedge capacity with date fixed
effects — the natural first specification — would find a significant negative
coefficient (−0.269, CGM SE 0.094, p=0.0042) and might conclude that
option-market depth is associated with — perhaps protects against, perhaps
signals — future drawdowns. We document why that conclusion fails, twice, in
the spirit of making both failure modes reusable knowledge.

**Act one: identification.** The association is entirely between funds. Adding
ticker fixed effects eliminates it (−0.012, p=0.96); two-way FE flips the sign
(ns); even coarse duration-bucket fixed effects kill it (−0.033, p=0.76). The
Mundlak decomposition is dispositive: the between-fund component is −0.437
(CGM p=0.0009) while the within-fund component is +0.063 (p=0.34). The
gradient is not an outlier artifact — it survives 1/99 winsorization and log
transformation — and it is not universe-wide: dropping TLT, LQD, and IEF
renders it insignificant, so three liquid funds carry the precision. The
composition mechanism is transparent given Sections 4–5: option depth
concentrates on long-duration Treasury funds; long-duration funds experienced
the deepest drawdowns of the 2022 rate cycle; the pooled regression reads that
composition as a capacity effect.

**Act two: inference.** Even the between-fund association, taken on its own
terms as a cross-sectional fact, does not survive inference that respects the
effective sample size. The regressor of interest is constant (or slow-moving)
within fund, so the informative sample is not 8,515 fund-weeks but 32 funds —
of which roughly eight have economically meaningful capacity. Wild-cluster
bootstrap p-values (Rademacher, 9,999 replications, clustered by ticker) rise
from 0.0042 to 0.25 for the pooled coefficient and from 0.0009 to 0.25 for the
Mundlak between-fund component. The asymptotic CGM stars were an artifact of
treating a 32-cluster problem as an 8,515-observation one.

One coefficient survives both acts: call-side capacity in the call/put horse
race (−0.313; CGM p=0.0001, bootstrap p=0.030), while put-side capacity is
null under every treatment (bootstrap p=0.84). This is the final tell, and it
closes the loop with Section 5: a genuine hedging channel would run through
puts; the channel that actually survives runs through the covered-call side of
the book. The regression evidence, once honestly decomposed and honestly
inferenced, says exactly what the book's anatomy says.

**[Table: full robustness ladder with both p-value columns —
`tables/robustness_spec0.csv` (CGM) joined with `tables/robustness_boot.csv`
(bootstrap); reproduced by notebook Section 10.]**

---

## 8. Conclusion

The listed options market on fixed-income ETFs is nominally the only
exchange-traded venue for limited-loss, basis-specific protection against bond
ETF price risk. Measured properly — Greeks translated to rate space,
aggregated over the tradeable book, compared to fund-level exposure — that
venue barely exists. One fund offers institutional-scale put capacity, and
even there the entire book covers 3.5% of the fund's own rate exposure. The
depth that exists is call-sided yield-enhancement flow, and the one credit
fund that briefly had a real options market watched its put side evaporate
within the sample. Option prices and capacity dynamics carry no
forward-looking information, which is what the anatomy predicts. The one
significant regression a naive researcher would find fails on identification
(it is between-fund composition) and then fails again on inference (it does
not survive wild-cluster bootstrap with 32 funds); the only surviving
coefficient is the call-side channel — the market's yield-enhancement
signature, not its hedging function.

Three implications. For risk managers: listed bond ETF options are not
currently a viable hedging channel at institutional scale outside a narrow use
of TLT puts, and sizing assumptions built on listed-option overlays for credit
or aggregate exposure are assumptions about a market that does not exist. For
market-structure questions: the fragility literature's stress-transmission
channels (AP capacity, liquidity mismatch) operate in a market where the
tail-risk-transfer mechanism that options nominally provide is absent — the
missing hedge market is a missing shock absorber. For empirical practice:
cross-sectional associations between market-development measures and outcomes
should be decomposed before interpretation, and inferenced at the level of the
cross-sectional unit; ours vanished within fund, and then vanished again at
the fund level under bootstrap.

Limitations: one rate cycle (2020–2025); 22 quarterly snapshots (limited
within-fund power); EOD quotes; OI as stock not flow; capacity as optimistic
upper bound. Future work: flow-based composition using signed volume; intraday
tradeability; whether the 2022 stress episode *created* option-market
development with a lag; and the OTC side — whether dealer-intermediated bond
ETF options fill the gap the listed market leaves.

---

## Empirical source map

All regression numbers from `notebooks/05_options_analysis.ipynb` (Section 10
= robustness ladder + bootstrap join; Section 11 generates the paper tables
and figures). Tables regenerate to `docs/options_paper/tables/`: capacity
accounting, call/put ratio, duration validation, universe, robustness ladder
(`robustness_spec0.csv`), wild bootstrap (`robustness_boot.csv`), American
bias (`american_bias.csv`). Figures 24–26 in `docs/options_paper/figures/`.
Julia replication layer in `julia/` (RateSpace.jl: AD Greeks with
machine-precision parity to the Python reference on all 80,521 contracts;
wild-cluster bootstrap; CRR American repricing) — file-exchange only, repo
reproducible without it. Sample: chains.csv 80,521 rows; options_panel.csv
18,074 ticker-weeks; capacity non-null on 8,515 regression obs / 32 tickers;
liquid set under the √-notional gate: 8 funds. State as of 2026-07-11 (canonical offline core panel: 156,588 rows built by
scripts/rebuild_panel_from_legacy.py from pinned inputs; stress index now
includes S&P realized vol as a fifth component); tests 155 passed / 4
skipped (Julia and live-API tests opt-in). Full pipeline: scripts/reproduce.py.

Before submission: refresh `ETF_METADATA` AUM/durations from current fact
sheets (the capacity accounting table inherits their precision) and rotate the
FRED/ThetaData credentials.
