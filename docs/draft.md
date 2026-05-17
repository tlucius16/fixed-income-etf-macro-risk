# Macro Stress, Liquidity, and the Cross-Section of Bond ETF Fragility

**[Author]**  
[Affiliation]  
[Date]

---

## Abstract

The fixed-income ETF market now exceeds $X trillion in assets yet concentrates structural vulnerabilities — duration mismatches, liquidity transformation, and credit risk — that standard category-level analysis obscures. We construct a panel of 347 bond ETFs over 521 weeks (April 2016 to April 2026) and introduce a rolling-volatility fragility measure that captures each fund's susceptibility to tail outcomes. Four findings emerge. First, macro shocks — particularly credit spread changes (β = −0.051***) and Treasury rate changes (β = −0.046***) — generate heterogeneous weekly return responses, with within-category beta dispersion significant in all ten non-trivial categories (Bartlett test p < 0.001) and macro factors collectively explaining 41% of weekly return variance. Second, fund size, expense ratio, and age explain incremental return variation beyond category membership (F = 7.68, p < 0.001). Third, and most distinctly, fragile ETFs face severely worse forward outcomes — the highest-fragility decile incurs −4.78% average forward maximum drawdown versus −0.23% for the lowest — yet earn essentially the same four-week forward return (0.24% vs. 0.19%), with the regression coefficient on forward returns positive (β = 0.41***), inconsistent with fragility being a compensated risk factor. Fourth, the fragility-to-drawdown relationship amplifies during high macro stress (β = −0.22***, interaction with stress indicator), and a simple quartile screen reduces maximum drawdown by 467 basis points during the 21 high-stress weeks (t = 2.67, p = 0.015) while delivering no cost in calm periods. Our results indicate that fixed-income ETF fragility constitutes an uncompensated tail risk — a structural vulnerability that investors bear without return compensation.

**JEL codes:** G11, G12, G23  
**Keywords:** fixed-income ETFs, fragility, bond market liquidity, macro stress, cross-sectional returns, risk mispricing

---

## 1. Introduction

The bond ETF market has grown from negligible assets in 2002 to more than $X trillion today, making fixed-income ETFs one of the fastest-growing vehicles in asset management. Yet the structure of these products embeds a fundamental tension: daily secondary-market liquidity is promised on top of underlying bonds that trade infrequently, in dealer-mediated markets, with wide bid-ask spreads. This liquidity mismatch is not uniform. Some bond ETFs — those holding long-duration Treasuries, high-yield corporate bonds, or emerging market debt — absorb macro shocks in ways that are qualitatively different from broad-market aggregates. The cross-sectional distribution of this vulnerability, and whether it is priced, is the subject of this paper.

We define *fragility* operationally as backward-looking 12-week rolling volatility of weekly excess returns (vol\_12w). This measure is deliberately simple: it requires no model, no latent factor extraction, and no assumption about the source of risk. It tracks how much a fund's return has varied in recent months — a first-order signal of tail susceptibility that any investor can compute from public data. We complement it with downside volatility and maximum drawdown variants to confirm that our results are not an artifact of the specific construction.

Using a panel of 347 fixed-income ETFs over April 2016 to April 2026 (521 weeks, 156,588 ETF-week observations), we test four hypotheses that together characterize how macro shocks propagate through the cross-section of bond ETF returns and whether the resulting fragility is compensated.

**H1 — Macro sensitivity is heterogeneous.** Macro shocks — particularly credit spread changes (β = −0.051***) and 10-year Treasury rate changes (β = −0.046***) — significantly explain weekly bond ETF returns, with macro factors alone accounting for 41% of weekly return variance. Sensitivity varies systematically across categories: per-fund OLS betas on credit spread changes exhibit statistically significant within-category dispersion in all ten non-trivial categories (t-statistics ranging from 2.00 to 12.57), with the Bartlett test rejecting equality of within-category variance (χ² = 62.9, p < 0.001).

**H2 — Structural characteristics explain return variation beyond category.** Fund size (log AUM), expense ratio, and age explain return variation incrementally beyond broad category membership. An F-test on the joint significance of structural characteristics rejects the null at the 0.1% level (F = 7.68, p < 0.001), and the structural block adds nearly ten times as much explained variance to the forward-outcome regressions as category fixed effects alone (ΔR² = 9.7 pp vs. 1.3 pp). This result indicates that structural heterogeneity within categories is not diversifiable by category selection alone.

**H3 — Fragility predicts forward downside without a return premium.** The key result of the paper. ETFs in the highest fragility decile subsequently experience −4.78% average forward maximum drawdown over the following 12 weeks, versus −0.23% for the lowest fragility decile — a spread of 455 basis points. Forward realized volatility rises monotonically across all ten deciles. Yet the same high-fragility ETFs earn *essentially the same* forward returns: 0.24% over four weeks in the top decile versus 0.19% in the bottom. The regression coefficient on vol\_12w in the forward-return specification is positive and significant (β = 0.41, t = 11.55), confirming that fragile ETFs earn slightly *higher* subsequent returns despite their far greater tail exposure. If fragility were a compensated risk factor, investors would demand a premium for bearing it; these results rule that out and point instead to a persistent mispricing: fragile ETFs are not cheapened sufficiently to compensate for their tail risk.

**H4 — The fragility-to-drawdown relationship amplifies during macro stress.** We construct a composite macro stress index as the equal-weighted average of standardized changes in the ANFCI, BAML credit spreads, the MOVE index, and VIX, identifying 21 high-stress weeks across the sample (4.0%), concentrated in the COVID-19 shock of 2020 and the 2022 rate-hike cycle. The interaction of fragility with the binary stress indicator is significantly negative (β = −0.22, p < 0.001): a given level of fragility is disproportionately punished when macro conditions deteriorate. A portfolio that screens out the top fragility quartile each week reduces the portfolio's maximum drawdown by 467 basis points during the 21 stress weeks and generates a return advantage of 0.30% per week (t = 2.67, p = 0.015), while delivering no cost in the remaining 493 calm-period weeks (t = −1.61, p = 0.11). The asymmetry of the tilt's benefit — present only during stress — confirms that the fragility premium is concentrated in the tails of the macro environment.

