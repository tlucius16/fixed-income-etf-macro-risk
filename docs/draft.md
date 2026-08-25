# Observable Fragility, Limited Hedge Capacity, and Tail Risk in Bond ETFs

**Travon Lucius**<br>
tlucius16@gmail.com<br>
August 2026


## Abstract

Fixed-income ETFs offer daily exchange liquidity on portfolios whose underlying bonds often trade in over-the-counter markets. This paper asks whether fragility is observable before tail losses occur and whether listed options provide enough capacity to hedge it. Using 159,216 ETF-week observations for 352 U.S. fixed-income ETFs from August 2016 to July 2026, we measure fragility as trailing 12-week volatility of weekly excess returns. ETFs in the highest fragility decile experience average 12-week forward maximum drawdowns of −4.75%, compared with −0.22% for the lowest decile, without a commensurate 4-week return premium. A simple screen that excludes the highest fragility quartile reduces maximum drawdown by 468 basis points during 19 high-stress weeks, with no statistically reliable cost during calm periods. We then study the available risk-transfer channel using 339,220 option contracts for a predetermined 36-fund option-chain universe. Capacity is measurable for 33 funds, but only six pass a strict open-interest, spread, and book-balance liquidity gate. The liquid subset is older, larger, and disproportionately concentrated in Treasury funds, so the broad fragility results and narrow options results are estimated on explicitly separate samples. Listed put capacity is negligible outside TLT, while standing depth is predominantly call-sided. The pooled relation between hedge capacity and subsequent drawdowns disappears with fund and date fixed effects; its between-fund component does not survive wild-cluster inference, and put capacity is null. Fragility is therefore broadly observable, but exchange-listed protection is narrow, selected, and provides no robust evidence of within-fund downside protection.

**JEL codes:** G11, G12, G23  
**Keywords:** fixed-income ETFs, fragility, hedge capacity, listed options, macro stress, tail risk

---

## 1. Introduction

Fixed-income ETFs have grown rapidly as they make bond exposure cheap, transparent, and easy to trade for investors without access to the primary market in which they originate. Their structure also creates a tension: ETF shares trade continuously on exchanges, while many underlying bonds trade infrequently through dealers and can become difficult to price during stress. Authorized participants normally arbitrage ETF prices back toward net asset value, but that mechanism can weaken when balance sheet capacity is scarce, bond quotes are stale, or creation/redemption baskets become costly to assemble. The result is an ETF specific form of fragility: secondary market prices can begin to reveal liquidity and arbitrage stress before the underlying portfolio fully reprices.

This paper asks whether that fragility is visible in public return data, whether investors are compensated for bearing it, and whether the listed-options market can transfer the resulting tail risk. We define fragility as trailing 12-week volatility of weekly excess returns. The measure is intentionally simple. It is not a structural estimate of liquidity, duration, or credit risk; rather, it is a transparent signal of recent instability in the ETF price itself. We validate the measure with downside volatility and drawdown variants, then compare the scale of observed fragility with the exchange-listed hedge capacity available to investors.

Four findings organize the analysis. First, recent fragility predicts forward drawdowns and realized volatility, but not meaningfully higher forward returns; macro-beta dispersion and fund characteristics show why broad category labels are insufficient controls. Second, fragility screens are most useful during macro stress, when avoiding the most fragile quartile materially reduces drawdowns with little evidence of a calm-period cost. Third, the apparent hedge set narrows sharply from 352 ETFs to 36 option-chain candidates, 33 funds with measurable capacity, and six funds that pass a strict liquidity gate. Fourth, the depth that remains is concentrated and call-sided: within-fund changes in capacity do not predict smaller drawdowns, and put-side capacity is null.

The contribution is therefore practical and empirical. Prior work studies ETF fragility, bond mutual fund flow fragility, and the effect of ETF ownership on bond liquidity. We connect the detection of bond ETF tail risk to the capacity of the most direct exchange-listed hedge. The resulting asymmetry is economically important: fragility is observable across a broad cross-section, while basis-specific, limited-loss protection is available only in a selected corner of that market. The results do not prove mispricing or investor irrationality. Fragility may proxy for duration, credit beta, convexity, carry, or unobserved portfolio liquidity, and open interest is an optimistic stock measure rather than executable depth. The tests below narrow those interpretations without claiming a single causal mechanism.

The rest of the paper proceeds as follows. Section 2 describes the broad ETF panel and nested options samples. Section 3 defines fragility and stress. Section 4 presents the empirical design. Section 5 reports the broad fragility results. Section 6 measures listed-option hedge capacity. Section 7 summarizes robustness checks, and Section 8 concludes.

## 2. Data

### 2.1 ETF Universe

The sample begins with U.S. exchange listed fixed-income ETFs from the ETFDB screener. We require at least five years of continuous price history, yielding 352 ETFs observed weekly from August 2016 to July 2026. Funds are grouped into broad research categories including Investment Grade Corporate, High Yield, Treasury/Government, Core/Aggregate, EM Debt, TIPS, Muni, Mortgage/Securitized, Preferred/Hybrid, and Other. Leveraged and inverse products are assigned to Other and excluded from the main portfolio tests.

The universe is survivorship-biased because it is based on funds present in the ETFDB screener as of April 2026. This likely understates fragility among the riskiest funds, since liquidated or merged ETFs are omitted. We therefore report a robustness check restricted to the 183 ETFs with full history from 2016.

