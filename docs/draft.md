# Macro Stress, Liquidity, and the Cross-Section of Bond ETF Fragility

**Travon Lucius**<br>
tlucius16@gmail.com<br>
April 2026


## Abstract

Fixed-income ETFs offer daily exchange liquidity on portfolios whose underlying bonds often trade in over-the-counter or primary auction markets. This paper studies cross-sectional risk differences inside the fixed-income ETF universe. Using a panel of 347 U.S. fixed-income ETFs over 521 weeks from April 2016 to April 2026, we show that broad categories hide economically meaningful macro sensitivity dispersion: within High Yield, for example, the P10/P90 credit-spread beta range implies nearly a 2:1 difference between the least and most credit-sensitive funds. We then measure ETF-level fragility as trailing 12-week volatility of weekly excess returns. Fragility predicts forward downside outcomes, but part of that signal reflects duration exposure during high rate-volatility regimes: ETFs in the highest fragility decile experience average 12-week forward maximum drawdowns of −4.79%, compared with −0.22% for the lowest decile. The same high-fragility ETFs do not earn meaningfully higher 4-week forward returns, suggesting that recent fragility is weakly compensated relative to its downside exposure. The most useful stress evidence comes from a simple portfolio screen: excluding the top fragility quartile reduces maximum drawdown by 467 basis points during high-stress weeks, with no statistically reliable cost during calm periods. The evidence supports a practical risk management interpretation: publicly observable ETF return dynamics contain information about forward tail risk that broad fixed-income categories miss.

**JEL codes:** G11, G12, G23  
**Keywords:** fixed-income ETFs, fragility, bond market liquidity, macro stress, cross-sectional returns, risk management

---

## 1. Introduction

Fixed-income ETFs have grown rapidly as they make bond exposure cheap, transparent, and easy to trade for investors without access to the primary market in which they originate. Their structure also creates a tension: ETF shares trade continuously on exchanges, while many underlying bonds trade infrequently through dealers and can become difficult to price during stress. Authorized participants normally arbitrage ETF prices back toward net asset value, but that mechanism can weaken when balance sheet capacity is scarce, bond quotes are stale, or creation/redemption baskets become costly to assemble. The result is an ETF specific form of fragility: secondary market prices can begin to reveal liquidity and arbitrage stress before the underlying portfolio fully reprices.

This paper asks whether that fragility is visible in public return data and whether investors are compensated for bearing it. We define fragility as trailing 12-week volatility of weekly excess returns. The measure is intentionally simple. It is not a structural estimate of liquidity, duration, or credit risk; rather, it is a transparent signal of recent instability in the ETF price itself. We validate the measure with downside volatility and drawdown variants.

Four findings organize the analysis. First, macro sensitivity varies substantially within fixed-income ETF categories, so category labels alone miss important fund-level risk differences. Second, fund characteristics such as size, age, and expense ratio add information beyond category membership. Third, recent fragility predicts forward drawdowns and realized volatility, but not meaningfully higher forward returns; duration and rate-volatility exposure explain part of this relation. Fourth, fragility screens are most valuable during macro stress, when avoiding the most fragile quartile materially reduces drawdowns with little evidence of a calm period cost.

The contribution is therefore practical and empirical. Prior work studies ETF fragility in equity markets, bond mutual fund flow fragility, and the effect of ETF ownership on bond liquidity. This paper focuses on the cross-section of fixed-income ETFs and shows that a publicly observable price-based signal contains useful information about future tail risk. The results are consistent with weak compensation for fragility risk, though they do not by themselves prove mispricing or investor irrationality. Fragility may also proxy for duration, credit beta, convexity, carry, or unobserved portfolio liquidity; the empirical tests below are designed to narrow those alternative interpretations, not to identify a single mechanism.

The rest of the paper proceeds as follows. Section 2 describes the data and variables. Section 3 defines the fragility measures and stress index. Section 4 presents the empirical design and limitations. Section 5 reports the main results. Section 6 summarizes robustness checks. Section 7 concludes.

