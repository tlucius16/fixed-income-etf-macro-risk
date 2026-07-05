# Methodology — Options Paper

## 1. Universe and Duration Buckets

The analysis universe comprises 36 fixed-income ETFs that passed the liquidity screen
(`mean_pass_rate >= 0.50` across quarterly snap dates 2020–2025). Each ticker is
assigned to a duration bucket:

| Bucket | Approximate Effective Duration | Example Tickers |
|---|---|---|
| short | < 3 yr | BIL, SGOV, MINT, IGSB, STIP |
| intermediate | 3–10 yr | IEF, AGG, LQD, TIP, MBB |
| long | 10+ yr | TLT, EDV, ZROZ, LTPZ, VCLT |
| credit | HY (credit risk primary) | HYS, HYGH, JNK |
| other | Mixed / equity-like | ICVT |

The bucket map is mostly category based, with two empirical overrides from the
rolling duration estimates: `VCEB` is treated as intermediate investment-grade
credit, and `LTPZ` is treated as long TIPS.

## 2. Empirical Rate-Duration Proxy

The paper's central exposure measure starts with a time-varying empirical
duration proxy estimated from the core weekly return panel:

```
Return_it = α_i,t + β_rate,i,t Δ10y_t + ε_it
realized_rate_duration_it = −100 · β_rate,i,t
```

The multiplier of 100 is required because `d_DGS10` is measured in percentage
points. A 10 bp yield move is represented as `0.10`, not `0.001`. Each estimate
uses a trailing 52-week window with at least 40 non-missing observations, so the
proxy is available at date `t` without look-ahead. The raw estimate is retained;
the reported proxy is clipped to `[-2, 35]` to limit unstable windows.

This is an empirical rate-beta duration, not an ETF sponsor's effective-duration
series. It is most interpretable for Treasury and aggregate bond ETFs. For credit
ETFs it can still be useful as a rate-risk proxy, but the coefficient may mix rate
and spread shocks if credit-spread controls are not included.

## 3. Rate-Space Bridge

The rate-space bridge translates per-contract dollar Greeks into yield-sensitivity
units (DV01-equivalent basis), so call and put contracts are commensurable and
exposure aggregates to a natural economic unit.

Starting from the fund price-rate relationship `dS/S = −D_i · dy`, the
chain-rule delta for a single contract is:

```
dV/dy = (∂V/∂S) · (∂S/∂y) = delta_c · (−D_i · S)
```

Scaling by a one-basis-point yield move (dy = 0.0001) and 100 contracts per
standard lot:

```
rate_dv01_c  = D_i · S · |delta_c| · 0.0001 · 100         [dollars per bp]
rate_conv_c  = 0.5 · D_i² · S · (delta_c + S · gamma_c) · (0.0001)² · 100
rate_carry_c = |theta_daily_c| / rate_dv01_c               [daily $/$ per bp]
```

**D_i sign convention.** `realized_rate_duration = −100 · beta_rate`, where
`beta_rate` is the OLS slope from regressing weekly returns on `d_DGS10`
(percentage-point yield changes). For a long-duration Treasury ETF, beta < 0
and D_i > 0.

**Absolute delta.** `rate_dv01` uses `|delta_c|` so puts and calls with the same
moneyness contribute equally to the chain's rate-hedging capacity.

**Convexity sign.** `rate_conv` uses the *signed* option delta so that the gamma
term `S · gamma_c` is always positive while the delta term carries its natural
sign.

## 4. Hedge Capacity Ratio and D_i Cancellation Identity

The chain-level hedge capacity for side `s ∈ {call, put, total}` on ticker `i`
at snap date `t` is:

```
chain_rate_dv01_it = Σ_c [ rate_dv01_c · w_c ]   where w_c = open_interest_c
                                                    (or 1 if OI unavailable)
fund_dv01_i  = D_i · AUM_i · 0.0001
hedge_capacity_ratio_it = chain_rate_dv01_it / fund_dv01_it
```

**D_i cancellation identity.** Expanding `chain_rate_dv01` with `w_c = 1`:

```
hedge_capacity_ratio = (D_i · S · Σ|delta_c| · 0.0001 · 100) / (D_i · AUM · 0.0001)
                     = (100 · S · Σ|delta_c|) / AUM
```

D_i cancels exactly. The ratio reduces to the OI-weighted delta-adjusted notional
as a share of AUM, making it robust to the noisiness of empirical duration
estimates. D_i does *not* cancel in absolute exposure levels or in the convexity
comparison, where the `D_i²` term in `rate_conv` makes the ratio scale with
duration.

**OI weighting.** Open interest is fetched via the bulk ThetaData endpoint
(`option_history_open_interest`, `strike='*'`, `right='both'`). When OI is
unavailable, uniform weights are used and `weight_basis = 'unweighted'` is
flagged in the output. Regressions using `weight_basis = 'unweighted'` rows
should be treated as robustness checks.

**Quality gate.** A ticker × snap_date × side row is retained only when at least
5 quality contracts (passing the tradeability filter) contribute to the aggregate.

**Convexity capacity ratio.** Analogous to hedge_capacity_ratio but using
`rate_conv` in the numerator and `fund_conv_dollar` (from `eff_convexity` or
the D_i² proxy) in the denominator. Because D_i² does not cancel, this ratio is
more sensitive to duration estimation error than `hedge_capacity_ratio`.

**Unweighted degradation caveat.** When OI is unavailable, `hedge_capacity_ratio`
degrades toward a contract-count-weighted average of delta-adjusted notional. The
ratio still has economic meaning but overstates capacity for deep-OTM strikes that
may carry zero OI in practice.

## 5. Duration-Scaled Greek Exposure (Robustness)

