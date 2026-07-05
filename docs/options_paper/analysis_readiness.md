# Options Paper Analysis Readiness

## Bottom Line

The notebook analysis is effectively complete, but the paper should now be framed around the result the data actually supports. The central contribution is not that IV predicts returns. It is that option-market vega capacity relative to rate-duration exposure predicts forward bond ETF drawdown severity.

The current version has a coherent empirical arc:

1. Establish options coverage for the fixed-income ETF universe.
2. Estimate empirical rate duration from weekly ETF returns and Treasury yield changes.
3. Convert option Greeks into duration-scaled exposure measures.
4. Show the cross-sectional and time-series structure of duration-scaled vega, gamma, and theta.
5. Build hedgeability and duration-normalized hedgeability scores.
6. Treat IV and the IV-realized variance gap as diagnostic state variables, not as the main predictive result.
7. Test predictive regressions and identify the clearest non-null relation: duration-normalized vega capacity is associated with less severe forward drawdowns.

I would not add more IV regressions, rho transforms, or broad interaction searches. Those would likely weaken the paper by making the analysis look exploratory after the main IV tests are already mostly null.

## Updated Paper Framing

The headline claim should be:

> Fixed-income ETF option chains reveal a market-structure measure of hedge capacity: vega available per unit of rate-duration exposure. ETFs with more duration-normalized vega capacity experience meaningfully less severe forward drawdowns.

That claim is cleaner than the original IV/VRP framing. It separates three empirical facts:

- **What works:** `vega_per_dur` predicts less severe 12-week forward max drawdowns (Spec 6, `t = 3.82`, `p = 0.0001`). This is a structural option-chain result.
- **What is null but useful:** IV-based predictors are mostly null. IVRVG does not robustly predict returns or forward realized volatility. This motivates the pivot away from IV levels and toward chain structure.
- **What dominates:** Rate duration remains the strongest cross-sectional risk force. Long-duration status strongly predicts worse forward drawdowns (Spec 7, `t = -5.41`), so the paper should be explicit that duration risk is doing the heavy lifting.

## What Is Working

The duration-scaled Greek framework is the strongest contribution. Raw IV does not carry much return-predictive power, but the option chain still contains useful information about hedge capacity relative to rate exposure.

The empirical duration proxy is defensible for this setting. Treasury and aggregate bond ETFs line up sensibly, rate-hedged ETFs fall near zero, and low-R2 tickers are handled with quality guards.

The quality filtering is important. Duration-scaled ratios are only interpretable when the denominator is reliable, so using duration R2, quality contract counts, and quality share prevents noisy credit or niche ETFs from driving plots and regressions.

The predictive regressions now tell a cleaner story:

- IVRVG is not a robust return predictor.
- Higher realized rate duration is associated with lower short-horizon forward returns in this sample.
- Duration-normalized vega capacity is associated with less severe 12-week forward drawdowns.
- Long-duration status dominates drawdown severity in the control check, while `H_dur` is weaker once duration bucket is controlled.

## Additions That Help

The continuous duration specification is useful. It confirms that the binary long-duration result is not only an artifact of the long bucket cutoff.

The roll-cost regime table is more than supporting evidence. It is the economic backbone for the hedgeability argument: hedging carry cost rose sharply during the tightening cycle, precisely when rate risk was most important.

The expanded roll-cost section now uses ticker-snap summaries, not contract rows, so tickers with more quoted contracts do not mechanically receive more weight. It adds a regime table, a quarterly time-series chart, and a roll-cost-to-vega-capacity tradeoff table.

The ex-ante versus ex-post IVRVG diagnostic table is useful as context, as long as ex-post measures remain descriptive only.

The ticker-snap theta/vega gap test is an improvement over contract-level inference because it reduces duplicate contract-row weighting.

## What I Would Not Add

I would not add more return-prediction variants based on IV, VRP, rho, or Greek interactions unless there is a specific economic hypothesis. The current results already show that IV is not the main story.

I would not add many more regressions to the main notebook. If robustness checks are needed, they should be brief and placed in an appendix section.

I would not treat `H_dur` as a main predictive result. It is better used as a descriptive hedgeability metric unless future results show stronger predictive content.

## Recommended Final Exhibit

The only additive item I would still add before drafting is an economic-magnitude table for Spec 6:

- p25, median, and p75 of `vega_per_dur`
- implied change in `fwd_maxdd_12w` using the Spec 6 coefficient
- the same calculation by duration bucket

That would translate the regression coefficient into paper language and make the result easier to interpret. This is the one additional analysis that would strengthen the notebook without opening a new specification search.

## Test Coverage Note

The feedback about missing tests is directionally correct because these functions are load-bearing for regression validity:

- `summarize_duration_exposure`
- `add_latest_duration_exposure_to_panel`
- `add_duration_normalized_hedgeability`