## 2. Data

### 2.1 ETF Universe

The sample begins with U.S. exchange listed fixed-income ETFs from the ETFDB screener. We require at least five years of continuous price history, yielding 347 ETFs observed weekly from April 2016 to April 2026. Funds are grouped into broad research categories including Investment Grade Corporate, High Yield, Treasury/Government, Core/Aggregate, EM Debt, TIPS, Muni, Mortgage/Securitized, Preferred/Hybrid, and Other. Leveraged and inverse products are assigned to Other and excluded from the main portfolio tests.

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

To classify stress weeks, we average standardized changes in financial conditions, credit spreads, bond market volatility, and equity market volatility:

$$\text{SI}_t = \frac{1}{4}\left(z[\Delta\text{ANFCI}_t] + z[\Delta\text{CS}_t] + z[\Delta\text{MOVE}_t] + z[\Delta\text{VIX}_t]\right)$$

where $z[\cdot]$ denotes full sample standardization. The high-stress indicator equals one when $\text{SI}_t > 1.0$, identifying 21 weeks concentrated in the COVID-19 shock and the 2022 rate-hike cycle. Because a full sample standardization is not a real time signal, Section 6 checks an expanding window version.

### 2.7 Forward Outcome Variables

The predictive tests use three forward outcomes:

- **fwd\_ret\_4w**: Compound return over the next 4 weeks, $\prod_{k=1}^{4}(1+r_{i,t+k}) - 1$.
- **fwd\_maxdd\_12w**: Maximum drawdown over the next 12 weeks (same computation as maxdd\_12w but applied to future returns).
- **fwd\_vol\_12w**: Standard deviation of weekly returns over the next 12 weeks.

All outcomes begin at $t+1$, so the trailing fragility window and forward outcome window do not overlap.

### 2.8 Panel Summary

The final unbalanced panel contains roughly 157,000 ETF week observations, with exact counts varying by variable because of rolling-window and forward-outcome availability. The main predictive regressions use 121,541 observations after requiring complete fragility measures, controls, and forward outcomes. Table 2 reports descriptive statistics. Table 3 summarizes the cross-sectional category structure and shows that fragility dispersion remains meaningful inside broad categories.

**Data sources.** ETF universe and fund metadata come from the ETFDB screener as of April 2026. Prices are Yahoo Finance adjusted closes, aggregated to Friday weekly frequency. The risk-free rate and macro variables are from FRED where available, with VIX and MOVE observed through Yahoo Finance tickers and geopolitical risk from Iacoviello's daily GPR index. All macro series are converted to weekly frequency and merged to the ETF panel by calendar week.

\setcounter{table}{1}
\begin{table}[H]
\centering
\scriptsize
\caption{Descriptive statistics. Returns, volatility, drawdowns, and expense ratios are in percent.}
\begin{tabular}{lrrrr}
\toprule
Variable & N & Mean & Median & P75 \\
\midrule
Weekly return & 157,171 & 0.05 & 0.07 & 0.38 \\
Weekly excess ret. & 157,171 & 0.01 & 0.02 & 0.34 \\
vol\_12w & 154,735 & 0.80 & 0.52 & 0.94 \\
fwd\_ret\_4w & 155,779 & 0.21 & 0.27 & 0.96 \\
fwd\_maxdd\_12w & 152,995 & -2.31 & -1.16 & -0.43 \\
fwd\_vol\_12w & 152,995 & 0.80 & 0.53 & 0.94 \\
Expense ratio & 157,171 & 0.33 & 0.23 & 0.41 \\
Age & 157,171 & 7.80 & 7.19 & 11.29 \\
\bottomrule
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\scriptsize
\caption{Category counts and fragility dispersion.}
\begin{tabularx}{\columnwidth}{Xrrr}
\toprule
Category & ETFs & Med. vol & P10--P90 vol \\
\midrule
Core/Aggregate & 81 & 0.62 & 0.14--0.89 \\
IG Corporate & 68 & 0.71 & 0.18--0.99 \\
High Yield & 49 & 0.85 & 0.57--1.02 \\
Muni & 46 & 0.60 & 0.27--0.86 \\
Treasury/Govt & 37 & 0.54 & 0.03--1.85 \\
TIPS & 16 & 0.66 & 0.29--1.28 \\
EM Debt & 15 & 1.11 & 0.70--1.33 \\
Mortgage/Sec. & 14 & 0.56 & 0.18--0.82 \\
DM Debt & 5 & 0.88 & 0.65--1.05 \\
Preferred/Hybrid & 3 & 1.80 & 1.77--1.84 \\
Short Duration & 1 & 0.16 & 0.16--0.16 \\
\bottomrule
\end{tabularx}
\vspace{0.2em}
\begin{minipage}{0.98\columnwidth}
\scriptsize Notes: Volatility entries are ETF-level averages of vol\_12w, reported in percent. P10--P90 is the within-category dispersion across ETFs.
\end{minipage}
\end{table}