### 2.2 Price Data and Excess Returns

Daily adjusted close prices are obtained from Yahoo Finance and aggregated to weekly Friday-close prices. Weekly simple returns are computed from consecutive Friday closes. The weekly risk-free rate is the annualized 3-month Treasury bill rate (FRED DTB3) divided by 5,200. Excess returns are defined as:

$$r_{i,t}^{xs} = r_{i,t} - r_{f,t}$$

where $r_{i,t}$ is the raw weekly return for ETF $i$ in week $t$ and $r_{f,t}$ is the weekly risk-free rate.

### 2.3 Macro Variables

Macro controls are public weekly series covering credit conditions, rates, volatility, and geopolitical risk. The main regressors are weekly changes in corporate credit spreads, the 10-year Treasury yield, the 10-year minus 2-year term spread, 5-year breakeven inflation, the Chicago Fed Adjusted National Financial Conditions Index, VIX, MOVE, and a standardized geopolitical-risk index. All series are aligned to the ETF panel by week.

### 2.4 Structural Characteristics

The main fund characteristics are log AUM, expense ratio, and fund age. These variables proxy for secondary market depth, replication cost, and the maturity of the ETF's trading and authorized participant relationships. Because these characteristics are mostly slow-moving, the main specifications use category and year controls so that these cross-sectional differences remain identified.

### 2.5 Fragility Measures

The primary fragility variable is **vol\_12w**, the standard deviation of weekly excess returns over the trailing 12-week window, computed with at least eight complete observations:

$$\text{vol}_{i,t}^{12w} = \sqrt{\frac{1}{n-1} \sum_{k=0}^{11} \left(r_{i,t-k}^{xs} - \bar{r}_{i,t}^{xs}\right)^2}, \quad n \geq 8$$

We also construct downside volatility and trailing maximum drawdown over the same window. The 12-week horizon balances responsiveness to new stress against excessive sensitivity to one-week outliers.

### 2.6 Composite Macro Stress Index

To classify stress weeks, we average standardized changes in financial conditions, credit spreads, bond and equity volatility, dollar strength, and policy-rate uncertainty:

$$
\begin{aligned}
\text{SI}_t = \frac{1}{7}\big(&z[\Delta\text{ANFCI}_t] + z[\Delta\text{CS}_t]
  + z[\Delta\text{MOVE}_t] + z[\Delta\text{VIX}_t] \\
 &+ z[\Delta\text{SPX RV}_t] + z[\Delta\text{DXY}_t]
  + z[\Delta\text{KCPRU}_t]\big)
\end{aligned}
$$

where $z[\cdot]$ denotes full sample standardization and SPX RV is 21-day realized equity volatility. The high-stress indicator equals one when $\text{SI}_t > 1.0$, identifying 19 weeks concentrated in the COVID-19 shock and the 2022 rate-hike cycle. Because full sample standardization is not a real-time signal, Section 7 checks an expanding-window version.

### 2.7 Forward Outcome Variables

The predictive tests use three forward outcomes:

- **fwd\_ret\_4w**: Compound return over the next 4 weeks, $\prod_{k=1}^{4}(1+r_{i,t+k}) - 1$.
- **fwd\_maxdd\_12w**: Maximum drawdown over the next 12 weeks (same computation as maxdd\_12w but applied to future returns).
- **fwd\_vol\_12w**: Standard deviation of weekly returns over the next 12 weeks.

All outcomes begin at $t+1$, so the trailing fragility window and forward outcome window do not overlap.

### 2.8 Broad Panel Summary

The final unbalanced panel contains 159,216 ETF-week observations, with exact counts varying by variable because of rolling-window and forward-outcome availability. The main predictive drawdown and volatility regressions use 123,793 observations after requiring complete fragility measures, controls, and forward outcomes; the 4-week return regression uses 148,753 observations. Table 2 reports descriptive statistics. Table 3 summarizes the cross-sectional category structure and shows that fragility dispersion remains meaningful inside broad categories.

**Data sources.** ETF universe and fund metadata come from the ETFDB screener as of April 2026. Prices are Yahoo Finance adjusted closes, aggregated to Friday weekly frequency. The risk-free rate and macro variables are from FRED where available, with VIX and MOVE observed through Yahoo Finance tickers and geopolitical risk from Iacoviello's daily GPR index. Option chains, native Greeks, implied volatility, and open interest come from ThetaData. All macro series are converted to weekly frequency and merged to the ETF panel by calendar week.

Table: **Table 2. Descriptive statistics.** Returns, volatility, drawdowns, and expense ratios are in percent.

| Variable | N | Mean | Median | P75 |
|:--|--:|--:|--:|--:|
| Weekly return | 159,216 | 0.05 | 0.06 | 0.38 |
| Weekly excess ret. | 159,216 | 0.00 | 0.02 | 0.33 |
| vol\_12w | 156,752 | 0.80 | 0.53 | 0.94 |
| fwd\_ret\_4w | 157,808 | 0.20 | 0.27 | 0.94 |
| fwd\_maxdd\_12w | 154,992 | -2.31 | -1.18 | -0.44 |
| fwd\_vol\_12w | 154,992 | 0.80 | 0.53 | 0.94 |
| Expense ratio | 159,216 | 0.33 | 0.22 | 0.41 |
| Age | 159,216 | 7.87 | 7.25 | 11.41 |

