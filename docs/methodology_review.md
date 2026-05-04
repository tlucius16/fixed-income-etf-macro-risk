# Methodology Review

These are the main statistical issues to handle explicitly in the paper and analysis notebook.

## Panel Construction

- The panel is long and unbalanced. State this directly.
- Report ETF counts by week and by category.
- Apply minimum-observation filters before regressions where needed.
- Avoid interpreting early years as representative of the final ETF universe if newer ETFs enter later.

## Survivorship Bias

The ETF universe is based on the available ETFDB screener or preserved legacy export. If dead or delisted ETFs are missing, historical returns may overstate investable performance and understate fragility. Treat this as a limitation unless a survivorship-free universe is added.

## Overlapping Forward Outcomes

Forward 12-week drawdown and volatility windows overlap heavily across adjacent dates. Standard errors should not assume independent ETF-week observations.

Preferred treatment:

- Cluster by ETF and date where feasible.
- Use two-way clustered standard errors for pooled panel regressions.
- For rank tests, compute weekly cross-sectional statistics and test the time-series mean.

## Fixed Effects

Category fixed effects help control broad ETF type differences, but they do not absorb all duration, credit quality, liquidity, or issuer effects. Interpret structural coefficients as associations unless richer controls are added.

## Stress Index Lookahead

The current stress index uses full-sample z-scores. That is acceptable for retrospective classification, but it is not a real-time signal. For predictive framing, add a rolling or expanding z-score robustness check.

## High-Stress Threshold

The `stress_index > 1.0` threshold should be described as pre-specified. If multiple thresholds are explored, report robustness across thresholds rather than selecting the strongest result.

## Macro Collinearity

Macro shocks can be correlated, especially credit spreads, VIX, MOVE, and financial conditions. Report correlation/VIF diagnostics and avoid over-interpreting individual macro coefficients when signs move with specification.

## Economic Interpretation

Separate three claims:

- Macro shocks explain contemporaneous ETF returns.
- Fragility metrics forecast downside outcomes.
- Stress regimes amplify fragility effects.

Each claim needs its own sample definition, dependent variable, controls, and standard-error treatment.

## Recommended Robustness Checks

- Re-run core regressions excluding `Other`, inverse, and leveraged bond ETFs.
- Add minimum ETF history filters after macro merge.
- Test stress results with alternative thresholds, such as top decile or top quartile stress weeks.
- Compare pooled OLS results to weekly cross-sectional Fama-MacBeth style estimates.
- Report category-level sample counts so small buckets do not drive broad claims.