## 3. Fragility Measurement

### 3.1 Why Rolling Volatility Captures Fragility

Bond ETF fragility is not directly observable. Holdings are disclosed with delay, underlying bond bid-ask spreads are unavailable at daily frequency for much of the universe, and ETF flows are filtered through authorized participant activity. We therefore use secondary market return dynamics as the observable signal.

Rolling volatility is a plausible ETF fragility proxy for three reasons. First, ETF prices aggregate information about underlying portfolio risk, arbitrage capacity, and secondary market liquidity. Second, when underlying bonds become hard to trade or price, ETF premiums and discounts can widen, showing up as return instability. Third, elevated recent volatility is not only a generic risk measure; in bond ETFs it can reflect impairment in the transmission between ETF prices, NAVs, and underlying cash-bond markets. The contribution is therefore not that volatility predicts volatility, but that ETF-specific return instability is informative about forward tail outcomes in a market structure where liquidity transmission can become impaired. Because volatility can also proxy for duration exposure and rate volatility, we treat the mechanism as an interpretation rather than a separately identified causal channel. Flow-based fragility remains an important complementary measure, but price based fragility is available consistently across the full ETF universe.

### 3.2 Three Fragility Metrics

The primary measure, **vol\_12w**, is the 12-week trailing standard deviation of weekly excess returns. It captures total return instability and has minimal missing data. Two robustness measures separate downside from total volatility: **downside\_vol\_12w**, the semi-deviation of negative weekly excess returns, and **maxdd\_12w**, the worst peak-to-trough cumulative loss within the same trailing window. The three measures are highly correlated in the cross-section (pairwise Spearman $\rho > 0.85$), so the main tests use vol\_12w and report the others as robustness checks.

### 3.3 Time-Series Properties

Fragility is persistent within funds but can move sharply during market stress. Category rankings are broadly intuitive, long duration and credit sensitive ETFs tend to be more fragile than aggregate bond ETFs but the ordering can invert when normally liquid markets become impaired. This time variation motivates a fund week panel rather than a static category analysis.

### 3.4 Composite Stress Index: Construction and Validation

The stress index SI$_t$ aggregates weekly changes in ANFCI, credit spreads, MOVE, and VIX. It is designed to capture co-occurring stress across funding, credit, rates, and equity volatility channels. High-stress weeks account for 4.0% of the sample and cluster in the COVID-19 shock and the 2022 rate hike cycle. The baseline uses a binary high-stress indicator for interpretability and checks the continuous index and expanding-window standardization in robustness tests.

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

### 4.4 Stress Regime Amplification (H4): Model M3

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

where $\text{SI}_t$ is either the continuous stress index or the binary high-stress indicator. H4 is supported if $\beta_3 < 0$: conditional on fragility, stress weeks are associated with deeper forward drawdowns. We interpret this interaction alongside stress conditional decile sorts and the portfolio tilt below, rather than relying on any single specification.