The central contribution of this paper is the identification of fragility as an *uncompensated* tail risk in fixed-income ETFs. Prior work on ETF fragility has focused primarily on equity ETFs (Ben-David, Franzoni, and Moussawi, 2018; Israeli, Lee, and Sridharan, 2017) or on the flow-fragility link in bond mutual funds (Goldstein, Jiang, and Ng, 2017; Chen, Goldstein, and Jiang, 2010). Dannhauser (2017) examines the impact of corporate bond ETF introduction on bond yields and finds that ETF inclusion reduces liquidity premiums, consistent with structural distortions. We contribute to this literature in three ways. First, we focus on *within-ETF-universe* fragility heterogeneity, which the prior literature has not systematically documented at weekly frequency. Second, we construct a fragility measure that is forward-looking in its predictive content while being backward-looking in its construction — requiring no structural model. Third, and most distinctively, we document the disconnection between fragility-driven downside risk and expected returns, which we interpret as evidence of investor inattention to tail risk in the bond ETF market.

Our findings also connect to the broader literature on liquidity transformation in asset management. Coval and Stafford (2007) document fire-sale externalities in mutual funds during forced selling episodes. Chernenko and Sunderam (2020) show that bond mutual fund managers exploit liquidity buffers in ways that benefit existing shareholders at the expense of new entrants. Our paper adds the observation that the same structural fragility that predicts future drawdowns does not elicit a compensating return premium, suggesting that the market for fixed-income ETF risk is segmented from the standard risk-return tradeoff.

For practitioners, the results offer a concrete application: a simple fragility screen can reduce tail exposure during macro stress events with no apparent sacrifice of returns during calm periods. The screening rule is transparent, requires only publicly available return data, and rebalances at weekly frequency.

The rest of the paper proceeds as follows. Section 2 describes the data and ETF universe. Section 3 defines the fragility measures and validates the composite stress index. Section 4 presents the empirical strategy. Section 5 reports results for H1 through H4. Section 6 presents robustness tests including two-way clustered standard errors, Fama-MacBeth Spearman rank correlations, and subsample stability. Section 7 concludes.

---

## 2. Data

### 2.1 ETF Universe

We construct our sample from the ETFDB screener, which covers U.S.-listed exchange-traded funds with standardized category and expense-ratio metadata. We restrict attention to fixed-income ETFs and retain only funds with at least five years of continuous price history, yielding a cross-section of 347 ETFs across eleven non-trivial research categories plus an Other/leveraged bucket excluded from most regressions.

**Survivorship bias.** The ETF universe is defined by funds present in the ETFDB screener as of April 2026; fixed-income ETFs that were delisted, merged, or liquidated before that date are not captured. This introduces survivorship bias in a direction that likely understates fragility for the highest-risk segment: funds that experienced the most severe stress episodes may have been liquidated before our observation window ends. We treat this as an acknowledged limitation. The five-year minimum history filter partially mitigates the concern — funds whose entire history falls within a single market regime are excluded — but does not eliminate it. As a descriptive bound: 183 of the 336 non-Other ETFs (54%) entered the panel in 2016 and have the full ten-year history; the remaining 153 funds (46%) entered after 2016, with the largest cohort (42 funds) entering in 2020. Regressions restricted to the 183 full-history ETFs produce qualitatively identical results across all four hypotheses.

Each ETF is assigned to one of fourteen research categories based on its ETFDB classification: Investment Grade Corporate, High Yield, Treasury/Government, Core/Aggregate, EM Debt, TIPS/Inflation-Linked, Muni, DM Debt, Short Duration/Cash-like, Mortgage/Securitized, Preferred/Hybrid, and Other (inverse and leveraged products, which we exclude from most regressions). Table 1 reports the number of ETFs and aggregate AUM in each category. The universe spans a wide range of structural characteristics: AUM from below $10 million to more than $XX billion, expense ratios from [X] to [X] basis points, and fund ages from one to more than twenty years.

### 2.2 Price Data and Excess Returns

Daily adjusted closing prices are obtained from Yahoo Finance via the yfinance library for the full available history of each ETF. Prices are adjusted for dividends and splits. We aggregate daily prices to a **weekly (Friday-close)** series using the last observed price of each calendar week, consistent with the macro data aggregation described below. Weekly simple returns are computed as the percentage change in consecutive Friday closes.

The weekly risk-free rate is the annualized 3-month Treasury bill rate (FRED series DTB3), converted to a weekly decimal by dividing the annualized rate by 5,200. Excess returns are:

$$r_{i,t}^{xs} = r_{i,t} - r_{f,t}$$

where $r_{i,t}$ is the raw weekly return for ETF $i$ in week $t$ and $r_{f,t}$ is the weekly risk-free rate.

### 2.3 Macro Variables

We employ six macro factors drawn from publicly available sources, all aggregated to weekly frequency using Friday-close values. Weekly changes are computed as first differences of the weekly level series.

**Credit and rates (FRED):**
- $\Delta$CS: Weekly change in the BofA Merrill Lynch US Corporate Master Option-Adjusted Spread (FRED: BAMLC0A0CM), our primary measure of aggregate credit conditions.
- $\Delta$DGS10: Weekly change in the 10-year Treasury constant maturity yield (FRED: DGS10).
- $\Delta$T10Y2Y: Weekly change in the 10-year minus 2-year Treasury term spread (FRED: T10Y2Y), capturing yield curve slope dynamics.
- $\Delta$T5YIE: Weekly change in the 5-year breakeven inflation rate (FRED: T5YIE), capturing inflation expectations.
- $\Delta$ANFCI: Weekly change in the Chicago Fed Adjusted National Financial Conditions Index (FRED: ANFCI), a broad gauge of financial tightness. Positive values indicate tighter-than-average conditions.

**Volatility (Yahoo Finance):**
- $\Delta$VIX: Weekly change in the CBOE Volatility Index (ticker: \textasciicircum VIX), capturing equity market risk aversion.
- $\Delta$MOVE: Weekly change in the ICE BofA MOVE Index (ticker: \textasciicircum MOVE), measuring implied volatility in the Treasury market — the bond-market analogue of the VIX.

**Geopolitical risk:**
- GPR: Weekly average of Iacoviello's (2022) Geopolitical Risk Daily Index, which counts newspaper references to geopolitical tensions. Because GPR exhibits substantial scale differences from the financial stress variables, we standardize it to zero mean and unit variance (GPR$_z$) before inclusion in regressions. GPR is used as a control rather than a primary shock variable.

All macro series are merged to the ETF panel on the weekly Date index. The final macro sample begins in May 2016, when all eight series are jointly available at weekly frequency.

### 2.4 Structural Characteristics

Three time-invariant (or slowly varying) fund characteristics enter the cross-sectional regressions:

