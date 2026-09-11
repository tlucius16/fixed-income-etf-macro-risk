# Paper Restructure Outline

Working note, 2026-08-28. How to rebuild `docs/draft.md` given: (a) no realistic
access to a 2016–2026 daily NAV / premium-discount panel, (b) a practitioner-journal
target (JFI / JPM / FAJ), (c) the honest problem that the unified draft's headline
signal reduces to realized volatility.

---

## Diagnosis

The unified paper (`draft.md`, commit `85e536f`) stapled two things together:

1. **Fragility half** — trailing 12-week realized vol predicts forward drawdown / vol
   but not forward return. This is a competent application of known results: volatility
   clustering, the bond low-risk anomaly (Chung–Wang–Wu 2019; Bai–Bali–Wen 2019),
   and volatility-managed portfolios (Moreira–Muir 2017; Cederburg et al. 2020). The
   draft's own §7.5 concedes most of the signal is time-varying duration exposure
   (rate-beta × MOVE knocks the coefficient to t = −1.68). As a *headline contribution*
   this does not clear a bar.

2. **Hedge-capacity half** — the standalone "Missing Hedge Market" analysis, now
   compressed into §6 and `docs/hedge_capacity/extension_notes.md`. This is the part
   with a genuine, checked-for-duplicates novel measurement: bond-ETF listed-option
   open interest translated into hedge capacity relative to fund rate exposure.

The merge made #1 the frame and #2 the extension. It should be the other way around —
and #1 should shrink to a one-section motivation, where realized vol is a perfectly
acceptable "the risk is visible ex ante" stylized fact.

**Move: un-merge. Promote the standalone options paper back to the deliverable, adapt
for a practitioner journal, add two new analyses that need no external data, and cut
the fragility material down to Section 2.**

The full standalone text already exists in `docs/hedge_capacity/extension_notes.md`
(retired title: *The Missing Hedge Market: Listed Option Capacity in Fixed-Income
ETFs*). This outline is that paper, re-scoped.

---

## Target and framing

| | |
|---|---|
| **Primary venue** | *Journal of Fixed Income* — market-structure measurement is its wheelhouse |
| **Secondary** | *Journal of Portfolio Management* (risk-management angle), *FAJ* (higher bar) |
| **Working title** | *The Missing Hedge: Listed Option Capacity for Fixed-Income ETFs* |
| **One-line thesis** | Bond-ETF tail risk is broadly observable; the only exchange-listed instrument that could transfer it — options on the funds — has capacity concentrated in one Treasury fund, is structurally call-sided because of option-income ETF flow, and leaves credit and liquidity risk unhedged. |
| **What a practitioner journal rewards here** | A clean measurement + a usable takeaway for sizing hedges. It does *not* demand a novel causal mechanism or a large-N result, which is why the null regressions are survivable if framed as "the naive result fails twice." |

---

## Section-by-section

Legend for data status:
`[HAVE]` fully in hand · `[BUILD]` small new analysis, in-hand inputs · `[OPT]` optional, needs light hand-collection

### 1. Introduction  `[HAVE]`

- Bond ETFs hold trillions in duration and credit exposure; stress fragility is
  documented (cite March 2020 discount blowout — BIS Aramonte–Schrimpf–Shin; the ETF
  arbitrage literature — Pan & Zeng, Todorov, Shim & Todorov; Koont–Ma–Pástor–Zeng).
- Instrument landscape: for exposure to the ETF *price*, listed options on the fund
  are the only exchange-traded, limited-loss, basis-specific hedge. Futures hedge
  rates not the basis; swaptions are OTC and rate-only; CDX needs ISDA and hedges
  spread only. **If bond-ETF tail risk is insurable on-exchange, it is insurable here.**
- Question prior to any pricing/prediction question: *does this market have the
  capacity to do that job?* Unanswered because nobody has put option Greeks into the
  units of the underlying bond exposure for this market.
- Four findings preview: (i) risk is observable ex ante; (ii) listed capacity is
  negligible outside TLT; (iii) the book is call-sided and traceable to option-income
  ETFs; (iv) the one available hedge (TLT puts) neutralizes the rate leg of a credit
  ETF and leaves the credit/liquidity leg — the part that drives tail events — exposed.
- Source: rewrite of `extension_notes.md` §1 + instrument paragraph from `draft.md` intro.

### 2. Observable risk: fragility as motivation  `[HAVE]`

Compress the entire current fragility paper to ~1.5 pages.

- One measure: `vol_12w`. State plainly it is realized return instability, not a
  structural fragility estimate.