**Portfolio tilt.** As a practical test of H4, we compare two weekly equal-weighted portfolios, excluding the Other category:

- *Naive EW*: equal-weight all ETFs with non-missing vol\_12w each week.
- *Tilt EW*: equal-weight only the bottom 75% of ETFs by vol\_12w (screen out the top fragility quartile each week).

The key question is whether the tilt reduces losses during stress without imposing a reliable cost during calm periods.

### 4.5 Identification and Limitations

The analysis is reduced-form. The macro regressions describe co-movement, not causal transmission. The predictive regressions avoid mechanical look-ahead because fragility uses returns through $t$ and forward outcomes begin at $t+1$, but persistence in volatility means past and future risk are naturally related. The stress index uses full sample standardization in the baseline, which is appropriate for retrospective classification but not for real time trading; an expanding-window version addresses this concern in Section 6. High-stress weeks cluster in the COVID-19 shock and the 2022 rate-hike cycle, so the stress evidence should be read as evidence from those episodes rather than from a broad sample of independent crises. Portfolio tests are gross of transaction costs, so the weekly tilt should be interpreted as a risk-management screen rather than a directly netted trading strategy. Finally, overlapping 12-week forward windows and multiple forward outcomes can inflate apparent precision, so we rely on two-way clustering, Fama-MacBeth rank correlations, and cross-sectional decile tests as robustness checks.

## 5. Results

### 5.1 Macro Sensitivity and Structural Heterogeneity (H1 and H2)

Table 4 shows that weekly bond ETF returns load heavily on common macro shocks, especially credit spread and Treasury rate changes. The macro block explains 41.2% of weekly return variation, while category controls add little incremental explanatory power in the contemporaneous return regression. This is unsurprising: macro shocks arrive at the same calendar time for all funds, so their largest effect is common.

The more important H1 result is cross-sectional. Per-fund credit spread betas vary significantly within all nontrivial categories, and the Bartlett test rejects equality of within category variance (χ² = 62.9, p < 0.001). Within High Yield, for example, the interdecile spread in credit spread betas implies nearly a 2:1 difference between the least and most credit-sensitive funds. Category labels therefore summarize broad exposure but do not fully describe fund level macro sensitivity.

Fund characteristics are jointly significant (F = 7.68, p < 0.001), though their contribution to contemporaneous return R² is modest. Their larger role appears in the forward-outcome regressions, where fund size, expense ratio, and age help explain differences in subsequent drawdown risk.

\begin{table}[H]
\centering
\scriptsize
\caption{Macro sensitivity and within-category heterogeneity.}
\begin{tabular}{lr}
\toprule
Statistic & Value \\
\midrule
Macro block R-squared & 41.2\% \\
Credit spread coefficient & -0.051 \\
10-year Treasury coefficient & -0.046 \\
HY credit beta P10/P90 & -0.102 / -0.048 \\
Bartlett test & $\chi^2 = 62.9$, $p < 0.001$ \\
\bottomrule
\end{tabular}
\end{table}

### 5.2 Fragility Predicts Forward Downside Without a Return Premium (H3)

Table 5 shows that recent fragility predicts future downside in the full specification with category and fund-characteristic controls. The result is not limited to the symmetric volatility measure: downside volatility and trailing maximum drawdown also predict worse forward drawdowns.

The key economic result is the contrast between downside and returns. A one standard deviation increase in vol\_12w predicts deeper forward drawdowns and higher forward realized volatility, but it does not predict a commensurate return premium. In the full specification, the coefficient on 4-week forward returns is positive (β = +0.41), while the decile sort shows D10 earning 0.23% versus 0.19% for D1 over the same horizon. The return relation is therefore positive on average but non-monotonic in the tails: mean forward returns peak around D8 and then flatten, while drawdowns continue to worsen through D10. This divergence is why the paper emphasizes weak compensation relative to downside exposure rather than a negative expected-return effect.