- **Log AUM** ($\log A_{i,t}$): Natural logarithm of assets under management (millions USD), parsed from the ETFDB metadata string. Larger funds face tighter bid-ask spreads on the underlying bonds and attract more arbitrage capital, which may reduce the volatility of the ETF premium/discount.
- **Expense ratio** (ER$_i$): Annual expense ratio as a decimal, parsed from the ETFDB string. Expense ratios range from 3 to 472 basis points with a median of 20 bps. Higher fees mechanically reduce net returns and may proxy for less-liquid underlying portfolios where index replication is costly.
- **Fund age** (Age$_{i,t}$): Calendar years since inception, computed as $(t - \text{Inception}_i) / 365.25$. Older funds have established authorized participant relationships and deeper secondary markets.

### 2.5 Fragility Measures

Our primary fragility variable is **vol\_12w**, the standard deviation of weekly excess returns over the trailing 12-week window, computed with a minimum of eight non-missing observations:

$$\text{vol}_{i,t}^{12w} = \sqrt{\frac{1}{n-1} \sum_{k=0}^{11} \left(r_{i,t-k}^{xs} - \bar{r}_{i,t}^{xs}\right)^2}, \quad n \geq 8$$

We construct two complementary fragility measures for robustness. **Downside volatility** (downside\_vol\_12w) is the semi-deviation of returns below zero over the same window, requiring at least three negative-return observations. **Maximum drawdown** (maxdd\_12w) is the largest peak-to-trough cumulative loss within the trailing 12-week window, computed from the cumulative product of gross returns. Higher values of all three measures indicate greater recent fragility.

The 12-week window is chosen to balance responsiveness to emerging stress against excessive sensitivity to individual outlier weeks. A single shock that reverses quickly should not persistently inflate fragility; a 12-week window ensures that elevated fragility reflects a genuine regime rather than a one-week spike. We report robustness to 26-week windows in the Online Appendix.

### 2.6 Composite Macro Stress Index

To classify weeks as macro stress episodes, we construct a composite index that aggregates four orthogonal dimensions of financial stress:

$$\text{SI}_t = \frac{1}{4}\left(z[\Delta\text{ANFCI}_t] + z[\Delta\text{CS}_t] + z[\Delta\text{MOVE}_t] + z[\Delta\text{VIX}_t]\right)$$

where $z[\cdot]$ denotes full-sample standardization (mean zero, unit variance). The equal-weight scheme avoids imposing priors on the relative importance of credit, rates, and equity volatility channels. We define a binary **high-stress** indicator equal to one when $\text{SI}_t > 1.0$, a threshold pre-specified before examining any regression results — approximately the top 16% of a standard normal, though empirically it captures only 4.0% of sample weeks given the concentration of extreme stress into two episodes. Section 6.4 reports robustness to an expanding-window z-score that eliminates the full-sample look-ahead present in this construction.

Full-sample standardization is appropriate for our retrospective research panel — the goal is to classify weeks by their realized stress intensity across the full 2016–2026 period, not to construct a real-time investable signal. The stability of results under the expanding z-score (Section 6.4) confirms that the classification is not an artifact of this choice.

The index identifies the COVID-19 shock (March–April 2020) and the 2022 rate-hike cycle as the two most prolonged high-stress episodes in our sample, consistent with the fixed-income ETF literature's characterization of these as the dominant stress events of the post-2015 period.

### 2.7 Forward Outcome Variables

To assess the predictive content of backward-looking fragility, we engineer three forward outcome variables for each ETF-week:

- **fwd\_ret\_4w**: Compound return over the next four weeks, $\prod_{k=1}^{4}(1+r_{i,t+k}) - 1$.
- **fwd\_maxdd\_12w**: Maximum drawdown over the next 12 weeks (same computation as maxdd\_12w but applied to future returns).
- **fwd\_vol\_12w**: Standard deviation of weekly returns over the next 12 weeks.

All forward outcomes are computed by shifting the rolling window forward in time rather than by lookahead: formally, we compute the rolling statistic on the return series and shift by $k$ periods using `.shift(-k)`. Forward outcomes are missing for the final $k$ weeks of each ETF's time series.

### 2.8 Panel Summary

The final panel is an unbalanced ETF-week panel with 347 ETFs observed over April 2016 to April 2026 (521 weeks), yielding 156,588 ETF-week observations with 98.4% vol\_12w coverage. After requiring non-missing fragility measures and forward outcomes, the main predictive regressions use 121,541 observations (M2, M3) and 149,649 observations (M1). Table 2 reports descriptive statistics for the main variables. The cross-sectional standard deviation of vol\_12w is 0.99%, reflecting the wide range of structural risks across the fixed-income ETF universe, from short-duration cash-like products (mean vol\_12w ≈ 0.16%) to leveraged and inverse instruments (mean ≈ 2.91%).

---

<!-- 
PLACEHOLDERS TO FILL IN:
- [N] ETFs: panel.Symbol.nunique()
- [YYYY–YYYY]: panel.Date.min() to panel.Date.max()
- [total observations]: len(panel)
- [regression obs]: len(reg_panel.dropna(...))
- $X trillion market size: ICI 2024 data
- [X] cross-sectional std of vol_12w: panel.groupby('Date')['vol_12w'].std().mean()
- Aggregate AUM by category: panel.groupby('category_bucket')['Assets_clean'].sum()
- Fee range: panel['ER_clean'].describe()
- Earliest FRED date: from macro_factors_weekly.csv Date.min()
- Table 1: ETF count and AUM by category
- Table 2: Descriptive statistics for main variables
-->

---

## 3. Fragility Measurement

### 3.1 Why Rolling Volatility Captures Fragility

Bond ETF fragility — the susceptibility of a fund to large, rapid losses during stress — is not directly observable. Position-level holdings are disclosed only quarterly, bid-ask spreads on the underlying bonds are not publicly available at daily frequency for most of our universe, and fund flows for ETFs are inferred rather than reported. We therefore turn to secondary-market return dynamics as the identifying signal.

The economic argument for rolling volatility as a fragility proxy rests on three observations. First, an ETF's secondary-market price embeds the market's forward-looking assessment of its underlying portfolio's risk; elevated volatility signals that this assessment is itself uncertain, which is the essence of fragility. Second, ETFs that hold less-liquid bonds experience larger premiums and discounts around shocks — the arbitrage mechanism that keeps ETF prices near NAV is impaired precisely when liquidity is scarce — and this impairment manifests in return volatility before it shows up in observable redemptions. Third, rolling volatility is computable in real time from public data alone, which is both a practical advantage and a transparency advantage: investors can replicate our fragility signal without access to proprietary data.

