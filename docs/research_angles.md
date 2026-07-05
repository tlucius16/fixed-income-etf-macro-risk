# Research Angles — Fixed-Income ETF Options

Extensions beyond the IV subsumption result, using the Greeks and transforms already computed.

---

## Context

The IV subsumption regression produced a null result under CGM two-way clustered standard errors: neither realized vol nor implied vol predicts 4-week forward returns with statistical reliability (t ≈ -0.9 and -1.1 after clustering). ΔR² is ~0.06%, economically negligible. The ticker fixed effects do all the work.

This motivates moving beyond IV-as-predictor toward the richer option surface and Greek transforms already available in the pipeline.

---

## Angle 1 — Variance Risk Premium Across the Yield Curve

**Core idea**

VRP = IV² − Realized Var is well-studied in equities (Carr & Wu 2009, Bollerslev et al. 2009) but largely unexplored for bond ETFs. Both legs are already computed: `iv_30d` (annualized) and `vol_12w_annualized` (from the core panel).

**Research question**

Does the variance risk premium vary systematically by duration and credit across fixed-income ETFs? Specifically:
- Is VRP larger for long-duration ETFs (TLT, ZROZ, EDV) than for short-duration (IEF, IEI, BIL)?
- Does VRP at the long end of the curve predict future rate volatility or excess returns?
- How does VRP co-move with macro regimes (rate hike cycles, credit spread widening)?

**Why this works**

Option sellers on long-duration bonds bear more interest rate tail risk than those on short-duration bonds. If the bond options market prices a duration-dependent risk premium, VRP should slope upward with duration — a directly testable prediction from the yield curve structure that has no direct equity analogue.

**Data already available**

| Variable | Source |
|---|---|
| `iv_30d` | `iv_panel_full.csv` |
| `vol_12w_annualized` | `iv_panel_full.csv` |
| Duration proxy | ticker grouping (short/medium/long/credit) |
| Macro regime | FRED DTB3 rate level, fed funds path |

**Key tests**

1. Cross-sectional: regress VRP on duration bucket, controlling for ticker FE
2. Time-series: does high VRP predict higher subsequent realized vol (VRP → vol) or positive forward returns (VRP → return)?
3. Regime: does VRP spike differentially across the curve during rate shock events (Mar 2020, 2022 rate cycle, Mar 2023 SVB)?

**Verdict:** Strongest extension. Uses existing data, established theoretical framework, and the yield-curve cross-section is the differentiating angle vs. the equity VRP literature.

---

## Angle 2 — Theta/Vega Spread as a Cost-of-Insurance Signal

**Core idea**

`theta_vega` (actual) = |θ_daily| / V is already computed in the options screen. So is `theta_vega_theoretical` = σ / (2·T·365). The spread between them:

```
theta_vega_spread = theta_vega_actual − theta_vega_theoretical
```

captures how much more expensive actual time decay is versus fair BSM — effectively a liquidity or demand-pressure premium embedded in the options surface.

**Research question**

Does a positive theta/vega spread (options more expensive than BSM theory predicts) forecast:
1. Higher future realized volatility (the market correctly anticipates risk)?
2. Higher future IV (persistent demand-driven overpricing)?
3. Negative forward returns (investors paying an insurance premium that compresses returns)?

**Why this works**

For bond ETFs, institutional investors (pension funds, insurers) may systematically buy protective puts or covered calls for ALM reasons, creating demand-pressure that drives a persistent wedge between actual and theoretical theta/vega. This wedge should vary with macro uncertainty (e.g., widen before Fed meetings or CPI prints).

**Data already available**

| Variable | Source |
|---|---|
| `theta_vega` | options screen chain JSONs / `ticker_summary.csv` |
| `theta_vega_theoretical` | options screen chain JSONs |
| `iv_30d`, `vol_12w_annualized` | `iv_panel_full.csv` |

**Key tests**

1. Is the spread significantly positive on average (systematic overpricing relative to BSM)?
2. Does it predict future vol or returns at 4w/12w horizons?
3. Does it co-move with macro uncertainty proxies (VIX, MOVE index, rate vol)?

**Verdict:** Novel angle with an economic story. Requires extracting `theta_vega` from the quarterly screen cache (not the weekly IV panel), so coverage is 22 snap dates not 338 Fridays — limits time-series power. Best framed as a cross-sectional or regime study rather than a predictive regression.

---

## Angle 3 — Dollar-Gamma as Options-Implied Convexity

**Core idea**

`dollar_gamma = 0.5 · Γ · S² · (0.01)²` is the P&L for a 1% move in the underlying — already computed in `compute_greeks`. For bond ETFs, the underlying's price convexity (from bond math) should be reflected in option gamma. Comparing options-implied convexity (γ from the options market) to bond-implied convexity (from duration and maturity) reveals whether the options market is correctly pricing interest rate tail risk.

**Research question**

1. Does dollar-gamma scale with bond duration as theory predicts?
2. Are there persistent gaps between options-implied and bond-implied convexity, and do they predict future rate volatility?
3. Do gamma-rich options (high dollar-gamma relative to dollar-delta) outperform during macro stress events?

**Why this works**

Bond convexity is one of the most important but underappreciated risk factors in fixed income. Options on bond ETFs implicitly price convexity in gamma. If the options market systematically misprices convexity relative to the underlying bond math, that represents a structural arbitrage signal — and a direct connection between the options surface and yield curve dynamics.

**Data gap**

Dollar-gamma from the options screen is quarterly (22 dates). Bond-level convexity requires supplementary data (e.g., effective duration and convexity from ETF fact sheets or TRACE). This angle requires the most additional data collection.

**Verdict:** Most theoretically compelling but requires supplementary bond convexity data to close the loop. Better suited as a follow-on paper or robustness exercise once the VRP angle is developed.

---

## Angle 4 — Cross-Sectional Term Structure of Implied Vol

**Core idea**

The options screen fetches chains with DTE in [7, 90] days, giving a short end of the vol term structure. The slope of ATM IV across expirations (term structure) and across strikes (smile/skew) encodes market expectations about near-term vs. medium-term uncertainty.

**Research question**

1. Does the shape of the bond ETF vol term structure predict future realized volatility?
2. Does the vol skew (if extractable) differ systematically across duration/credit categories?
3. How does the term structure slope change around macro events vs. the yield curve slope (2y10y spread)?

**Data gap**

Currently only one expiration (nearest to 30 days) is stored in the IV panel. Extracting the term structure requires fetching and storing multiple expirations per snap date — a pipeline extension.

**Verdict:** Interesting but requires a pipeline change to store multiple expirations. Medium effort, medium novelty.

---

## Summary

| Angle | Novelty | Data Ready | Effort | Verdict |
|---|---|---|---|---|
| 1. VRP across yield curve | Medium | Yes | Low | **Do this first** |
| 2. Theta/vega spread | High | Partial (quarterly only) | Medium | Good secondary |
| 3. Dollar-gamma vs. bond convexity | High | Partial (needs bond data) | High | Follow-on |
| 4. Vol term structure | Medium | No (pipeline change) | High | Later |

---

## Recommended Path

1. Build `vrp = iv_30d**2 - vol_12w_annualized**2` from the existing panel
2. Group tickers by duration bucket (short/intermediate/long/credit)
3. Run the same CGM panel regression with VRP as predictor, check cross-sectional slope by bucket
4. Add macro regime dummies (pre-hike / hike cycle / post-hike) to test whether VRP premium concentrates in stress periods
5. If VRP shows structure, add the theta/vega spread from the quarterly screen as a robustness check