Figure 3 makes the magnitude clear. The lowest fragility decile has an average 12-week forward maximum drawdown of −0.22%, while the highest fragility decile has −4.79%, a 457-basis-point spread. The evidence therefore supports the narrower claim that fragility is weakly compensated relative to its forward downside risk.

\begin{table}[H]
\centering
\scriptsize
\caption{Fragility and forward outcomes (H3).}
\begin{tabular}{lrrr}
\toprule
Outcome / sort & Estimate & t-stat & N \\
\midrule
fwd\_maxdd\_12w & -0.695 & -3.23 & 121,541 \\
fwd\_vol\_12w & 0.313 & 7.62 & 121,541 \\
fwd\_ret\_4w & 0.413 & 11.55 & 121,541 \\
D10 - D1 max drawdown & -4.57 pp & -- & -- \\
D10 - D1 return & 0.04 pp & -- & -- \\
\bottomrule
\end{tabular}
\vspace{0.2em}
\begin{minipage}{0.98\columnwidth}
\scriptsize Notes: Regression rows report the coefficient on vol\_12w from the full M2 specification. t-statistics use two-way clustered standard errors by ETF and calendar week. Decile rows report equal-weighted high-minus-low fragility decile spreads.
\end{minipage}
\end{table}

\setcounter{figure}{2}
\begin{figure}[H]
\centering
\includegraphics[width=\columnwidth]{docs/figures/fragility_deciles.png}
\caption{Forward outcomes by fragility decile. Bars show 12-week forward maximum drawdown; line shows 4-week forward return.}
\end{figure}

### 5.3 Stress Regime Amplification (H4)

Table 7 provides the clearest H4 evidence. Excluding the top fragility quartile each week produces nearly the same full sample annualized return as the naive equal-weight portfolio, while reducing full sample maximum drawdown from 14.76% to 12.30%. During the 20 high-stress portfolio weeks with complete returns, the tilt portfolio's cumulative return is −10.57%, compared with −15.91% for the naive portfolio, and its maximum drawdown is 467 basis points shallower. The stress index identifies 21 high-stress weeks, but one week drops from the portfolio test because complete portfolio returns are unavailable. The paired weekly return difference during stress is statistically significant (t = 2.51, p = 0.021). During calm weeks, the return cost is not statistically reliable.

Table 6 gives supporting regression and decile-sort evidence. Stress weeks are unconditionally worse for ETF drawdowns, and the fragility stress interaction is negative in both binary and continuous stress specifications. The split sample coefficients are similar across stress and non-stress weeks, so the interaction should be read cautiously: the evidence is strongest for stress-conditional portfolio usefulness, not for a clean structural amplification parameter. During high-stress weeks, the D1–D10 forward drawdown spread widens from 457 basis points in the full sample to 628 basis points. Stress hurts the entire universe, but the most fragile ETFs remain the deepest source of tail exposure.

This asymmetry is the most practical evidence for H4. The interaction estimates are useful diagnostics, but the portfolio test is the main stress-regime result. The tilt's stress-period outperformance partly reflects an implicit reduction in long-duration and lower-quality credit exposure, consistent with the duration-beta robustness evidence in Section 6.5.

\begin{table}[H]
\centering
\scriptsize
\caption{Stress-regime evidence (H4).}
\begin{tabular}{lr}
\toprule
Statistic & Estimate \\
\midrule
High-stress indicator & -0.005 \\
vol\_12w $\times$ high\_stress & -0.218 \\
vol\_12w $\times$ stress\_index & -0.224 \\
High-stress D10 - D1 drawdown & -6.28 pp \\
\bottomrule
\end{tabular}
\vspace{0.2em}
\begin{minipage}{0.98\columnwidth}
\scriptsize Notes: Estimates are from M3 specifications with two-way clustered standard errors by ETF and calendar week. Decile spread is the high-minus-low fragility decile difference during high-stress weeks.
\end{minipage}
\end{table}