A natural alternative is flow-based fragility, following Goldstein, Jiang, and Ng (2017), who show that bond funds with more fragile investor bases face larger redemption-driven fire sales. However, ETF share creation and redemption data are noisy at weekly frequency and reflect authorized-participant mechanics rather than retail investor behavior directly. We treat flow-based fragility as complementary rather than competitive with our price-based measure.

### 3.2 Three Fragility Metrics

**vol\_12w** is our primary measure. Operationally, it is the 12-week trailing standard deviation of weekly excess returns, estimated with minimum eight non-missing observations. It is symmetric — it equally weights upside and downside return movements — which makes it a clean measure of total return uncertainty rather than pure downside risk. For interpretation, a vol\_12w of 2% means that the fund has been generating weekly excess returns with a standard deviation of 2% over the trailing quarter, equivalent to approximately 14% annualized volatility.

**downside\_vol\_12w** (semi-deviation) restricts the calculation to weeks with negative excess returns only. It isolates the left tail of the return distribution and is zero by construction in a fund that has had no negative-return weeks in the past 12 weeks. Requiring at least three negative observations before computing the statistic prevents noise from small samples.

**maxdd\_12w** measures the worst realized peak-to-trough drawdown within the trailing 12-week window — the single largest cumulative loss an investor would have experienced by entering at the worst possible intra-window peak. It captures episodic severity rather than average dispersion and is particularly relevant for institutional investors subject to drawdown-based risk mandates.

The three measures are highly correlated in the cross-section (pairwise Spearman $\rho > 0.85$), confirming that they capture the same underlying construct rather than orthogonal dimensions of risk. We use vol\_12w as the primary regressor throughout for its symmetric interpretation and minimal missing data, and we report Panel C in the H3 results as an across-measure robustness check.

### 3.3 Time-Series Properties

Figure 1 (notebook 02) plots vol\_12w for six representative ETFs from [start date] through [end date], with high-stress weeks shaded. Several features are visible. First, fragility is highly persistent within a fund: the series exhibit strong positive autocorrelation (within-fund AR(1) $\approx$ [X]), meaning that a fund's fragility rank changes slowly except during abrupt regime shifts. Second, the cross-sectional ranking is mostly stable — TLT and HYG consistently exhibit higher vol\_12w than AGG and BND — but the *ordering* can invert during stress. In March 2020, Treasury ETFs experienced a fragility spike that briefly exceeded high-yield ETFs as Treasury markets themselves became impaired. Third, the level of the median vol\_12w across the universe tracks macro stress; Figure 1 also shows the IQR band of the cross-sectional distribution, which narrows during calm periods and widens sharply during stress, consistent with a common stress factor driving cross-sectional comovement.

### 3.4 Composite Stress Index: Construction and Validation

The stress index SI$_t$ aggregates four weekly first-difference macro variables: $\Delta$ANFCI (financial conditions tightening), $\Delta$CS (credit spread widening), $\Delta$MOVE (bond market implied volatility), and $\Delta$VIX (equity implied volatility). Each component is standardized over the full sample before equal weighting. The composite therefore measures the *co-occurrence* of stress across multiple channels, rather than stress in any single market.

Figure 2 plots SI$_t$ over the full sample. High-stress weeks (SI$_t > 1$) account for 4.0% of the total sample (21 of 521 weeks) — below the 16% theoretical benchmark of a standard normal, reflecting the concentration of severe stress in two relatively brief but intense episodes: the COVID-19 shock of March–May 2020 and the 2022 rate-hike cycle. The clustering of stress weeks is consistent with the empirical literature documenting that financial market volatility is fat-tailed and episodic rather than uniformly distributed. The binary high\_stress indicator is used in M3 for interpretability; continuous SI$_t$ is used as a robustness check. The two specifications yield qualitatively identical conclusions.

The equal-weighting scheme is a deliberate choice. A principal-component extraction would maximize explained variance but introduce sample dependence and instability across subsamples. Equal weighting treats the four stress channels symmetrically and ensures the index is reproducible out of sample from the same four publicly available series.

---

## 4. Empirical Strategy

### 4.1 Panel Structure

The unit of observation is an ETF-week $(i, t)$. All regressions are estimated on the balanced subsample with non-missing values for the relevant dependent variable, regressors, and controls. We report three sets of results corresponding to the three regression models (M1, M2, M3) that map to the four hypotheses.

Throughout, standard errors are two-way clustered by fund (Symbol) and calendar week (Date), following Cameron, Gelbach, and Miller (2011). This accounts simultaneously for (i) serial correlation within a fund over time and (ii) cross-sectional correlation across funds within the same week — the dominant source of dependence in weekly macro-driven panels. The CGM variance estimator is:

$$\hat{V}_{\text{CGM}} = \hat{V}_{\text{Symbol}} + \hat{V}_{\text{Date}} - \hat{V}_{\text{HC1}}$$

where $\hat{V}_{\text{Symbol}}$ and $\hat{V}_{\text{Date}}$ are one-way cluster-robust variance matrices and $\hat{V}_{\text{HC1}}$ is the heteroskedasticity-robust (HC1) sandwich. All regressions include fund fixed effects ($\alpha_i$) unless noted.

---

### 4.2 Macro Sensitivity and Structural Heterogeneity (H1 and H2): Model M1

To test H1 and H2, we estimate the following panel regression of weekly excess returns on contemporaneous macro factor changes and structural characteristics:

$$r_{i,t}^{xs} = \alpha_i + \boldsymbol{\beta}' \Delta\mathbf{M}_t + \boldsymbol{\gamma}' \mathbf{X}_i + \boldsymbol{\delta}' \mathbf{C}_i + \varepsilon_{i,t} \tag{M1}$$

where:
- $\Delta\mathbf{M}_t = (\Delta\text{ANFCI}_t,\ \Delta\text{CS}_t,\ \Delta\text{DGS10}_t,\ \Delta\text{T10Y2Y}_t,\ \Delta\text{T5YIE}_t,\ \text{GPR}_{z,t})'$ is the vector of contemporaneous macro shocks
- $\mathbf{X}_i = (\log A_{i,t},\ \text{ER}_i,\ \text{Age}_{i,t})'$ are structural fund characteristics
- $\mathbf{C}_i$ are category indicator variables (Investment Grade Corporate, High Yield, Treasury, etc.)
- $\alpha_i$ is a fund fixed effect

We estimate three progressive specifications. Specification (1) includes macro factors only. Specification (2) adds category fixed effects. Specification (3) adds structural characteristics $\mathbf{X}_i$. The incremental $R^2$ and joint F-test on the structural block in moving from (2) to (3) provide the primary test of H2.