Table: **Table 3. Category counts and fragility dispersion.**

| Category | ETFs | Med. vol | P10--P90 vol |
|:--|--:|--:|--:|
| Core/Aggregate | 82 | 0.61 | 0.15--0.88 |
| IG Corporate | 69 | 0.71 | 0.18--0.98 |
| High Yield | 49 | 0.86 | 0.57--1.01 |
| Muni | 47 | 0.60 | 0.27--0.86 |
| Treasury/Govt | 37 | 0.54 | 0.03--1.84 |
| TIPS | 16 | 0.66 | 0.28--1.27 |
| Mortgage/Sec. | 15 | 0.57 | 0.19--0.83 |
| EM Debt | 14 | 1.11 | 0.81--1.32 |
| DM Debt | 5 | 0.88 | 0.65--1.05 |
| Preferred/Hybrid | 4 | 1.81 | 1.13--1.85 |
| Short Duration/Cash-like | 1 | 0.15 | 0.15--0.15 |

*Notes: Volatility entries are ETF-level averages of vol\_12w, reported in percent. P10--P90 is the within-category dispersion across ETFs.*

### 2.9 Option Chains and Nested Samples

The hedge-capacity analysis begins with a predetermined 36-ETF universe spanning Treasury, aggregate, investment-grade credit, high-yield, inflation-linked, emerging-market, mortgage, and short-duration funds. Monthly business-start option-chain snapshots cover February 2016 through August 2026 and contain 339,220 call and put contract observations across 114 observed snapshot dates. A contract enters the capacity calculation when its relative bid-ask spread is at most 0.35, days to expiration are between 14 and 90, absolute delta is between 0.10 and 0.90, and its dollar delta, gamma, and vega exceed fixed economic-significance floors. Capacity is measurable for 33 funds. A stricter ticker-level gate based on open-interest premium notional, spread, and call-put book balance identifies six liquid funds: EDV, EMB, IEF, LQD, TLT, and ZROZ.

Table 4 documents the selection induced by this narrowing. The option-chain universe is much larger and older than the broad sample. The six liquid funds have median AUM of $22.9 billion, twice the broad universe's median weekly volatility, and a 66.7% Treasury share. The options results therefore describe the available hedge market rather than a representative cross-section of bond ETFs. Broad fragility claims continue to use all 352 funds; capacity tests use the 33 covered funds, and tradeability statements emphasize the six-fund liquid subset.

Table: **Table 4. Nested analysis samples and selection into listed-option capacity.**

| Sample | ETFs | ETF-weeks | Med. AUM | Med. age | Med. vol | Treasury share |
|:--|--:|--:|--:|--:|--:|--:|
| Full ETF universe | 352 | 159,216 | \$0.91B | 10.7 | 0.67% | 10.5% |
| Option-chain universe | 36 | 18,056 | \$12.53B | 18.6 | 0.68% | 27.8% |
| Capacity-covered universe | 33 | 16,830 | \$13.84B | 18.6 | 0.68% | 27.3% |
| Liquid-options universe | 6 | 3,108 | \$22.92B | 21.3 | 1.47% | 66.7% |

*Notes: Fund characteristics use the latest observation in the canonical core panel; volatility is the median across fund-level averages of weekly vol\_12w. The option-chain universe is predetermined rather than selected by the liquidity gate. Capacity-covered funds have at least one non-missing hedge-capacity observation. The liquid-options universe passes the fixed composite liquidity threshold.*

## 3. Fragility Measurement

### 3.1 Why Rolling Volatility Captures Fragility

Bond ETF fragility is not directly observable. Holdings are disclosed with delay, underlying bond bid-ask spreads are unavailable at daily frequency for much of the universe, and ETF flows are filtered through authorized participant activity. We therefore use secondary market return dynamics as the observable signal.

Rolling volatility is a plausible ETF fragility proxy for three reasons. First, ETF prices aggregate information about underlying portfolio risk, arbitrage capacity, and secondary market liquidity. Second, when underlying bonds become hard to trade or price, ETF premiums and discounts can widen, showing up as return instability. Third, elevated recent volatility is not only a generic risk measure; in bond ETFs it can reflect impairment in the transmission between ETF prices, NAVs, and underlying cash-bond markets. The contribution is therefore not that volatility predicts volatility, but that ETF-specific return instability is informative about forward tail outcomes in a market structure where liquidity transmission can become impaired. Because volatility can also proxy for duration exposure and rate volatility, we treat the mechanism as an interpretation rather than a separately identified causal channel. Flow-based fragility remains an important complementary measure, but price based fragility is available consistently across the full ETF universe.

### 3.2 Three Fragility Metrics

The primary measure, **vol\_12w**, is the 12-week trailing standard deviation of weekly excess returns. It captures total return instability and has minimal missing data. Two robustness measures separate downside from total volatility: **downside\_vol\_12w**, the semi-deviation of negative weekly excess returns, and **maxdd\_12w**, the worst peak-to-trough cumulative loss within the same trailing window. The three measures are highly correlated in the cross-section (pairwise Spearman $\rho > 0.85$), so the main tests use vol\_12w and report the others as robustness checks.