- One result: the decile sort. D1 fwd 12w max drawdown −0.22% vs D10 −4.75%; flat
  forward return across deciles. One table, one figure (`docs/figures/fragility_deciles.png`).
- One robustness sentence + footnote pointer: holds under downside-vol and trailing-DD
  variants, two-way clustering, the 183-fund full-history subsample; a substantial
  component is time-varying duration exposure (§7.5 of the old draft) — which is fine,
  because the point here is only *"the risk is visible before the drawdown,"* not that
  it is a mispricing.
- Optional: one line on the stress-period portfolio tilt (screening the top vol
  quartile cuts stress-window drawdown ~468bp) as evidence the risk is *avoidable*
  ex ante — which sharpens the "so why can't you hedge it?" turn into Section 3+.
- Sources: `notebooks/02`, `notebooks/03`, `data/exports/tables/offline/{decile_summary,decile_stress,port}.csv`.
- **Cut from here:** M1 macro-sensitivity regression (Table 5), Bartlett test, the
  full stress-index construction, Fama–MacBeth section, expanding-window stress check,
  duration-beta ladder. These belong to the old framing.

### 3. Data and measurement  `[HAVE]`

- Option chains: monthly snapshots, 36 bond ETFs, 2016–2026, ~339k call+put
  contract-obs with per-contract OI, ThetaData. Weekly combined call/put ATM 30d IV
  panel for the informational tests.
- Quality screen (unchanged, pre-specified): rel. spread ≤ 0.35, DTE ∈ [14, 90],
  |Δ| ∈ [0.10, 0.90], dollar-Greek floors. State it makes every capacity number an
  upper bound (full OI usable, no price impact, EOD quotes).
- Liquidity classification: the √-notional screener family. Eight funds pass.
- Empirical rate duration: negated slope of weekly returns on Δ10y; quality gate
  (R² ≥ 0.20, |D| ≥ 1.0); validates at ρ = 0.98 vs published effective durations.
- American-exercise robustness: 751-step CRR repricing → ≈ zero median IV bias; one
  footnote (`tables/american_bias.csv`).
- Sources: `extension_notes.md` §2, `notebooks/05` §§2–5, `src/features/rate_space.py`.
- **Refresh before submission:** `ETF_METADATA` AUM / durations from current fact
  sheets; rotate FRED + ThetaData credentials.

### 4. The capacity accounting — a market that mostly is not there  `[HAVE]` (core)

The center of the paper. Descriptive, point-estimate — **needs no significance stars.**

- Rate-space translation and the DV01 cancellation identity:
  `HCR = 100·S·Σ(|Δ|·OI) / AUM`. Emphasize duration cancels from the headline ratio.
- Fund-by-fund put-side accounting at a representative recent snapshot (2025-04-01),
  with cross-snapshot min/median/max columns showing the shape is stable.
- TLT: put book ≈ $2.93M DV01/bp ≈ 3.5% of the fund's own DV01; at 5–10% OI
  participation ≈ $100–200M hedgeable vs a ~$50B+ fund.
- Everything else: IEF / TIP retail-scale; LQD / AGG / BND / EMB ≈ zero quality
  put DV01; JNK ($10B HY fund) entire put book hedges ~$15k. The categories with the
  weakest instrument substitutes (credit, aggregate) have no listed capacity at all.
- Table: `tables/capacity_accounting.csv`. Figure: `figures/24_missing_market.png`
  (hedgeable position vs fund AUM, log-log, with %-of-fund reference diagonals).
- Sources: `extension_notes.md` §4, `notebooks/05` §11.

### 5. Anatomy of the book — and the option-income ETF footprint  `[BUILD]` (core, novel positive result)

The current draft has the call-sided observation (TLT 2.6:1, MBB ~100:1). **New work:
tie it to the specific funds creating it.**

- Compile the option-income / buy-write bond-ETF set and its growth: TLTW (iShares
  20+ Year Treasury Buywrite, 2022), Amplify TLTP, and the 2023–25 crop of
  Treasury/credit option-income ETFs. AUM history and each fund's prospectus roll
  rule (typically sell ~1-month ATM calls monthly) are public — fact sheets,
  prospectuses, `stockanalysis.com` / issuer sites. No data vendor.
- Overlay: for TLT (and any other underlier with a wrapper), plot standing call OI by
  strike and expiry against wrapper AUM and roll dates. The prediction: call OI
  concentrates at ~1-month tenor, near-ATM, and steps with wrapper AUM. If it lines
  up, you have attributed the call-sidedness to a nameable, growing flow — a positive,
  novel, topical finding, not just "the book is skewed."