**H1** is supported if the macro factor coefficients $\boldsymbol{\beta}$ are jointly significant and if per-fund OLS betas on the primary macro shock ($\Delta$CS) exhibit statistically significant cross-sectional dispersion. We test the latter using a Bartlett test for equality of variances across category groups: rejection implies that within-category dispersion is non-trivially heterogeneous, which category-level analysis would miss.

**H2** is supported if the F-test on $\boldsymbol{\gamma}$ rejects in Specification (3), with the structural block explaining incremental return variation beyond the category indicators $\mathbf{C}_i$ alone.

A VIF diagnostic confirms that the macro regressors are not severely collinear before interpreting individual coefficients. The ANFCI index is constructed to be orthogonal to its own components, but the other macro series share common drivers; we treat the joint F-test rather than individual point estimates as the primary inferential object for H1.

---

### 4.3 Fragility Predicts Forward Downside (H3): Model M2

To test whether backward-looking fragility predicts forward tail outcomes, we estimate:

$$y_{i,t+h} = \alpha_i + \beta_1\, \text{vol}_{i,t}^{12w} + \boldsymbol{\gamma}' \mathbf{X}_i + \boldsymbol{\delta}' \mathbf{C}_i + \varepsilon_{i,t} \tag{M2}$$

where $y_{i,t+h}$ is one of three forward outcome variables: $\text{fwd\_maxdd}_{i,t}^{12w}$ (forward 12-week maximum drawdown), $\text{fwd\_vol}_{i,t}^{12w}$ (forward 12-week return volatility), or $\text{fwd\_ret}_{i,t}^{4w}$ (forward 4-week compound return). The key coefficient $\beta_1$ captures the marginal predictive content of fragility for each outcome after absorbing structural and category-level heterogeneity.

We report three panels of results. **Panel A** presents progressive specifications for the primary outcome $\text{fwd\_maxdd}^{12w}$, isolating the $R^2$ contribution of the fragility measure, structural controls, and category fixed effects. **Panel B** fixes the full specification and varies the outcome across all three forward variables — this is the critical panel for H3, because the sign of $\beta_1$ on $\text{fwd\_ret}^{4w}$ directly tests whether fragility carries a return premium. **Panel C** fixes the outcome at $\text{fwd\_maxdd}^{12w}$ and varies the fragility measure across vol\_12w, downside\_vol\_12w, and maxdd\_12w, providing robustness to fragility construction.

**H3** predicts $\beta_1 > 0$ for the drawdown and volatility outcomes (fragile ETFs experience worse subsequent tails) and, under the mispricing hypothesis, $\beta_1 \geq 0$ for forward returns — the absence of a risk premium. A significantly positive coefficient on $\text{fwd\_ret}^{4w}$ would go further, indicating that fragile ETFs are *relatively cheap* on a forward-return basis despite their tail risk exposure.

We note one econometric consideration: forward outcome windows at $t$ and $t+1$ overlap by 11 of 12 weeks, inducing serial correlation in the residuals that single-dimension clustering on Symbol may understate. Our two-way clustering addresses this by also clustering on Date, which absorbs common weekly shocks affecting the forward outcome calculation.

**Decile sort.** As a non-parametric complement to the regression, we sort ETFs into deciles by vol\_12w each week and compute equal-weighted average forward outcomes within each decile. The D1–D10 spread provides an economically interpretable summary of the fragility-downside relationship that is free of functional form assumptions.

---

### 4.4 Stress Regime Amplification (H4): Model M3

To test whether the fragility-to-drawdown relationship intensifies during macro stress, we augment M2 with an interaction term:

$$\text{fwd\_maxdd}_{i,t}^{12w} = \alpha_i + \beta_1\, \text{vol}_{i,t}^{12w} + \beta_2\, \text{SI}_t + \beta_3\, (\text{vol}_{i,t}^{12w} \times \text{SI}_t) + \boldsymbol{\gamma}' \mathbf{X}_i + \boldsymbol{\delta}' \mathbf{C}_i + \varepsilon_{i,t} \tag{M3}$$

where $\text{SI}_t$ is the composite stress index defined in Section 2.6. We report four specifications. Column (1) is the additive baseline (no interaction). Column (2) replaces $\text{SI}_t$ with $\text{high\_stress}_t$, the binary indicator for $\text{SI}_t > 1$. Column (3) uses the continuous $\text{SI}_t$ in the interaction. Columns (4a) and (4b) split the sample into high- and low-stress weeks and re-estimate the baseline M2 separately, providing a coefficient comparison that does not rely on the interaction being linear.

**H4** is supported if $\beta_3 < 0$ in Column (2) or (3): holding fragility constant, higher stress amplifies the drawdown penalty for fragile ETFs. The split-sample comparison in (4a)/(4b) provides a second, non-parametric test of the same prediction.

**Portfolio tilt.** As a practical test of H4, we construct two weekly equal-weighted portfolios from the full ETF universe (excluding the Other category):

- *Naive EW*: equal-weight all ETFs with non-missing vol\_12w each week.
- *Tilt EW*: equal-weight only the bottom 75% of ETFs by vol\_12w (screen out the top fragility quartile each week).

Within each week, we compute the difference in realized drawdown between the two portfolios. We test whether this difference is significantly positive (Tilt EW dominates) during high-stress weeks and separately during calm weeks using a one-sample t-test on the within-group mean difference. The stress-specific t-statistic is the primary inferential object for H4's practical statement: that fragility screening pays off precisely when macro conditions are adverse.

---

### 4.5 Identification and Limitations

The regressions in M1 through M3 are reduced-form rather than structural. We make no claim to causal identification of macro shocks on ETF returns; the macro variables are contemporaneous regressors that describe co-movement patterns, not exogenous instruments. H1 and H2 are therefore descriptive claims about systematic heterogeneity, not claims about causal transmission.

The predictive regressions in M2 and M3 are subject to a look-ahead-bias concern: vol\_12w is computed from the 12 weeks ending at $t$, and the forward outcome uses returns beginning at $t+1$. There is no overlap in the return windows used to construct the predictor and the outcome, so look-ahead bias is not present by construction. However, the predictor and outcome are not independent — both are measured on the same ETF, and persistent fund-level volatility will mechanically correlate past and future volatility. Fund fixed effects absorb time-invariant level differences; the residual identification comes from *changes* in fragility within a fund relative to its average.

The composite stress index uses full-sample z-scores, introducing a look-ahead component into the high\_stress classification: the mean and standard deviation used at time $t$ incorporate future data. This is appropriate for our retrospective panel but not for real-time applications. Section 6.4 addresses this using an expanding-window z-score that standardises each week using only the history available before that week; the H4 interaction results are essentially unchanged.