### 3.3 Time-Series Properties

Fragility is persistent within funds but can move sharply during market stress. Category rankings are broadly intuitive, long duration and credit sensitive ETFs tend to be more fragile than aggregate bond ETFs but the ordering can invert when normally liquid markets become impaired. This time variation motivates a fund week panel rather than a static category analysis.

### 3.4 Composite Stress Index: Construction and Validation

The stress index SI$_t$ aggregates weekly changes in ANFCI, credit spreads, MOVE, VIX, 21-day S\&P 500 realized volatility, DXY, and policy-rate uncertainty. It is designed to capture co-occurring stress across funding, credit, rates, equity volatility, dollar-funding, and policy-uncertainty channels. High-stress weeks account for 3.7% of the sample and cluster in the COVID-19 shock and the 2022 rate-hike cycle. The baseline uses a binary high-stress indicator for interpretability and checks the continuous index and expanding-window standardization in robustness tests.

## 4. Empirical Strategy

### 4.1 Panel Structure

The unit of observation is an ETF week $(i,t)$. Standard errors are two-way clustered by fund and calendar week, following Cameron, Gelbach, and Miller (2011), to account for serial correlation within ETFs and common shocks across ETFs in the same week. The main specifications use category controls and year controls so that slow-moving fund characteristics remain identified.

### 4.2 Macro Sensitivity and Structural Heterogeneity (H1 and H2): Model M1

To test H1 and H2, we estimate weekly excess returns on contemporaneous macro factor changes, category controls, and fund characteristics:

$$r_{i,t}^{xs} = \alpha + \beta' \Delta\mathbf{M}_t + \gamma' \mathbf{X}_{i,t} + \delta' \mathbf{C}_i + \varepsilon_{i,t} \tag{M1}$$

where $\Delta\mathbf{M}_t$ is the vector of contemporaneous macro shocks, $\mathbf{X}_{i,t}$ contains log AUM, expense ratio, and age, and $\mathbf{C}_i$ contains category indicator variables (Investment Grade Corporate, High Yield, Treasury, etc.).

H1 is supported if macro shocks are jointly significant and if per-fund credit spread betas vary substantially within categories. H2 is supported if the fund characteristic block adds explanatory power beyond category controls. Full time fixed effects are not included in M1 as they would absorb the macro variation of interest.


### 4.3 Fragility Predicts Forward Downside (H3): Model M2

To test whether recent fragility predicts forward outcomes, we estimate:

$$y_{i,t+h} = \alpha + \beta_1\, \text{vol}_{i,t}^{12w} + \gamma' \mathbf{X}_i + \delta' \mathbf{C}_i + \varepsilon_{i,t} \tag{M2}$$

where $y_{i,t+h}$ is forward 12-week maximum drawdown, forward 12-week volatility, or forward 4-week compound return. When the dependent variable is maximum drawdown, more negative values represent worse outcomes; H3 therefore predicts a negative coefficient for drawdowns, a positive coefficient for volatility, and little evidence of return compensation large enough to match the higher downside exposure.

**Decile sort.** As a nonparametric complement to the regression, we sort ETFs into deciles by vol\_12w each week and compute equal-weighted average forward outcomes within each decile. The D1–D10 spread provides an economically interpretable summary of the fragility-downside relationship that is free of functional form assumptions.

### 4.4 Fragility During Stress Regimes (H4): Model M3

To test stress dependence, we augment M2 with a stress interaction:

$$
\begin{aligned}
\text{fwd\_maxdd}_{i,t}^{12w}
  ={}& \alpha + \beta_1\, \text{vol}_{i,t}^{12w}
      + \beta_2\, \text{SI}_t \\
   &+ \beta_3\, (\text{vol}_{i,t}^{12w} \times \text{SI}_t)
      + \gamma' \mathbf{X}_i
      + \delta' \mathbf{C}_i
      + \varepsilon_{i,t}
\end{aligned}
\tag{M3}
$$

where $\text{SI}_t$ is either the continuous stress index or the binary high-stress indicator. A negative $\beta_3$ indicates that stress is associated with a more adverse conditional fragility gradient. We interpret this interaction alongside split-sample slopes, stress-conditional decile sorts, and the portfolio tilt below. These diagnostics distinguish a broad stress-period level shift from literal amplification of the fragility slope.

**Portfolio tilt.** As a practical test of H4, we compare two weekly equal-weighted portfolios, excluding the Other category:

- *Naive EW*: equal-weight all ETFs with non-missing vol\_12w each week.
- *Tilt EW*: equal-weight only the bottom 75% of ETFs by vol\_12w (screen out the top fragility quartile each week).

The key question is whether the tilt reduces losses during stress without imposing a reliable cost during calm periods.

### 4.5 Listed-Option Hedge Capacity (H5)

We translate option Greeks into the same rate-risk units as the underlying ETF. If ETF $i$ has empirical rate duration $D_i$, underlying price $S_{it}$, contract delta $\Delta_c$, and open interest $OI_c$, the chain's rate DV01 is the quality-screened sum of per-contract exposure. Dividing by fund DV01 gives:

