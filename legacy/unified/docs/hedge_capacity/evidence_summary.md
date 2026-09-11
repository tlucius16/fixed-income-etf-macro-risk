# Hedge-Capacity Evidence Summary

## Bottom Line

The analysis is complete, but the evidence does not support a causal claim that
greater listed-option capacity protects fixed-income ETFs from future drawdowns.
The defensible contribution is a market-structure decomposition:

> Fixed-income ETF option depth is highly concentrated, small relative to fund
> rate exposure, and predominantly call-driven. The apparent relation between
> capacity and subsequent drawdowns is a between-fund composition effect, not a
> within-fund protective effect.

In the unified paper, this evidence is the market-completeness extension rather
than a standalone manuscript. Funds with the most rate risk attract the deepest option markets, but
changes in their measured capacity did not predict smaller drawdowns during
2016–2026. Put-side capacity—the side most directly associated with downside
insurance—is generally too small to explain protection outside TLT.

## Core Empirical Findings

### 1. The pooled capacity coefficient has the wrong sign

The date-fixed-effect baseline estimates:

```text
fwd_maxdd_12w ~ hedge_capacity_ratio + date FE
β = −0.338, p = 0.0004
```

Since forward maximum drawdown is negative, a protective effect would require a
positive coefficient. The negative pooled estimate associates deeper option
markets with worse subsequent drawdowns.

### 2. The association is entirely cross-sectional

The baseline disappears under controls for persistent fund characteristics:

| Specification | Coefficient | p-value |
|---|---:|---:|
| Ticker FE | −0.228 | 0.140 |
| Ticker + date FE | −0.022 | 0.653 |
| Duration-bucket + date FE | −0.073 | 0.467 |
| Mundlak within component | −0.046 | 0.393 |
| Mundlak between component | −0.507 | <0.0001 |

The meaningful coefficient is the between-ticker component. Funds that are
structurally different—especially funds carrying large duration exposure—also
have structurally different option markets. Within a ticker, increases in option
capacity do not predict less severe drawdowns.

### 3. Call capacity, not put capacity, drives the pooled result

The side-specific horse race estimates:

| Side | Coefficient | p-value |
|---|---:|---:|
| Call capacity | −0.487 | <0.0001 |
| Put capacity | −0.046 | 0.769 |

This is inconsistent with a downside-insurance interpretation. The observed
depth is better described as call-side positioning—such as covered-call or
yield-enhancement demand—concentrated in funds with substantial rate exposure.

### 4. Timing checks provide no protective evidence

The coefficient is insignificant when capacity is no more than 30 days old and
when the sample is restricted to monthly snapshot weeks. Capacity-age controls
do not rescue a within-fund interpretation. Winsorized and logged estimates retain
the pooled negative association, confirming that the between-fund pattern is not
solely an outlier artifact.

### 5. IV-based predictors remain secondary null results

Weekly near-30-day IV now combines quality-controlled call and put IV at a common
near-ATM strike, with single-side fallback. IVRVG does not robustly predict
four-week returns or forward realized volatility. This null result is useful:
neither the option price level nor aggregate option depth provides evidence of a
simple protective or predictive channel.

## Economic Scale and Tradeability

`hedge_capacity_ratio` is an upper-bound stock measure:

```text
100 × underlying price × Σ(|delta| × open interest) / fund AUM
```

It is not executable order-book depth. It assumes all qualifying OI is potentially
available, ignores market impact, and sums absolute delta. The values are generally
near zero because listed option exposure is small relative to the funds’ aggregate
rate exposure.

The 2025-04-01 quality-screened snapshot illustrates the practical scale:

- **TLT puts:** approximately $2.93M DV01 per bp; roughly $1.9B delta-adjusted
  OI. At 5–10% participation, about $100–200M of hedgeable notional.
- **IEF puts:** approximately $27K DV01 per bp.
- **TIP puts:** approximately $13K DV01 per bp.
- **LQD puts:** zero quality-screened DV01 despite approximately $25M/bp of
  underlying fund DV01.
- **AGG, BND, EMB:** approximately zero practical put-side capacity.
- **TLT calls:** approximately 2.6 times TLT put capacity.
- **MBB:** approximately 100:1 call-to-put capacity.

TLT puts are the only clear institutional-scale ETF-option hedging venue in this
sample. Using them to hedge other bond ETFs introduces duration, credit, and
convexity basis risk, which the rate-space framework can quantify.

## What Unified Section 6 Should Claim

The main results section should make four claims:

1. Fixed-income ETF option markets are heterogeneous and concentrated.
2. Aggregate OI-based capacity is small relative to fund rate exposure and is an
   optimistic upper bound on tradeable protection.
3. The negative pooled capacity-drawdown relation reflects persistent differences
   across funds, not protective changes within funds.
4. The relation is call-driven; put-side depth does not predict drawdown protection.

The unified paper should not say:

- “higher hedge capacity reduces future drawdowns”;
- “option depth provides resilience”;
- “vega capacity is a protective predictor” without immediately presenting the
  fixed-effect and call/put decomposition.

## Integrated Empirical Structure

### Unified paper, Section 6

1. Universe, quality screen, and rate-space construction.
2. Economic scale of total, call, and put capacity.
3. Pooled baseline as a motivating descriptive correlation.
4. Ticker-FE and Mundlak decomposition.
5. Call/put horse race.
6. Tradeability tiers and the special role of TLT puts.

### Appendix

- IV and IVRVG null results.
- Duration-normalized Greek and composite hedgeability scores.
- Winsorized/log specifications.
- Capacity-age, fresh-only, and snapshot-week samples.
- Exclusion of dominant funds and duration buckets.
- Roll-cost regime figures.

## Interpretation of Earlier Spec 6

The earlier result that `vega_per_dur` predicted less severe drawdowns should no
longer anchor the paper. It is a date-FE cross-sectional specification and is
vulnerable to the same composition problem exposed by the capacity robustness
battery. It may remain as a descriptive appendix result, but it is not evidence
that increasing hedge supply within a fund improves resilience.

Similarly, `H_dur` remains a descriptive market-structure metric. IVRVG, `H`, and
`H_dur` are not robust return predictors.

## Data and Reproducibility Status

- Monthly chain data: 339,220 contracts, 36 tickers, 114 observed snapshots.
- Screen summary: 3,046 ticker-snapshot observations.
- Weekly options panel: 18,056 rows, 36 tickers.
- Weekly valid combined IV: 7,157 rows.
- Hedge-capacity coverage: 12,599 weekly rows across 33 tickers.
- Robustness table: `tables/robustness_spec0.csv` with 18 coefficient rows.
- Tests: see the current `pytest tests -q` result in `REPRODUCING.md`.

The notebook writes all regression and robustness tables automatically. The
core evidence is integrated into `docs/draft.md`; this file remains the detailed
interpretive audit behind Section 6.

## Submission Checklist

Before submission:

1. Quantify basis risk from using TLT puts to hedge non-TLT exposures.
2. Refresh `ETF_METADATA` AUM and fact-sheet inputs with dated sources.
3. Rotate ThetaData and FRED credentials because they circulated outside the
   repository, even though git history is clean.