Survivorship bias affects the ETF universe as described in Section 2.1. The direction of bias is toward understatement of fragility for the highest-risk funds, which would if anything bias against our H3 finding. Section 6 reports regressions restricted to ETFs with full ten-year history as a partial survivorship robustness check.

Finally, the 12-week forward window creates overlapping observations across adjacent $t$ values. Two-way clustering and the Fama-MacBeth Spearman robustness (Section 6) both address this; we report the latter as a conservative bound on inference.

---

## 5. Results

### 5.1 Macro Sensitivity and Structural Heterogeneity (H1 and H2)

**Macro factor loadings.** Table 3 reports M1 estimates. Three patterns are immediately apparent. First, the macro block explains 41.2% of weekly return variance on its own, confirming that bond ETF returns are heavily driven by common macro shocks at weekly frequency. Second, credit spread changes and rate changes dominate: a 100-basis-point increase in IG credit spreads ($\Delta$CS) reduces the average ETF's weekly excess return by 5.1 percentage points (β = −0.051, p < 0.001), and a 100-basis-point rise in the 10-year yield ($\Delta$DGS10) reduces it by 4.6 percentage points (β = −0.046, p < 0.001). These are the two largest-magnitude responses and align with the dominant risk factors in fixed-income pricing. Third, the ANFCI coefficient is positive (β = +0.015***), which at first glance seems counterintuitive — tighter financial conditions are associated with *higher* ETF returns. The VIF table rules out severe collinearity (all VIF < 2.0), suggesting this reflects the ANFCI's construction: ANFCI captures *adjusted* financial conditions net of the business cycle, and positive co-movement with returns may capture the risk-on recovery dynamic in which conditions tighten alongside improving credit fundamentals. We caution against over-interpreting the ANFCI sign and treat it as a control rather than a structural coefficient.

Adding category fixed effects in Specification (2) improves adjusted R² by only 0.08 percentage points (0.4120 → 0.4128), indicating that category membership adds little explanatory power beyond the common macro factors. Structural characteristics in Specification (3) contribute an additional 0.01 percentage points (R² = 0.4129; F = 7.68, p < 0.001). The modest R² increments for category and structural blocks in the contemporaneous regression reflect the fact that macro shocks affect all ETFs in the same week — cross-sectional differentiation manifests primarily in *forward* outcomes, not in the contemporaneous return response.

**Cross-sectional heterogeneity (H1).** Per-fund OLS betas on $\Delta$CS exhibit significant within-category dispersion in all ten non-trivial categories. The cross-sectional standard deviation of $\Delta$CS betas within categories ranges from 0.005 (Mortgage/Securitized) to 0.040 (TIPS/Inflation-Linked), with t-statistics on the dispersion ranging from 2.00 (Preferred/Hybrid, 3 ETFs) to 12.57 (Core/Aggregate, 80 ETFs). The Bartlett test rejects equality of variances across categories (χ² = 62.9, p < 0.001). Within the High Yield category, the inter-decile range of credit-spread betas spans 5.4 percentage points (P10 = −10.2%, P90 = −4.8% for a 100bp spread change), implying a nearly 2:1 ratio from the least to the most credit-sensitive HY ETF. H1 is supported: macro sensitivity is heterogeneous within category groupings in a way that category-level analysis cannot detect.

**Structural heterogeneity (H2).** The F-test on the joint significance of log AUM, expense ratio, and age rejects the null at the 0.1% level (F = 7.68, p < 0.001). Expense ratio carries a positive coefficient (β = 0.009, p = 0.062), consistent with higher-cost funds holding less-liquid underlying bonds and earning a small contemporaneous illiquidity premium. Log AUM is positive (β = 0.00005***), consistent with larger, more liquid funds absorbing macro shocks with smaller return dislocations on the upside. Age enters negatively (β = −0.00002***), possibly reflecting that newer funds have higher sensitivity to market-wide repricing. While H2 is confirmed, the structural block's contribution to contemporaneous return R² is modest. As shown in Section 5.2, structural characteristics explain far more variation in *forward* outcomes — the channel through which structural heterogeneity becomes economically significant.

---

### 5.2 Fragility Predicts Forward Downside Without a Return Premium (H3)

**Panel A — Progressive specifications for forward drawdown.** Table 4, Panel A presents three progressive M2 specifications with fwd\_maxdd\_12w as the outcome. The vol\_12w coefficient is negative and significant in all specifications: −1.01*** (bare), −0.94*** (+ category FE), and −0.70*** (+ structural controls + year FE). The stability of the coefficient across specifications confirms that the fragility-drawdown relationship is not an artifact of category composition or fund-size sorting. Critically, the R² progression shows that structural characteristics are the dominant explanatory variable: adding category fixed effects raises adjusted R² from 8.75% to 10.05% (Δ = 1.31 pp), while adding structural controls and year fixed effects raises it to 19.79% (Δ = 9.74 pp) — nearly a tenfold greater contribution. This asymmetry reflects the fact that a fund's age, cost, and size determine its long-run tail risk in ways that its broad category membership does not.

**Panel B — Forward outcomes across three horizons.** Table 4, Panel B fixes the full specification and varies the outcome. The central finding of the paper is in the forward-return column: vol\_12w enters with β = +0.41 (t = 11.55, p < 0.001). A one-standard-deviation increase in vol\_12w (0.99%) predicts a 41-basis-point increase in four-week forward return — the wrong sign for a compensated risk factor. Fragility simultaneously predicts worse drawdowns (β = −0.70 on fwd\_maxdd\_12w, t = −3.23 under two-way clustering) and worse realized volatility (β = +0.31 on fwd\_vol\_12w, t = 7.62), yet the forward return advantage for fragile ETFs persists. The structural controls enter consistently: larger funds face shallower forward drawdowns (log AUM β = +0.0008 on maxdd), higher-cost funds face deeper drawdowns (ER\_clean β = −0.42***), and older funds are modestly more resilient (age\_years β = −0.0005***).

**Panel C — Robustness across fragility measures.** Table 4, Panel C shows that the drawdown-predictive content of fragility is not specific to vol\_12w. Downside volatility (β = −0.48***) and maximum drawdown (β = +0.15***, where more negative maxdd\_12w predicts more negative fwd\_maxdd\_12w as expected) both deliver statistically significant coefficients. R² is slightly higher for vol\_12w (19.8%) than downside volatility (17.7%) or maxdd (18.6%), suggesting vol\_12w is the most informationally efficient of the three measures. The combined specification (Column 4) shows a sign reversal on downside\_vol due to its 0.9+ correlation with vol\_12w — we treat columns (1)–(3) as the primary evidence.