$$
\begin{aligned}
\text{HCR}_{it}
&= \frac{\sum_c D_i S_{it}|\Delta_c|(0.0001)(100)OI_c}
{D_i\,\text{AUM}_{it}(0.0001)} \\
&= \frac{100S_{it}\sum_c|\Delta_c|OI_c}{\text{AUM}_{it}}.
\end{aligned}
$$

The duration estimate cancels from the hedge-capacity ratio, although it remains necessary for absolute DV01 and convexity accounting. HCR is an optimistic upper bound: open interest is a stock rather than an executable quote, all qualifying positions are treated as potentially available, and price impact is ignored. Call and put capacity are therefore reported separately, with put capacity providing the more direct test of downside insurance.

The descriptive baseline relates forward drawdown to the latest prior monthly capacity snapshot with date fixed effects:

$$
\text{fwd\_maxdd}_{i,t}^{12w} = \alpha_t + \beta\,\text{HCR}_{i,t} + \varepsilon_{i,t}. \tag{M4}
$$

Because drawdowns are negative, a protective relation requires $\beta>0$. H5 predicts economically meaningful put-side capacity and a positive within-fund capacity coefficient. We test that prediction with ticker and date fixed effects, a Mundlak decomposition into within- and between-fund capacity, call-put horse races, fresh-snapshot restrictions, and wild-cluster bootstrap inference at the ticker level.

### 4.6 Identification and Limitations

The analysis is reduced-form. The macro regressions describe co-movement, not causal transmission. The predictive regressions avoid mechanical look-ahead because fragility uses returns through $t$ and forward outcomes begin at $t+1$, but persistence in volatility means past and future risk are naturally related. The stress index uses full sample standardization in the baseline, which is appropriate for retrospective classification but not for real-time trading; an expanding-window version addresses this concern in Section 7. High-stress weeks cluster in the COVID-19 shock and the 2022 rate-hike cycle, so the stress evidence should be read as evidence from those episodes rather than from a broad sample of independent crises. Portfolio tests are gross of transaction costs, so the weekly tilt should be interpreted as a risk-management screen rather than a directly netted trading strategy.

The options extension has separate limitations. The 36-fund universe is predetermined but not representative of all bond ETFs, capacity is available for only 33 funds, and six pass the strict liquidity gate. Effective cross-sectional sample size is therefore the number of funds rather than the number of ETF-week rows. Open interest does not identify signed demand, and the call-sided interpretation is an inference from book composition rather than transaction direction. Finally, overlapping forward windows and multiple outcomes can inflate apparent precision, so the broad panel relies on two-way clustering and weekly rank tests, while the capacity analysis adds ticker-cluster wild-bootstrap inference.

## 5. Results

### 5.1 Macro Sensitivity and Structural Heterogeneity (H1 and H2)

Table 5 shows that weekly bond ETF returns load heavily on common macro shocks, especially credit spread and Treasury rate changes. The macro block explains 41.2% of weekly return variation, while category controls add little incremental explanatory power in the contemporaneous return regression. This is unsurprising: macro shocks arrive at the same calendar time for all funds, so their largest effect is common.

The more important H1 result is cross-sectional. Per-fund credit spread betas vary significantly within all nontrivial categories, and the Bartlett test rejects equality of within category variance (χ² = 62.9, p < 0.001). Within High Yield, for example, the interdecile spread in credit spread betas implies nearly a 2:1 difference between the least and most credit-sensitive funds. Category labels therefore summarize broad exposure but do not fully describe fund level macro sensitivity.

Fund characteristics are jointly significant (F = 7.68, p < 0.001), though their contribution to contemporaneous return R² is modest. Their larger role appears in the forward-outcome regressions, where fund size, expense ratio, and age help explain differences in subsequent drawdown risk.

Table: **Table 5. Macro sensitivity and within-category heterogeneity.**

| Statistic | Value |
|:--|--:|
| Macro block R-squared | 41.2% |
| Credit spread coefficient | -0.051 |
| 10-year Treasury coefficient | -0.046 |
| HY credit beta P10/P90 | -0.102 / -0.048 |
| Bartlett test | $\chi^2 = 62.9$, $p < 0.001$ |

### 5.2 Fragility Predicts Forward Downside Without a Return Premium (H3)

Table 6 shows that recent fragility predicts future downside in the full specification with category and fund-characteristic controls. The result is not limited to the symmetric volatility measure: downside volatility and trailing maximum drawdown also predict worse forward drawdowns.

The key economic result is the contrast between downside and returns. A one standard deviation increase in vol\_12w predicts deeper forward drawdowns and higher forward realized volatility, but it does not predict a commensurate return premium. In the full specification, the coefficient on 4-week forward returns is positive (β = +0.41), while the decile sort shows D10 earning 0.23% versus 0.19% for D1 over the same horizon. The return relation is therefore positive on average but non-monotonic in the tails: mean forward returns peak around D8 and then flatten, while drawdowns continue to worsen through D10. This divergence is why the paper emphasizes weak compensation relative to downside exposure rather than a negative expected-return effect.

Figure 3 makes the magnitude clear. The lowest fragility decile has an average 12-week forward maximum drawdown of −0.22%, while the highest fragility decile has −4.75%, a 453-basis-point spread between the average decile endpoints. The evidence therefore supports the narrower claim that fragility is weakly compensated relative to its forward downside risk.

Table: **Table 6. Fragility and forward outcomes (H3).**