- Keep the LQD put-side evaporation paragraph (liquid on the 2020–25 median, zero
  quality put DV01 by 2025-04-01): depth on average ≠ depth when needed.
- Caveat stated plainly: composition inferred from standing-book skew, not signed
  volume; OI is a stock.
- Table/fig: `tables/call_put_dv01_ratio.csv`, `figures/25_call_put_ratio.png`, plus
  a new wrapper-AUM-vs-call-OI figure.
- New inputs: wrapper fund list + AUM series (public); existing `chains.csv`.

### 6. What the one available hedge actually does — TLT-put basis risk  `[BUILD]` (core, new constructive result)

Replaces the pure null with something a desk can use. **All inputs in the core panel.**

- Setup: an investor holds LQD / HYG / EMB / AGG and can only buy listed puts on TLT
  (the sole liquid venue). How much protection does a TLT-put overlay actually deliver?
- Step 1 — hedge ratio: regress each credit/agg ETF's weekly excess return on TLT's
  weekly excess return (full sample and stress-only). Report β, R², and the residual.
- Step 2 — residual decomposition: regress the residual on the macro factors already
  in the panel (Δcredit spread, Δterm spread / curve, Δbreakevens). Quantify how much
  of each credit ETF's variance the TLT hedge *cannot* touch.
- Step 3 — tail check: construct the drawdown of a TLT-put-overlaid LQD/HYG position
  through March 2020 and the 2022 cycle using realized TLT option payoffs (or a
  Black-Scholes proxy on TLT IV from the panel). Show the overlay removes the rate
  drawdown and leaves the credit/liquidity drawdown roughly intact.
- Takeaway sentence for the abstract: "A listed TLT-put overlay hedges ~X% of an
  investment-grade bond ETF's variance and essentially none of its stress-period
  drawdown, because the tail is a spread/liquidity event the rate hedge does not span."
- Sources: core panel (`data/exports/legacy_csv_exports/excess_returns.csv`,
  `macro_factors.csv`), TLT IV from the weekly IV panel. New notebook section.

### 7. Informational nulls — prices and capacity predict nothing  `[HAVE]`

Short. Frame as corroboration, not failed hypotheses.

- IV–realized variance gap (IVRVG): predicts neither fwd 12w max drawdown, fwd 4w
  return, nor fwd realized vol, in any specification.
- Within-fund capacity change: no predictive content (Mundlak within +0.065,
  bootstrap p ≈ 0.72). Fresh-only and snapshot-week subsamples likewise null.
- One paragraph: a market this shallow and this one-sided has neither the depth to
  aggregate risk information nor a participant base positioned to trade on it.
- Caveat: 114 monthly snapshots, limited within-fund power — "no detectable signal,"
  not proven zero.
- Sources: `extension_notes.md` §6, `notebooks/05` §§8–9.

### 8. The between-fund association — why the naive regression fails twice  `[HAVE]`

Compress the current §7 "autopsy" to ~1 page + an appendix table.

- The naive spec (fwd drawdown on capacity, date FE) gives β ≈ −0.34, CGM p < 0.001
  — wrong sign for protection, and a researcher would run it first.
- Act 1, identification: entirely between-fund. Ticker FE kills it; duration-bucket FE
  kills it; Mundlak between −0.507 / within −0.046. Mechanism: option depth sits on
  long-duration Treasury funds; those drew down hardest in 2022; the pooled regression
  reads composition as a capacity effect.
- Act 2, inference: with ~33 funds (≈8 with meaningful capacity) the unit is the fund,
  not the fund-week. Wild-cluster bootstrap (Rademacher, 9,999 reps, ticker clusters):
  pooled p → 0.095, between p → 0.116. The CGM stars were a 33-cluster problem treated
  as an 8,600-observation one.
- The one survivor: call-side capacity (bootstrap p ≈ 0.03), put-side null throughout
  — which is the option-income-ETF signature from Section 5, not a hedging channel.
- Table: `tables/robustness_spec0.csv` ⋈ `tables/robustness_boot.csv`.

### 9. Conclusion  `[HAVE]`

- Measured properly, the exchange-listed hedge for bond ETFs barely exists; the depth
  that exists is yield-enhancement flow; the one usable hedge spans rate risk but not
  the spread/liquidity risk that drives tail events.
- Three implications: (i) risk managers should not build sizing on listed-option
  overlays for credit/aggregate exposure — that market is not there; (ii) the fragility
  literature's stress-transmission channels operate in a market where the nominal
  tail-risk-transfer mechanism is absent — a missing shock absorber; (iii) empirical
  practice: decompose cross-sectional market-development associations before
  interpreting, and inference at the level of the cross-sectional unit.