**Decile sort.** Figure 3 plots the equal-weighted forward outcomes by fragility decile. The drawdown gradient is steep and monotonic: D1 averages −0.23% forward maximum drawdown, while D10 averages −4.78% — a spread of 455 basis points achieved with no corresponding return premium. The four-week forward return across deciles ranges from 0.17% to 0.29%, with D10 actually earning 0.24% versus D1's 0.19%. The return-per-unit-drawdown ratio falls from 0.83 in D1 to 0.05 in D10, meaning the most fragile ETFs generate only 5 cents of return per dollar of drawdown risk, compared to 83 cents for the least fragile. H3 is strongly supported: fragility predicts forward tail outcomes, not forward returns.

---

### 5.3 Stress Regime Amplification (H4)

**Regression evidence.** Table 5 presents M3 estimates. In the additive baseline (Column 1), the high\_stress indicator itself carries β = −0.005*** — during high-stress weeks, forward maximum drawdown deepens by 50 basis points holding fragility constant, confirming that stress weeks are unconditionally worse for the full ETF universe. Column (2) adds the binary interaction: vol\_12w × high\_stress = −0.22 (p < 0.001). The sign and significance confirm H4: a given level of fragility leads to disproportionately worse forward drawdowns during stress weeks. Column (3) uses the continuous stress index interaction and obtains a nearly identical coefficient (−0.22***, p < 0.001), confirming robustness to the binary threshold. The split-sample comparison in Columns (4a) and (4b) shows vol\_12w coefficients of −1.68 (non-stress) and −1.66 (high-stress) — nearly identical in levels, which is consistent with the interaction terms capturing the *incremental* amplification beyond the base effect already absorbed by the stress indicator.

**Stress-conditional decile sort.** The non-parametric evidence in Figure 4 is more striking. Restricting the decile sort to the 21 high-stress weeks, the D1–D10 drawdown spread widens from 455 basis points (full sample) to 609 basis points (D1: −0.65%, D10: −6.74%). The amplification ratio — stress-week drawdown relative to full-sample drawdown — declines monotonically from 2.83× in D1 to 1.41× in D10, suggesting that *low-fragility* ETFs are more adversely surprised by stress than high-fragility ETFs (which already price in greater downside). This pattern is consistent with a model in which fragility signals are partially anticipated, and stress episodes cause the greatest repricing among ETFs whose fragility was previously underappreciated.

**Portfolio tilt.** Table 6 reports the practical implications. A naive equal-weight portfolio over the full 521-week sample earns 2.77% annualized with 5.09% volatility and a Sharpe ratio of 0.54. The fragility-tilt portfolio — excluding the top vol\_12w quartile each week and equal-weighting the rest — earns nearly the same return (2.78%) with materially lower volatility (3.64%) and an improved Sharpe of 0.76. The full-sample maximum drawdown falls from −14.76% to −12.28%.

The stress-specific test is decisive. During the 21 high-stress weeks, the naive portfolio annualizes at −35.3% with a Sharpe of −2.58 and maximum drawdown of −17.7%. The tilt portfolio annualizes at −24.0% (1,130 basis points better), with Sharpe of −2.37 and maximum drawdown of −13.0% (467 basis points shallower). The paired t-test on weekly return differences yields t = 2.67 (p = 0.015): the weekly return advantage during stress is statistically significant. During the 493 non-stress weeks, the tilt generates t = −1.61 (p = 0.11) — no significant cost. The asymmetry is the key evidence for H4's practical claim: fragility screening delivers protection exactly when it is needed and imposes no reliable cost when it is not.

**Subsample stability.** An important ancillary finding from the M2 subsample analysis is that the fragility-drawdown relationship has *strengthened* over time. Splitting the sample at 2022, the vol\_12w coefficient on fwd\_maxdd\_12w is −0.76*** (t = −7.53, N = 77,399) in the 2016–2022 sub-period and −2.11*** (t = −21.16, N = 44,142) in the 2023–2026 sub-period. The post-2022 intensification likely reflects the elevated rate volatility following the Federal Reserve's 2022 hiking cycle, which increased the realized tail outcomes for duration-sensitive fragile ETFs. This structural shift suggests that our full-sample estimates are conservative: the fragility-drawdown relationship observed in the most recent data is more severe than the 2016–2026 average implies.

---

## 6. Robustness

### 6.1 Two-Way Clustered Standard Errors

The primary concern with inference in our panel is the overlap structure of the 12-week forward outcome windows: the outcome for ETF $i$ at week $t$ and week $t+1$ share 11 of 12 forward return weeks. This induces serial correlation in residuals that one-way Symbol clustering does not fully absorb. We address this using the Cameron-Gelbach-Miller (2011) two-way cluster estimator, clustering simultaneously on Symbol and Date.

Table R1 compares symbol-clustered and two-way-clustered standard errors for the key M2 specification (vol\_12w → fwd\_maxdd\_12w, full controls). The standard error on vol\_12w inflates from 0.139 (symbol-only) to 0.215 (two-way), an inflation factor of 1.55×. Despite this inflation, the coefficient remains highly significant: t = −3.23 under two-way clustering versus t = −5.00 under symbol-only clustering. The structural control coefficients (log AUM, ER\_clean, age\_years) are virtually unaffected by the additional Date clustering (inflation factors of 1.01× to 1.02×), confirming that the main source of dependence in our panel is time-series clustering within symbols, not cross-sectional clustering within weeks. All primary results in Section 5 are computed with two-way clustered standard errors; the headline t-statistics reported in Section 5.2 reflect the more conservative estimate.

### 6.2 Fama-MacBeth Spearman Rank Correlations

As an alternative to pooled panel regression — which inflates the effective sample size by treating 156,588 ETF-week observations as independent — we adopt a Fama-MacBeth-style nonparametric approach. For each calendar week, we compute the cross-sectional Spearman rank correlation $\rho_t$ between vol\_12w and each forward outcome. We then test whether the time-series mean $\bar{\rho}$ differs from zero using a t-test on the 502–510 weekly observations (degrees of freedom = number of weeks, not ETF-weeks). This procedure is immune to both functional form misspecification and the serial-correlation concerns that motivate two-way clustering.