But the coverage already exists in `tests/test_options_paper_features.py`, not `tests/test_options_features.py`. That is the right place for it because these helpers are specific to the options-paper workflow.

The existing tests cover:

- duration exposure summary construction
- latest-prior as-of merge behavior
- quality gate behavior
- duration-normalized hedgeability coverage requirements
- basic shape and missing-value expectations

I would not duplicate these tests in `test_options_features.py`.

## Recommendation

Freeze the main analysis. The notebook is ready for paper drafting after the current wording fixes. If one more item is added, make it the Spec 6 economic-magnitude table, not another predictive regression.

---

## Detailed Empirical Results

### Regression Results (all 9 specifications)

All regressions use CGM (2011) two-way cluster standard errors clustered on ticker × date. Fixed effects choice follows the identification constraint: time-invariant regressors (duration_long, realized_rate_duration, H, H_dur, vega_per_dur) cannot be identified under ticker FEs and instead use date FEs. Time-varying regressors (vrp / IVRVG) use ticker FEs.

| Spec | Regressors → Outcome | FEs | Key coefficient | t-stat | p-value | Result |
|------|----------------------|-----|-----------------|--------|---------|--------|
| 1 | IVRVG → fwd_ret_4w | Ticker | vrp: 0.0096 | 0.23 | 0.815 | **Null** |
| 2 | IVRVG × duration_long → fwd_ret_4w | Date | duration_long: −0.0047 | −2.23 | 0.026 | **Significant** |
| 2b | IVRVG + realized_rate_duration → fwd_ret_4w | Date | realized_rate_duration: −0.0003 | −2.07 | 0.039 | **Significant** |
| 3a | H → fwd_ret_4w | Date | H: 0.0003 | 0.87 | 0.384 | **Null** |
| 3b | H_dur → fwd_ret_4w | Date | H_dur: 0.0003 | 0.91 | 0.360 | **Null** |
| 4 | IVRVG → fwd_vol_12w | Ticker | vrp: 0.0653 | 1.12 | 0.263 | **Null** |
| 5 | IVRVG / duration → fwd_ret_4w | Ticker | vrp_per_dur: 0.0534 | 0.38 | 0.703 | **Null** |
| 6 | vega_per_dur → fwd_maxdd_12w | Date | vega_per_dur: 0.7542 | 3.82 | 0.0001 | **Significant** |
| 7 | H_dur + duration_long → fwd_maxdd_12w | Date | H_dur: 0.0020; duration_long: −0.0444 | 1.59 / −5.41 | 0.112 / <0.001 | H_dur weak; duration_long highly significant |

**Take-away narrative:**

IV-based predictors (Specs 1, 4, 5) are uniformly null. The options chain does not carry exploitable return-predictive power in raw IV form.

Rate duration is the dominant cross-sectional predictor. Long-duration ETFs earn roughly 47 bps less per 4-week period (Spec 2, t=−2.23). The continuous analog in Spec 2b confirms this is not an artifact of bucket cutoffs.

Vega capacity per unit of duration (Spec 6) is the strongest Greek-based finding: higher option market depth relative to rate exposure predicts meaningfully smaller forward max drawdowns (`t = 3.82`). This is not an IV result; it is a structural feature of the option chain.

H_dur (duration-normalized hedgeability composite) does not predict returns (Spec 3b) and is weak once duration_long is controlled in drawdowns (Spec 7, `t = 1.59`). Duration_long dominates (Spec 7, `t = -5.41`). H_dur is best treated as a descriptive market-structure metric.

---

### Roll Cost by Rate Regime

Median `theta_bp_per_duration` by rate regime and duration bucket:

| Regime | Short | Intermediate | Long | Credit |
|--------|-------|--------------|------|--------|
| pre_tightening (before 2022-01) | 0.2509 | 0.1965 | 0.1473 | n/a |
| tightening (2022-01 to 2023-07) | 0.4016 | 0.4311 | 0.4243 | n/a |
| plateau (2023-07 to 2024-10) | 0.4401 | 0.4213 | 0.3267 | 0.5724 |
| easing (2024-10+) | 0.4420 | 0.3904 | 0.3062 | 0.5523 |

The headline finding is that hedging carry cost rose sharply across the major duration buckets during the rate-tightening cycle and remained elevated through the plateau. Relative to pre-tightening medians, tightening-period roll cost rose about 1.6x for short-duration ETFs, 2.2x for intermediate-duration ETFs, and 2.9x for long-duration ETFs. This supports the economic interpretation that option-based duration insurance became substantially more expensive precisely when rate risk was highest.

The tradeoff table links this mechanism to the main Spec 6 result. During tightening, theta cost per unit of vega capacity rose to about 17.2 for short duration, 19.4 for intermediate duration, and 29.2 for long duration. Vega capacity is valuable for drawdown resilience, but the cost of that capacity also rises during rate-stress regimes.