- Limitations: one-plus rate cycle; monthly snapshots; EOD quotes; OI as stock;
  capacity as optimistic upper bound; no OTC visibility.

### Appendix  `[HAVE]`

IV combined-method validation; duration-scaled Greek / hedgeability scores; convexity
capacity and roll cost by regime; winsorized / log capacity; drop-dominant-funds;
American CRR repricing detail; the fragility robustness battery (pointer to old draft
+ `fragility_h4_reference.csv`).

### Optional: stress-episode premium/discount mini-case  `[OPT]`

If time permits and only if it strengthens Section 6: hand-collect daily NAV for ~6
funds (LQD, HYG, TLT, AGG, EMB, MUB) across March 2020, Oct 2022, March 2023 from
the Wayback Machine's snapshots of issuer fund pages or the Rule 6c-11 quarterly
premium/discount tables. One figure: P/D blows out exactly when `vol_12w` fires and
when listed puts do not exist. Not load-bearing — the mechanism is citable without it.

---

## New analysis checklist (all inputs in hand or public, no vendor)

1. **Option-income ETF footprint (§5).** Build wrapper list + monthly AUM series
   (public fact sheets / issuer sites). Overlay wrapper AUM and roll dates on TLT call
   OI by strike/expiry from `chains.csv`. New figure + short table.
2. **TLT-put basis-risk decomposition (§6).** Hedge-ratio regressions of
   LQD/HYG/EMB/AGG excess returns on TLT; residual variance decomposition on existing
   macro factors; overlaid-position drawdown through 2020 / 2022. New notebook section.
3. **Metadata refresh.** `src/data/options_universe.py` `ETF_METADATA` AUM + durations
   from current fact sheets, with dated sources.
4. **Credential rotation.** FRED + ThetaData keys (already on the submission checklist).
5. **(Optional) Stress-episode P/D mini-case.** ~6 funds × 3 windows, hand-collected.

## What to cut from `draft.md`

- §4.2 / §5.1 macro-sensitivity model M1, Table 5, Bartlett test.
- §2.6 / §3.4 full stress-index construction (keep a 2-sentence version only if the
  portfolio-tilt line is retained in Section 2).
- §7.2 Fama–MacBeth, §7.4 expanding-window stress, §7.5 duration-beta ladder
  (compress §7.5 to one sentence + footnote in Section 2).
- The "four hypotheses H1–H5" scaffolding — a practitioner paper does not need it.
- Abstract and title rewritten around the hedge-capacity thesis.

## Reused-material map

| New section | Pull from |
|---|---|
| 1. Introduction | `hedge_capacity/extension_notes.md` §1; `draft.md` intro instrument paragraph |
| 2. Observable risk | `draft.md` §5.2 + §5.3 (compressed); `notebooks/02`, `03`; `figures/fragility_deciles.png` |
| 3. Data & measurement | `extension_notes.md` §2; `notebooks/05` §§2–5 |
| 4. Capacity accounting | `extension_notes.md` §4; `notebooks/05` §11; `tables/capacity_accounting.csv` |
| 5. Book anatomy + wrapper footprint | `extension_notes.md` §5 + **new wrapper analysis** |
| 6. TLT-put basis risk | **new** — core panel + IV panel |
| 7. Informational nulls | `extension_notes.md` §6; `notebooks/05` §§8–9 |
| 8. Between-fund autopsy | `draft.md` §6.3 / `extension_notes.md` §7; `tables/robustness_*.csv` |
| 9. Conclusion | `extension_notes.md` §8 |
| Appendix | `draft.md` §7; `hedge_capacity/*` |

---

## Honest risks

- Sections 4–5 and 7–8 are, net, a null result on ~33 funds. A referee can still
  bounce it. Mitigations: (a) Sections 5 (wrapper footprint) and 6 (basis
  decomposition) are *positive, constructive* results that anchor the paper; (b) the
  practitioner framing ("do not size hedges against a market that isn't there") is a
  real contribution independent of statistical significance; (c) the DV01 methodology
  is a reusable artifact.
- If Section 5's wrapper-to-OI overlay does *not* line up cleanly, keep the call-sided
  observation as-is (it is still true and still evidence) and drop the attribution
  claim to a hypothesis in the conclusion.
- Sample is one-plus rate cycle. Own it in the limitations; frame findings as
  "as of 2016–2026," not timeless.