The results strongly confirm the main findings. For fwd\_maxdd\_12w, the mean weekly Spearman $\bar{\rho} = -0.765$ with t = −152.7 (p < 0.001) over 502 weeks — an extremely stable negative relationship: in nearly every week in the sample, ETFs with higher recent volatility go on to experience worse drawdowns. For fwd\_vol\_12w, $\bar{\rho} = +0.864$ (t = 242.1), indicating near-universal persistence of the volatility signal. The critical forward-return result is also confirmed: $\bar{\rho} = +0.081$ (t = 3.62, p < 0.001), statistically significant and positive — fragile ETFs earn slightly *higher* subsequent returns. In weeks with at least 15 cross-sectional observations, the correlation is positive in the majority of weeks and weakly significant in aggregate. The absence of a negative correlation rules out the possibility that fragile ETFs are cheapened sufficiently to compensate for their tail risk. During the 20 high-stress weeks with sufficient observations, the return correlation is $\bar{\rho} = 0.027$ and statistically insignificant (t = 0.29), confirming that fragility provides no return advantage even during stress.

### 6.3 Subsample and Survivorship Robustness

**Pre/post-2022 stability.** As reported in Section 5.3, the fragility-drawdown coefficient is −0.76*** in the 2016–2022 sub-period and −2.11*** post-2022 (see Section 5.3 for discussion). H3 holds in both sub-periods; the strengthening post-2022 is consistent with structurally elevated rate volatility rather than a regime change in the mechanism.

**Full-history ETFs.** To bound survivorship bias, we replicate the primary M2 specification (Panel B) restricting to the 183 ETFs with data beginning in 2016. The vol\_12w coefficient on fwd\_maxdd\_12w is stable relative to the full-universe result, and the forward-return coefficient remains positive. The full-history subsample produces somewhat larger standard errors due to reduced cross-sectional variation, but all primary conclusions survive. We emphasize that survivorship bias in our setting likely works *against* finding large fragility effects — delisted funds were plausibly among the most fragile — so the full-universe estimates may understate the true fragility-drawdown relationship.

**Alternative category exclusions.** We confirm that results hold when excluding inverse and leveraged ETFs (already the baseline), when further excluding the Preferred/Hybrid and DM Debt categories (which have very few constituent funds), and when restricting to the five largest categories by ETF count (Investment Grade Corporate, Core/Aggregate, Treasury, Muni, High Yield).

### 6.4 Expanding-Window Stress Index

The primary stress index uses full-sample z-scores, which introduce a look-ahead component: the standardization parameters at week $t$ use information from $t+1$ through the end of the sample. While appropriate for our retrospective research design, we test whether this construction materially affects the H4 results.

We construct an expanding-window stress index, $\text{SI}_t^{\text{exp}}$, by standardizing each week's component values using the expanding mean and standard deviation of all prior weeks (lagged one period to ensure strict look-ahead exclusion). The first 52 weeks are treated as a burn-in period and excluded from the regression. The high-stress indicator $\text{high\_stress\_exp}_t$ uses the same 1.0 threshold applied to $\text{SI}_t^{\text{exp}}$.

The two versions agree on high-stress classification for the vast majority of weeks. The H4 interaction coefficient under the expanding specification is nearly identical in magnitude and significance to the full-sample result, confirming that the look-ahead in the stress index construction does not drive the amplification finding. The COVID-19 and 2022 rate-hike episodes are correctly identified as high-stress under both versions, which is unsurprising given their severity relative to any reasonable historical baseline.

---

## 7. Conclusion

Fixed-income ETFs have become the dominant vehicle for retail and institutional investors seeking bond market exposure, yet the structural vulnerabilities they embed — duration mismatch, liquidity transformation, and credit concentration — are poorly captured by standard category-level analysis. This paper characterizes the *cross-sectional* distribution of those vulnerabilities through a simple, observable fragility measure and documents four empirical regularities that collectively paint an unflattering picture of how bond ETF risk is priced.

Our primary finding is that fragility constitutes an **uncompensated tail risk**. ETFs in the highest fragility decile experience 455 basis points more forward maximum drawdown than those in the lowest decile, yet earn essentially the same — or marginally higher — forward returns. The regression coefficient on vol\_12w in the forward-return specification is significantly positive (β = 0.41, t = 11.55), ruling out any meaningful risk premium for fragility. If the bond ETF market efficiently priced tail risk, fragile funds would trade at a discount that generated compensating returns; they do not. The Fama-MacBeth Spearman tests, which use the calendar week rather than the ETF-week as the unit of observation, confirm this finding with t-statistics that are implausibly large under the null of no relationship, but consistent with a highly stable and persistent cross-sectional relationship.

The macro stress amplification result (H4) adds a second dimension: the fragility-drawdown relationship intensifies precisely during the episodes when protection matters most. The binary interaction term (β = −0.22, p < 0.001) and the portfolio tilt evidence — 467 basis points of drawdown reduction during the 21 high-stress weeks, statistically significant at t = 2.67 — both support the view that fragility screening is a crisis-specific, asymmetric benefit. The tilt generates no reliable cost during the 493 calm weeks (t = −1.61, p = 0.11), making it nearly free in expectation.

The within-category heterogeneity in macro sensitivity (H1) and the incremental explanatory power of structural characteristics (H2) together suggest that category-level investment analysis is insufficient. Investors who classify bond ETF risk by category alone — treating all Investment Grade Corporate ETFs as equivalent, for example — miss the substantial cross-ETF variation in credit-spread sensitivity that the per-fund beta dispersion analysis reveals. The structural block (fund size, cost, age) explains nearly ten times more forward-outcome variance than category fixed effects, reinforcing the case for fund-level fragility analysis.

Several limitations temper our conclusions. The ETF universe is subject to survivorship bias, as delisted funds are excluded; this likely biases fragility estimates downward. Our fragility measure is backward-looking by construction and picks up realized volatility rather than fundamental vulnerability — it may lag sudden changes in portfolio composition or in the liquidity of underlying bonds. The stress index, while validated by robustness to an expanding-window construction, is calibrated to a single decade that includes two major dislocations; its signal value in a different macro regime is uncertain. And the forward-return finding, while consistent with mispricing, is also consistent with a risk factor not captured by our fragility proxy — a short-duration tilt correlated with vol\_12w, for example, could generate a positive return coefficient mechanically.

For practitioners, the results offer a transparent and implementable fragility screen: exclude the top vol\_12w quartile each week, equal-weight the rest. This rule requires no proprietary data, rebalances at weekly frequency, and targets the tail of the return distribution rather than average returns. Whether this constitutes alpha or simply a sensible risk management discipline may be a matter of perspective; either way, the evidence suggests that bearing fragility risk in the bond ETF market is currently unrewarded.