| Outcome / sort | Estimate | t-stat | N |
|:--|--:|--:|--:|
| fwd\_maxdd\_12w | -0.681 | -3.20 | 123,793 |
| fwd\_vol\_12w | 0.312 | 4.74 | 123,793 |
| fwd\_ret\_4w | 0.419 | 3.51 | 148,753 |
| D10 - D1 max drawdown | -4.53 pp | -- | -- |
| D10 - D1 return | 0.04 pp | -- | -- |

*Notes: Regression rows report the coefficient on vol\_12w from the full M2 specification. t-statistics use two-way clustered standard errors by ETF and calendar week. Decile rows report equal-weighted high-minus-low fragility decile spreads.*

![Figure 3. Forward outcomes by fragility decile. Bars show 12-week forward maximum drawdown; line shows 4-week forward return.](docs/figures/fragility_deciles.png)

### 5.3 Fragility During Stress Regimes (H4)

Table 8 provides the clearest H4 evidence. Excluding the top fragility quartile each week produces nearly the same full sample annualized return as the naive equal-weight portfolio, while reducing full sample maximum drawdown from 14.85% to 12.42%. Across the 19 high-stress weeks, the tilt portfolio's cumulative return is −12.53%, compared with −18.25% for the naive portfolio, and its maximum drawdown is 468 basis points shallower. The paired weekly return difference during stress is statistically significant (t = 3.00, p = 0.0078). During calm weeks, the return cost is not statistically reliable.

Table 7 gives supporting regression and decile-sort evidence. Stress weeks are worse for ETF drawdowns, and the fragility-stress interaction is negative in both binary and continuous specifications. The separate vol\_12w slope is nevertheless smaller in absolute value during stress (−1.23 versus −1.73 outside stress), a ratio of 0.71. Thus, the interaction evidence should not be described as unambiguous slope amplification: stress shifts the full cross-section toward worse outcomes while the most fragile ETFs remain the deepest source of tail exposure. The mean weekly D10−D1 forward-drawdown spread is 4.36 percentage points in the full sample and 6.67 percentage points during stress.

This asymmetry is the most practical evidence for H4. The interaction estimates are useful diagnostics, but the portfolio test is the main stress-regime result. The tilt's stress-period outperformance partly reflects an implicit reduction in long-duration and lower-quality credit exposure, consistent with the duration-beta robustness evidence in Section 7.5.

Table: **Table 7. Stress-regime evidence (H4).**

| Statistic | Estimate |
|:--|--:|
| vol\_12w $\times$ high\_stress | -0.678 |
| vol\_12w $\times$ stress\_index | -0.267 |
| Low-stress vol\_12w slope | -1.730 |
| High-stress vol\_12w slope | -1.234 |
| High-stress D10 - D1 drawdown | -6.67 pp |

*Notes: Interaction and split-slope estimates are from M3 specifications that also control for trailing downside volatility and maximum drawdown, with standard errors clustered by ETF. The decile spread is the mean weekly high-minus-low fragility-decile difference during high-stress weeks.*

Table: **Table 8. Portfolio tilt performance.**

| Regime | Portfolio/test | Ret. | Max DD | t-stat |
|:--|:--|--:|--:|--:|
| Full sample | Naive EW | 2.54% | -14.85% | -- |
| Full sample | Tilt EW | 2.63% | -12.42% | -- |
| High stress | Naive EW | -18.25% | -18.37% | -- |
| High stress | Tilt EW | -12.53% | -13.69% | -- |
| High stress | Tilt - Naive | +0.35 pp/wk | -- | 3.00 |
| Calm weeks | Tilt - Naive | -0.01 pp/wk | -- | -1.48 |

*Notes: Full sample returns are annualized. High-stress returns are cumulative over 19 weeks. Tilt - Naive rows report average weekly return differences and paired t-statistics. Naive EW equal-weights all eligible bond ETFs each week, excluding the Other category; Tilt EW excludes the highest fragility quartile each week.*

## 6. Listed-Option Hedge Capacity

### 6.1 A Narrow and Selected Hedge Set

The sample funnel in Table 4 is the first hedge-capacity result. Listed option data are available for a deliberately broad set of 36 candidate funds, but three never produce measurable capacity and only six pass the strict liquidity gate. This narrowing is economically selected rather than random: the liquid group is older, larger, more volatile, and dominated by Treasury exposure. Restricting the macro-risk analysis to these funds would therefore confound general bond ETF fragility with the characteristics that attract an options market. We instead preserve the broad sample for H1–H4 and limit H5 to the hedge-capacity universe.

Empirical rate durations validate the rate-space bridge: the latest quality estimates correlate 0.98 with published effective durations. More importantly, duration cancels algebraically from the headline ratio. The capacity measure is therefore not mechanically larger for a fund merely because its estimated duration is large; absolute DV01 and convexity measures retain that dependence.

### 6.2 Capacity Is Sparse and Call-Sided

The fund-by-fund accounting shows that TLT is the only clear institutional-scale listed-option venue. At the representative 2025-04-01 snapshot, the full quality-screened TLT put book supplies approximately $2.93 million of DV01 per basis point, equivalent to roughly 3.5% of the fund's own rate DV01. Even that is an upper bound. A 5–10% participation assumption supports approximately $100–200 million of hedgeable notional against a fund with tens of billions of dollars in AUM. IEF and TIP put capacity is closer to retail or small-account scale, while LQD, AGG, BND, and EMB have approximately zero quality-screened put capacity at the same snapshot.