The legacy Greek-scaling approach (retained as a robustness comparison) maps from
dollar Greeks to rate-space without requiring OI:

```
dollar_duration = dollar_delta · realized_rate_duration
duration_per_vega = dollar_duration / dollar_vega
vega_per_100_duration = 100 · dollar_vega / |dollar_duration|
gamma_per_100_duration = 100 · dollar_gamma / |dollar_duration|
theta_bp_per_duration = 10000 · |theta_daily| / |dollar_duration|
```

Quality-filtered versions require `duration_r2 ≥ 0.20` and
`|realized_rate_duration| ≥ 1.0`. These are computed from `chains.csv` using
`add_duration_exposure_features` in `src/options_paper/features.py`.

## 6. Hedgeability Score (H)

```
H_i = z(mean_pass_rate_i) + z(median_dollar_vega_i) + z(median_dollar_gamma_i)
```

where z(·) denotes cross-sectional z-score across liquid tickers, computed from
`ticker_summary.csv`. The `median_theta_vega` term used in earlier drafts has
been dropped: theta_vega is not in the lean chain schema and is not an
independently informative screen predictor once dollar_vega and dollar_gamma are
controlled.

- **mean_pass_rate**: fraction of contracts passing the tradeability + dollar-Greek filter.
- **median_dollar_vega** (`V · 0.01`): P&L sensitivity per 1pp vol move. Higher = more vega capacity.
- **median_dollar_gamma** (`0.5 · Γ · S² · 0.01²`): P&L for a 1% price move.

Tickers are assigned to terciles (1 = least hedgeable, 3 = most hedgeable).

## 7. Fragility Tercile

Fragility is measured as mean forward 12-week maximum drawdown per ticker
(`fwd_maxdd_12w` from the core panel, averaged across all weekly dates).
More negative = more fragile; tercile 3 is the most fragile.

The `fragility_hedgeability_group` (`F{1|2|3}_H{1|2|3}`) captures the joint
distribution for a 3×3 fragility-hedgeability matrix.

## 8. Rate Carry

```
rate_carry_c = |theta_daily_c| / rate_dv01_c   [$/$ per bp per day]
```

Zero when `rate_dv01_c = 0`. Aggregated to chain level as the quality-contract
median. Interpretable as the daily theta cost per unit of rate-hedging capacity —
the "price of the hedge" in carry terms. Expected to be higher for credit and
short-duration ETFs (thin options markets, higher per-unit carry cost).

## 9. IV-Realized Variance Gap as Diagnostic

```
IVRVG_it = IV²_it − RV_trailing²_it
```

where `IV_it` is the annualized 30-day ATM implied volatility and `RV_trailing_it` is
`vol_12w_annualized` (12-week rolling weekly return standard deviation × √52).

Both legs are in variance units (annualized squared return). This variable is an
ex-ante IV-realized variance gap, not a fully ex-post variance risk premium, because
the realized-volatility leg is backward-looking and known at date `t`.

For descriptive, non-predictive analysis, an ex-post premium is also computed when
forward realized volatility is available:

```
VRP_ex_post_12w_it = IV²_it − RV_forward_12w²_it
```

where `RV_forward_12w` is `fwd_vol_12w × √52`. This ex-post measure should not be
used as a predictor in forward-return regressions because it uses future returns.

The return-predictive role of IV/IVRVG is treated as a diagnostic null test. The
subsumption tests and duration-normalized regressions do not support IVRVG as a
robust 4-week return predictor, so IVRVG is not the paper's main signal.

The weekly IV panel is also merged to the latest prior empirical duration estimate,
which supports duration-normalized IVRVG tests:

```
vrp_per_duration = IVRVG / |realized_rate_duration|
vrp_x_duration = IVRVG · realized_rate_duration
```

The quality-filtered versions apply the same duration `R²` and absolute-duration
guards described above.

## 10. Predictive Regressions

**Primary specification:**
```
fwd_maxdd_12w_it = α_t + β · hedge_capacity_ratio_it + ε_it
```

`hedge_capacity_ratio` is merged onto the weekly panel via `merge_asof` backward,
attaching the nearest prior quarterly snap's capacity estimate. Date fixed effects
`α_t` absorb common shocks. A positive `β` means higher hedge capacity is
associated with less severe forward drawdowns (fwd_maxdd is negative when
drawdowns occur).

**Additional specifications (null checks / robustness):**
- Outcomes: `fwd_ret_4w`, `fwd_vol_12w_annualized`, `fwd_maxdd_12w`
- Predictors: `vrp`, `realized_rate_duration`, `H`, `H_dur`, `vega_per_dur`,
  `convexity_capacity_ratio`, `median_rate_carry`
- Fixed effects: ticker FEs for time-varying predictors; date FEs for
  time-invariant cross-sectional regressors (`duration_long`, `H`, `H_dur`)
- Standard errors: CGM (2011) two-way cluster on ticker × date throughout

**CGM two-way SE formula:**
```
V_CGM = V(cluster_ticker) + V(cluster_date) − V(HC1)
```
followed by eigenvalue projection to the PSD cone (Cameron, Gelbach & Miller 2011).

Implemented in `src/options_paper/analysis/regression_utils.py::twoway_cluster_se`.

## References

- Cameron, A. C., Gelbach, J. B., & Miller, D. L. (2011). Robust inference with multiway clustering. *Journal of Business & Economic Statistics*, 29(2), 238–249.
- Carr, P., & Wu, L. (2009). Variance risk premiums. *Review of Financial Studies*, 22(3), 1311–1341.
- Bollerslev, T., Tauchen, G., & Zhou, H. (2009). Expected stock returns and variance risk premia. *Review of Financial Studies*, 22(11), 4463–4492.