---

### Methodology Improvements Made During This Session

**Time-varying exposure via latest-prior merge.** The original panel attached static duration metrics. `add_latest_duration_exposure_to_panel()` uses `pd.merge_asof(..., direction="backward")` to attach the most recent prior quarterly option-screen snapshot to each weekly observation. This makes the Greek ratios time-varying without lookahead. The regression panel (Spec 6, Spec 7) uses this to pick up `vega_per_dur` at each date.

**Quality gate on H_dur.** `add_duration_normalized_hedgeability()` requires `quality_contracts >= 50` and `quality_share >= 0.25` before computing H_dur. Tickers that fail either threshold receive H_dur = NaN and are excluded from regressions. This prevents noisy credit, MBS, and niche ETFs from entering the normalized hedgeability measure with unreliable denominators.

**T-test collapse fix.** The original theta/vega gap t-test ran on contract-level rows, inflating degrees of freedom by roughly 100×. The fix collapses to ticker × snap_date means before the one-sample t-test, giving correct inference on the gap between theta and vega carry.

**Duration-scaled Greek ratios.** `vega_per_100_duration`, `gamma_per_100_duration`, and `theta_bp_per_duration` (with `_quality` variants) express each Greek per unit of empirical rate duration. This makes the metrics comparable across short-duration (BIL, SHV) and long-duration (TLT, EDV) ETFs, which would otherwise be incomparable on raw notional Greeks.

**Display filtering.** Charts use `_display` columns that mask tickers with fewer than 50 quality contracts or less than 25% quality share. The underlying summaries are retained, but the masked display prevents visual conclusions driven by unreliable tickers.

---

### Notebook State (41 cells)

The executed notebook (`notebooks/05_options_analysis.ipynb`) has the following structure:

- **Cells 0–10**: setup (imports, config, data loading, universe coverage, rolling duration estimation)
- **Cell 11**: 3-panel bar chart — dollar_duration, vega_per_100_duration, theta_bp_per_duration by ticker with quality masking
- **Cell 12**: scatter — realized_rate_duration vs vega_per_100_duration_quality_median
- **Cell 13**: time-series of duration-scaled Greek exposure by bucket
- **Cell 14**: heatmap — Greek exposure by ticker × date
- **Cell 15**: Section 5 markdown
- **Cell 16**: H and H_dur computation with quality gate
- **Cell 17**: H and H_dur side-by-side bar chart
- **Cell 18**: fragility heatmap
- **Cell 19**: Section 6 markdown
- **Cell 20**: theta/vega gap — defines chains_duration, spread_by_ticker
- **Cell 21**: theta/vega bar chart
- **Cell 22**: t-test on collapsed ticker × snap_date means
- **Cell 23**: spread by bucket
- **Cell 24**: roll-cost regime summary table and grouped bar chart
- **Cell 25**: quarterly roll-cost time-series figure
- **Cell 26**: roll-cost-to-vega-capacity tradeoff table
- **Cell 27**: Section 7 markdown (collapsed summary)
- **Cell 28**: iv_vrp computation (ex-ante IVRVG only)
- **Cell 29**: IV / IVRVG condensed summary table
- **Cell 30**: Section 8 markdown (updated for Specs 2b, 7)
- **Cell 31**: regression setup — latest-prior merge, H_dur included
- **Cell 32**: Spec 1 (ticker FEs)
- **Cell 33**: Spec 2 (date FEs, defines DATE_FE and duration_long)
- **Cell 34**: Spec 2b (continuous realized_rate_duration, new)
- **Cell 35**: Spec 3a + Spec 3b (H and H_dur → ret)
- **Cell 36**: Spec 4 (IVRVG → fwd_vol, ticker FEs)
- **Cell 37**: Spec 5 (IVRVG/duration → ret, ticker FEs)
- **Cell 38**: Spec 6 (vega_per_dur → fwd_maxdd_12w, date FEs)
- **Cell 39**: Spec 7 (H_dur + duration_long → fwd_maxdd_12w, new)
- **Cell 40**: combined regression table (all 9 specs) saved to tables/regression_results.csv

Output figures are saved to `docs/options_paper/figures/`. The roll-cost expansion adds `15_roll_cost_by_regime.png` and `16_roll_cost_time_series.png`. Output tables are saved to `docs/options_paper/tables/`, including `roll_cost_by_regime.csv`, `roll_cost_time_series.csv`, and `roll_cost_vega_tradeoff.csv`.

---

## Final Status

The analysis is complete. The 41-cell notebook is executed end-to-end with no errors. The paper can be drafted directly from this notebook.

The one remaining recommended item is the Spec 6 economic-magnitude table (p25/median/p75 of `vega_per_dur` × coefficient → implied change in `fwd_maxdd_12w` by duration bucket). That table would translate the regression coefficient into intuitive paper language and should be added before drafting the main results section.