The standing book is also oriented away from downside insurance. TLT call-side DV01 exceeds put-side DV01 by approximately 2.6 to one, and MBB is more heavily call-dominated. No fund with a meaningful two-sided book is robustly put-dominant. Because open interest is unsigned, this composition cannot identify investor motives, but it is more consistent with covered-call and yield-enhancement activity than with a deep market for protective puts.

### 6.3 Capacity Does Not Predict Protection

Table 9 reports the identification sequence. The pooled date-fixed-effect coefficient is negative, the opposite of protection, and conventionally significant under asymptotic CGM inference. That result does not survive inference at the effective fund level: its wild-cluster p-value is 0.095. Ticker-plus-date fixed effects remove the association, and the Mundlak decomposition places it in persistent between-fund differences rather than within-fund changes. The between component also fails the wild bootstrap. In the call-put horse race, calls retain a negative association while puts remain null. Thus, the one coefficient that survives is attached to the side of the book least consistent with downside insurance.

Table: **Table 9. Hedge capacity and forward drawdowns (H5).**

| Specification / component | Estimate | CGM $p$ | Wild-bootstrap $p$ |
|:--|--:|--:|--:|
| Pooled capacity, date FE | -0.338 | 0.0004 | 0.095 |
| Ticker + date FE | -0.022 | 0.653 | -- |
| Mundlak within-fund capacity | -0.046 | 0.393 | 0.374 |
| Mundlak between-fund capacity | -0.507 | $<0.0001$ | 0.116 |
| Call capacity, joint horse race | -0.487 | $<0.0001$ | 0.030 |
| Put capacity, joint horse race | -0.046 | 0.769 | 0.786 |

*Notes: The dependent variable is 12-week forward maximum drawdown, so a protective relation requires a positive coefficient. CGM standard errors cluster by ticker and date. Wild-bootstrap p-values use 9,999 Rademacher replications clustered by ticker; the capacity-covered sample contains 33 funds.*

### 6.4 Option Prices Provide No Substitute Signal

The implied-volatility diagnostics reach the same conclusion. Near-30-day ATM IV combines call and put estimates at a common strike, validated on 784 matched monthly pairs with median absolute IV disagreement of 0.0078. Neither IV levels nor the ex-ante implied-minus-trailing-realized variance gap robustly predicts forward drawdowns, 4-week returns, or forward realized volatility. Fresh-capacity-only and monthly-snapshot-only samples are likewise null. These are informative nulls: neither the price nor the measured quantity of listed-option exposure provides evidence of a simple protective channel.

## 7. Robustness

### 7.1 Two-Way Clustered Standard Errors

Overlapping 12-week forward outcomes create serial dependence. Two-way clustering inflates the standard error on the main vol\_12w coefficient from 0.138 to 0.212, but the coefficient remains statistically significant (t = −3.20). The main conclusions do not rely on one-way fund clustering.

### 7.2 Fama-MacBeth Spearman Rank Correlations

As a nonparametric check, we compute weekly cross-sectional Spearman correlations between vol\_12w and each forward outcome, then test the time-series mean. The average rank correlation is strongly negative for forward drawdowns and strongly positive for forward volatility. The forward return correlation is small and positive, and it becomes statistically insignificant during high-stress weeks. This confirms that the main result is not driven by a linear panel specification.

Weekly decile-spread tests tell the same story. The average D10-D1 forward drawdown spread is −4.36 percentage points across weeks (t = −36.3), while the average D10-D1 forward return spread is only 0.08 percentage points and is not statistically different from zero (t = 0.68). The decile evidence therefore supports monotonic downside prediction, not a monotonic return premium.

The drawdown result is not sensitive to multiple-testing concerns across the three forward outcomes: the weekly decile-spread t-statistic for drawdowns is large enough that standard family-wise adjustments do not alter the inference. The forward-return result is treated more cautiously because the decile spread is small and statistically indistinguishable from zero.

### 7.3 Subsample and Survivorship Robustness

The fragility drawdown relationship is stable across available within-sample splits, and the main results also hold when restricting to the 183 ETFs with full history from 2016 and when excluding small or specialized categories. These checks reduce, but do not eliminate, concerns about survivorship and category composition.

As a simple out-of-sample screen, we estimate the top-quartile fragility cutoff using 2016--2021 data and apply that fixed threshold to 2022--2026. The tilt portfolio earns an 8.96% cumulative return versus 7.08% for the naive portfolio and reduces maximum drawdown from 13.29% to 7.56%, though the weekly return difference is not statistically reliable (t = 0.23, p = 0.82). This supports the drawdown-control interpretation but not an alpha claim.

### 7.4 Expanding-Window Stress Index

Replacing the full sample stress index with an expanding-window version identifies 36 stress weeks, with 96.3% week-level agreement between the two classifications. The interaction remains negative (−0.290 versus −0.325 under full sample standardization), so the stress-regime findings are not an artifact of ex post standardization.

### 7.5 Duration-Beta Robustness