\begin{table}[H]
\centering
\scriptsize
\caption{Portfolio tilt performance.}
\begin{tabular}{llrrr}
\toprule
Regime & Portfolio/test & Ret. & Max DD & t-stat \\
\midrule
Full sample & Naive EW & 2.74\% & -14.76\% & -- \\
Full sample & Tilt EW & 2.75\% & -12.30\% & -- \\
High stress & Naive EW & -15.91\% & -17.70\% & -- \\
High stress & Tilt EW & -10.57\% & -13.03\% & -- \\
High stress & Tilt - Naive & +0.30 pp/wk & -- & 2.51 \\
Calm weeks & Tilt - Naive & -0.01 pp/wk & -- & -1.52 \\
\bottomrule
\end{tabular}
\vspace{0.2em}
\begin{minipage}{0.98\columnwidth}
\scriptsize Notes: Full sample returns are annualized. High-stress returns are cumulative over the 20 high-stress portfolio weeks with complete returns; the stress index identifies 21 high-stress weeks, but one week lacks complete portfolio returns. Tilt - Naive rows report average weekly return differences and paired t-statistics. Naive EW equal-weights all eligible bond ETFs each week, excluding the Other category; Tilt EW excludes the highest fragility quartile each week.
\end{minipage}
\end{table}

## 6. Robustness

### 6.1 Two-Way Clustered Standard Errors

Overlapping 12-week forward outcomes create serial dependence. Two-way clustering inflates the standard error on the main vol\_12w coefficient from 0.139 to 0.215, but the coefficient remains statistically significant (t = −3.23). The main conclusions do not rely on one-way fund clustering.

### 6.2 Fama-MacBeth Spearman Rank Correlations

As a nonparametric check, we compute weekly cross-sectional Spearman correlations between vol\_12w and each forward outcome, then test the time-series mean. The average rank correlation is strongly negative for forward drawdowns and strongly positive for forward volatility. The forward return correlation is small and positive, and it becomes statistically insignificant during high-stress weeks. This confirms that the main result is not driven by a linear panel specification.

Weekly decile-spread tests tell the same story. The average D10-D1 forward drawdown spread is −4.44 percentage points across weeks (t = −36.3), while the average D10-D1 forward return spread is only 0.08 percentage points and is not statistically different from zero (t = 0.63). The decile evidence therefore supports monotonic downside prediction, not a monotonic return premium.

The drawdown result is not sensitive to multiple-testing concerns across the three forward outcomes: the weekly decile-spread t-statistic for drawdowns is large enough that standard family-wise adjustments do not alter the inference. The forward-return result is treated more cautiously because the decile spread is small and statistically indistinguishable from zero.

### 6.3 Subsample and Survivorship Robustness

The fragility drawdown relationship is stable across available within-sample splits, and the main results also hold when restricting to the 183 ETFs with full history from 2016 and when excluding small or specialized categories. These checks reduce, but do not eliminate, concerns about survivorship and category composition.

As a simple out-of-sample screen, we estimate the top-quartile fragility cutoff using 2016--2021 data and apply that fixed threshold to 2022--2026. The tilt portfolio earns an 8.8% cumulative return versus 7.1% for the naive portfolio and reduces maximum drawdown from 13.2% to 7.4%, though the weekly return difference is not statistically reliable (t = 0.22). This supports the drawdown-control interpretation but not an alpha claim.

### 6.4 Expanding-Window Stress Index

Replacing the full sample stress index with an expanding-window version produces nearly identical H4 results. The COVID-19 and 2022 rate-hike episodes are identified under both methods, so the stress-regime findings are not an artifact of ex post standardization.

### 6.5 Duration-Beta Robustness

