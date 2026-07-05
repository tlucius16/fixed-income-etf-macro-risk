# Expanding the IV Pilot: Greek-Based Research Angles

## Core Reframing

The IV pilot suggests that implied volatility levels add little incremental predictive power for future fixed-income ETF drawdowns once realized volatility and ticker fixed effects are included.

Rather than treating this as a dead end, the stronger expansion is:

> Fixed-income ETF fragility is not only about which funds are risky, but whether that risk is hedgeable through listed option markets.

The Greek transforms can support a shift from return prediction to hedgeability, convexity access, and option-market quality.

---

## Angle 1: Hedgeability Gap

### Research Question

Are the most fragile fixed-income ETFs also the ETFs with usable listed-option markets?

### Motivation

Some ETFs may exhibit high realized volatility, downside volatility, or drawdown risk, but lack liquid options with meaningful convexity exposure. This creates a hedgeability gap.

### Candidate Variables

Fragility:

- `vol_12w`
- `downside_vol_12w`
- `maxdd_12w`
- `fwd_maxdd_12w`

Option-market hedgeability:

- `pass_rate`
- `passing_contracts`
- `median_dollar_vega`
- `median_dollar_gamma`
- `median_theta_vega`

### Empirical Output

- Hedgeability by ETF category
- Fragility by hedgeability decile
- High-fragility / low-hedgeability ETF list

---

## Angle 2: Cost of Convexity

### Research Question

How expensive is option convexity across fixed-income ETF option markets?

### Motivation

IV alone is a blunt measure. Greek transforms give a better view of whether options provide useful convexity at reasonable carry cost.

### Useful Measures

```text
dollar_gamma = local convexity payoff for a 1% underlying move
dollar_vega  = exposure to a 1 vol-point repricing
theta_vega   = daily carry cost per unit of vega
gamma_vega   = convexity intensity per unit of vega
```

A useful composite:

```text
convexity_quality = z(median_dollar_gamma)
                  + z(median_dollar_vega)
                  - z(median_theta_vega)
```

### Empirical Output

- Cheap vs expensive convexity ETFs
- Convexity quality by category
- Convexity cost during high-stress vs low-stress periods

---

## Angle 3: Greek-Based Liquidity Screen

### Research Question

Can option liquidity be measured more economically using Greeks rather than raw contract counts?

### Motivation

A contract may exist, but still be useless for hedging if it has too little vega, too little gamma, or excessive theta cost.

The current screen classifies contracts by whether they provide meaningful exposure:

- Minimum `dollar_vega`
- Minimum `dollar_gamma`
- Maximum `theta_vega`

### Contribution

This creates a Greek-based measure of option-market usability:

> An ETF option market is liquid if it offers tradable units of volatility and convexity exposure, not merely if contracts are listed.

---

## Angle 4: Fragility x Hedgeability Sorts

### Research Question

Which ETFs combine high fragility with weak hedgeability?

### Proposed Classification

Create two indicators:

```text
high_fragility = vol_12w or maxdd_12w in top tercile
high_hedgeability = hedgeability_score in top tercile
```

Then form four groups:

| Group | Interpretation |
|---|---|
| High fragility / High hedgeability | Risky but hedgeable |
| High fragility / Low hedgeability | Risky and hard to hedge |
| Low fragility / High hedgeability | Defensive and hedgeable |
| Low fragility / Low hedgeability | Low-risk but thin option market |

The most interesting group is:

> High fragility / Low hedgeability

This group may represent fixed-income ETF risk that is difficult to insure through listed options.

---

## Angle 5: Stress-State Option Market Quality

### Research Question

Do fixed-income ETF option markets become more or less hedgeable during macro stress?

### Motivation

The need for convexity is highest during stress, but option-market quality may deteriorate exactly when hedges are most valuable.

### Tests

Compare high-stress vs low-stress periods:

- `pass_rate`
- `median_dollar_vega`
- `median_dollar_gamma`
- `median_theta_vega`
- `median_iv`

### Possible Finding

Even if IV does not predict drawdowns strongly, Greek transforms may show that the cost or availability of convexity changes materially across stress regimes.

---

## Angle 6: IV Result as a Negative Finding

### Current Interpretation

The IV subsumption test suggests:

- IV has weak standalone predictive power.
- IV adds almost no incremental `R^2` beyond realized volatility.
- Under two-way clustered standard errors, neither IV nor realized volatility is robust in the joint model.

### Paper Framing

This can be framed as a useful negative result:

> Implied volatility levels do not materially subsume realized fragility in predicting future fixed-income ETF drawdowns.

Then the paper pivots:

> However, option Greek transforms reveal substantial cross-sectional variation in whether fixed-income ETF risks are hedgeable through listed options.

---

## Candidate Tables

### Table 1: Option Coverage by ETF Category

Show number of ETFs, liquid-option count, mean pass rate, median dollar gamma, and median theta-vega by category.

### Table 2: Fragility by Hedgeability Decile

Sort ETFs into hedgeability deciles and compare realized volatility, downside volatility, and future drawdowns.

### Table 3: Convexity Cost Across Categories

Compare median dollar gamma, dollar vega, theta-vega, and gamma-vega across Treasury, credit, high yield, municipal, aggregate bond, and inflation-linked ETFs.

### Table 4: Stress vs Non-Stress Greek Metrics

Compare option-market quality during high and low macro stress regimes.

### Table 5: High-Fragility / Low-Hedgeability ETFs

List ETFs with high realized fragility but weak option-market hedgeability.

---

## Proposed One-Sentence Contribution

This extension shows that fixed-income ETF fragility is not only a question of return predictability, but also of hedgeability: while implied volatility levels add little predictive power for future drawdowns, Greek-transformed option-chain measures reveal which bond ETF risks can actually be hedged through listed options.