To separate ETF-level fragility from duration exposure, we estimate each fund's rate beta from weekly excess returns on changes in the 10-year Treasury yield and add that beta to the M2 drawdown regression. This robustness check uses a common category/characteristic control set across all three specifications, without year fixed effects, so that rate-volatility regime variation is not absorbed. Under this common specification, the baseline vol\_12w coefficient is −0.956 (t = −4.73). The coefficient remains negative and statistically reliable after controlling for static rate beta (β = −0.389, t = −2.40). A stricter specification that also includes the interaction of rate beta with MOVE attenuates the coefficient further and leaves it below conventional significance thresholds (β = −0.247, t = −1.68). This check shows that recent ETF volatility contains drawdown information beyond static category labels, but not that it is independent of time-varying duration exposure. A substantial component of the fragility signal is therefore interpretable as dynamic duration risk during high rate-volatility regimes.

### 7.6 Hedge-Capacity Robustness

The capacity conclusions survive alternative timing, transformation, and pricing assumptions. Restricting capacity to observations no more than 30 days old or to monthly snapshot weeks does not produce a protective coefficient. Winsorized and log-capacity specifications retain the pooled negative sign but do not restore a within-fund channel. Dropping TLT, LQD, and IEF removes the pooled precision, confirming that a few developed markets drive the cross-sectional result. Finally, repricing the option chains with a 751-step American CRR model produces approximately zero median IV bias across ticker, right, and moneyness buckets; stale deep-in-the-money quotes account for the apparent tail cases. These checks reinforce the interpretation of limited and selected capacity rather than a hidden protective effect.

## 8. Conclusion

Fixed-income ETF risk is not fully summarized by broad category labels. A simple price-based fragility measure identifies funds with materially worse forward drawdowns and higher realized volatility. The highest fragility decile experiences 453 basis points more average forward maximum drawdown than the lowest decile while earning nearly the same 4-week forward return. During high-stress weeks, excluding the most fragile quartile reduces portfolio drawdown without a statistically reliable calm-period cost. Duration and rate volatility explain a meaningful part of the relation, so the result is best understood as a practical risk screen rather than a standalone alpha factor.

The options evidence completes that risk-management interpretation. The direct exchange-listed hedge is available for only a selected subset of the market, and practically liquid capacity is narrower still. TLT is the only clear institutional-scale put venue; credit and aggregate ETF put capacity is generally negligible. The pooled capacity-drawdown association is a between-fund composition effect, not evidence that increasing hedge supply protects a fund over time, and put-side capacity does not predict smaller drawdowns. The depth that remains is predominantly call-sided, consistent with yield enhancement rather than broad downside-risk transfer.

The central conclusion is therefore asymmetric: bond ETF fragility is easier to observe than to hedge with listed options. This does not establish mispricing, nor does it rule out futures, swaps, credit derivatives, or OTC options as alternative hedges. It does show that investors relying on exchange-listed, basis-specific protection face a narrow and selected market precisely when the broad ETF cross-section contains substantial tail-risk dispersion. Recent fragility is useful because it is transparent and available before the drawdown; the options evidence shows why identifying that risk cannot be assumed to make it readily transferable.

## Disclaimer

This research was conducted independently and does not represent the views, opinions, or research of BlackRock, Inc. or any of its affiliates. The content is provided for informational and educational purposes only and should not be construed as investment advice or a recommendation to trade.

## References

Ben-David, Itzhak, Francesco Franzoni, and Rabih Moussawi. 2018. "Do ETFs Increase Volatility?" *Journal of Finance* 73 (6): 2471-2535.

Bollerslev, Tim, George Tauchen, and Hao Zhou. 2009. "Expected Stock Returns and Variance Risk Premia." *Review of Financial Studies* 22 (11): 4463-4492.

Cameron, A. Colin, Jonah B. Gelbach, and Douglas L. Miller. 2011. "Robust Inference With Multiway Clustering." *Journal of Business & Economic Statistics* 29 (2): 238-249.

Carr, Peter, and Liuren Wu. 2009. "Variance Risk Premiums." *Review of Financial Studies* 22 (3): 1311-1341.

Chen, Qi, Itay Goldstein, and Wei Jiang. 2010. "Payoff Complementarities and Financial Fragility: Evidence from Mutual Fund Outflows." *Journal of Financial Economics* 97 (2): 239-262.

Chernenko, Sergey, and Adi Sunderam. 2020. "Do Fire Sales Create Externalities?" *Journal of Financial Economics* 135 (3): 602-628.

Coval, Joshua, and Erik Stafford. 2007. "Asset Fire Sales and Purchases in Equity Markets." *Journal of Financial Economics* 86 (2): 479-512.

Dannhauser, Caitlin D. 2017. "The Impact of Innovation: Evidence from Corporate Bond Exchange-Traded Funds." *Journal of Financial Economics* 125 (3): 537-560.

Goldstein, Itay, Hao Jiang, and David T. Ng. 2017. "Investor Flows and Fragility in Corporate Bond Funds." *Journal of Financial Economics* 126 (3): 592-613.

Iacoviello, Matteo. 2022. "Measuring Geopolitical Risk." *American Economic Review* 112 (4): 1194-1225.

Israeli, Doron, Charles M. C. Lee, and Suhas A. Sridharan. 2017. "Is There a Dark Side to Exchange Traded Funds? An Information Perspective." *Review of Accounting Studies* 22: 1048-1083.