To separate ETF-level fragility from duration exposure, we estimate each fund's rate beta from weekly excess returns on changes in the 10-year Treasury yield and add that beta to the M2 drawdown regression. This robustness check uses a common category/characteristic control set across all three specifications, without year fixed effects, so that rate-volatility regime variation is not absorbed. Under this common specification, the baseline vol\_12w coefficient is −0.957 (t = −4.68). The coefficient remains negative and statistically reliable after controlling for static rate beta (β = −0.371, t = −2.30). A stricter specification that also includes the interaction of rate beta with MOVE attenuates the coefficient further and leaves it below conventional significance thresholds (β = −0.229, t = −1.57). This check shows that recent ETF volatility contains drawdown information beyond static category labels, but not that it is independent of time-varying duration exposure. A substantial component of the fragility signal is therefore interpretable as dynamic duration risk during high rate-volatility regimes.

## 7. Conclusion

Fixed-income ETF risk is not fully summarized by broad category labels. The clearest cross-sectional result is that macro sensitivity varies materially inside categories, including large within-category differences in credit-spread betas. Using a simple price-based fragility measure, this paper also shows that ETFs with elevated recent volatility face substantially worse forward drawdowns and higher realized volatility. The return compensation for that fragility is small relative to the downside gap: the highest fragility decile experiences 457 basis points more forward maximum drawdown than the lowest fragility decile, while earning nearly the same 4-week forward return. Duration and rate-volatility exposure explain a meaningful part of this relation, so the evidence should be read as a practical risk-screen result rather than proof of a standalone fragility factor independent of rates.

The stress results make the finding practically relevant. A weekly screen that excludes the top fragility quartile reduces drawdowns during high-stress weeks and does not impose a statistically reliable cost during calm periods. This does not prove that bond ETF fragility is mispriced; the tested duration result suggests that part of the signal reflects rate exposure, while credit beta, carry, convexity, and unobserved portfolio liquidity remain plausible additional channels. It does show, however, that a public and easily replicable ETF price signal contains information about future tail risk that investors using category level analysis alone would miss.

The most conservative interpretation is therefore risk management rather than alpha. Recent fragility identifies ETFs whose downside exposure is large relative to observed forward return compensation, especially in macro stress regimes. For investors allocating across fixed-income ETFs, that signal is useful precisely because it is simple, transparent, and available before the forward drawdown is realized.

## Disclaimer

This research was conducted independently and does not represent the views, opinions, or research of BlackRock, Inc. or any of its affiliates. The content is provided for informational and educational purposes only and should not be construed as investment advice or a recommendation to trade.

## References

Ben-David, Itzhak, Francesco Franzoni, and Rabih Moussawi. 2018. "Do ETFs Increase Volatility?" *Journal of Finance* 73 (6): 2471-2535.

Cameron, A. Colin, Jonah B. Gelbach, and Douglas L. Miller. 2011. "Robust Inference With Multiway Clustering." *Journal of Business & Economic Statistics* 29 (2): 238-249.

Chen, Qi, Itay Goldstein, and Wei Jiang. 2010. "Payoff Complementarities and Financial Fragility: Evidence from Mutual Fund Outflows." *Journal of Financial Economics* 97 (2): 239-262.

Chernenko, Sergey, and Adi Sunderam. 2020. "Do Fire Sales Create Externalities?" *Journal of Financial Economics* 135 (3): 602-628.

Coval, Joshua, and Erik Stafford. 2007. "Asset Fire Sales and Purchases in Equity Markets." *Journal of Financial Economics* 86 (2): 479-512.

Dannhauser, Caitlin D. 2017. "The Impact of Innovation: Evidence from Corporate Bond Exchange-Traded Funds." *Journal of Financial Economics* 125 (3): 537-560.

Goldstein, Itay, Hao Jiang, and David T. Ng. 2017. "Investor Flows and Fragility in Corporate Bond Funds." *Journal of Financial Economics* 126 (3): 592-613.

Iacoviello, Matteo. 2022. "Measuring Geopolitical Risk." *American Economic Review* 112 (4): 1194-1225.

Israeli, Doron, Charles M. C. Lee, and Suhas A. Sridharan. 2017. "Is There a Dark Side to Exchange Traded Funds? An Information Perspective." *Review of Accounting Studies* 22: 1048-1083.
