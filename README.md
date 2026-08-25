# Observable Fragility, Limited Hedge Capacity, and Tail Risk in Bond ETFs

One paper built from two linked empirical layers. The broad panel asks whether
publicly observable bond ETF fragility predicts forward tail risk. The
hedge-capacity extension then asks whether listed options provide a practical
risk-transfer channel for that exposure.

- Core panel: **352 ETFs · 518 weeks · August 2016–July 2026 · 159,216 ETF-week observations**
- Option-chain universe: **36 ETFs · 339,220 contracts · 114 monthly snapshots**
- Capacity-covered universe: **33 ETFs · 12,599 ETF-week capacity observations**
- Strict liquid-options universe: **6 ETFs — EDV, EMB, IEF, LQD, TLT, ZROZ**

The nested samples are intentional. Broad fragility claims use all 352 ETFs;
option-market claims are limited to the selected hedge-capacity samples.

---

## Repository Structure

```text
.
├── data/
│   ├── raw/
│   │   ├── prices.csv                    # unadjusted EOD closes (scripts/01)
│   │   ├── options_screen/               # ThetaData chain + IV caches (gitignored)
│   │   └── live/                         # live raw intermediates
│   ├── processed/
│   │   ├── offline/                      # paper's fixed core-panel snapshot (default)
│   │   ├── live/                         # fresh-pull outputs
│   │   └── options_screen/               # chains.csv, options_panel.csv, iv_panel_full.csv (gitignored)
│   └── exports/
│       ├── legacy_csv_exports/           # cached raw outputs from original prototype
│       └── tables/                       # exported result tables
├── notebooks/
│   ├── 02_rolling_risk_metrics.ipynb     # core fragility figures
│   ├── 03_analysis.ipynb                 # macro, fragility, stress, robustness
│   ├── 05_options_analysis.ipynb         # hedge-capacity extension
│   └── archive/                          # retired notebooks
├── docs/
│   ├── draft.md                          # unified paper draft
│   ├── hedge_capacity/                   # extension methodology and evidence notes
│   │   ├── figures/                      # generated (gitignored)
│   │   └── tables/                       # generated (gitignored)
│   ├── data_provenance.md
│   └── methodology_review.md
├── scripts/
│   ├── reproduce.py                      # ★ one-command pipeline (see REPRODUCING.md)
│   ├── 01_download_prices.py             # batch EOD close download (yfinance)
│   ├── 02_fetch_chains.py                # raw chain repull (ThetaData API)
│   ├── 03_concat_screen.py               # screen CSVs from the chain cache
│   ├── 04_build_iv_panel.py              # weekly ATM call/put IV panel
│   ├── 05_build_call_put_iv_diagnostic.py# monthly call/put IV gap table
│   ├── 06_build_options_panel.py         # hedge-capacity panel build
│   ├── 07_robustness_ladder.py           # Spec 0 CGM robustness ladder
│   ├── 08_paper_artifacts.py             # paper tables + figures 24-26
│   └── 09_fragility_h4.py                # fragility H4 clustered-inference reference
├── julia/                                # robustness bootstrap and American pricer
├── src/
│   ├── config.py                         # paths + options quality thresholds (single source of truth)
│   ├── analysis/
│   │   └── regression_utils.py           # CGM (2011) two-way cluster SEs
│   ├── data/
│   │   ├── macro.py, prices.py, risk_free.py, universe.py   # core-panel inputs
│   │   ├── options.py                    # ThetaData chains, IV series, liquidity screen
│   │   ├── options_panel.py              # build_options_panel() steps 2–7
│   │   └── options_universe.py           # 36-ticker universe, buckets, ETF metadata
│   ├── features/
│   │   ├── category.py, forward_outcomes.py, rolling_risk.py,
│   │   ├── stress_index.py, structural.py                    # core fragility features
│   │   ├── rate_space.py                 # dollar-Greeks → rate-space (D_i bridge, DV01)
│   │   ├── hedge_capacity.py             # OI-weighted chain capacity by side (C/P/total)
│   │   ├── call_put_iv.py                # monthly call/put IV diagnostic
│   │   ├── options_features.py           # empirical duration, hedgeability scores
│   │   └── vrp.py                        # IVRVG appendix diagnostics
│   └── pipelines/
│       └── build_core_panel.py           # core panel end-to-end (FRED key required)
└── tests/                                # pytest suite
```

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Credentials

All keys are read from the environment — nothing is hardcoded. Put them in a `.env`
in the repo root (gitignored) or export them in your shell:

```bash
FRED_API_KEY=...            # macro series + risk-free rate (free: fred.stlouisfed.org)
THETADATA_USERNAME=...      # options data only (ThetaData subscription)
THETADATA_PASSWORD=...
```

The committed offline core snapshot and cached options pipeline need no
credentials. Refreshing the core panel needs `FRED_API_KEY`; repulling or
extending options data also needs the two `THETADATA_*` credentials.

---

## Core Fragility Analysis (notebooks 02–03)

### Panel modes

| Mode | Path | Purpose |
|------|------|---------|
| `offline` | `data/processed/offline/` | Paper's fixed 2016–2026 snapshot — never changes |
| `live` | `data/processed/live/` | Fresh pulls from FRED / Yahoo Finance |

Notebooks default to `offline`. To switch, change one line near the top of the notebook and rerun:

```python
PANEL_MODE = 'offline'  # change to 'live' after running the live pipeline
panel = pd.read_csv(config.core_panel_csv(PANEL_MODE), ...)
```

> **BAML credit spread note:** FRED now exposes only a rolling 3-year window for `BAMLC0A0CM`. The live pipeline automatically merges the legacy cached `baml_w.csv` (1997–2026) with the fresh FRED pull.

### Canonical offline snapshot

`data/processed/offline/core_panel.csv` is the committed paper snapshot:
159,216 rows across 352 ETFs. It can be used directly without credentials.

### Refresh the panel (FRED key + internet)

```bash
python -m src.pipelines.build_core_panel                       # writes to live/
python -m src.pipelines.build_core_panel --panel-mode offline  # overwrite the snapshot
```

### Run the analysis

```bash
.venv/bin/python -m nbconvert --to notebook --execute --inplace notebooks/02_rolling_risk_metrics.ipynb
.venv/bin/python -m nbconvert --to notebook --execute --inplace notebooks/03_analysis.ipynb
```

---

## Hedge-Capacity Extension (notebook 05)

One command reproduces every derived artifact from the raw ThetaData caches:

```bash
python scripts/reproduce.py        # ~15-30 min; see REPRODUCING.md for stages,
                                   # requirements, and the checkpoint table
```

**See [REPRODUCING.md](REPRODUCING.md)** — it documents the three data layers
(raw caches → derived CSVs → paper artifacts), which stages need credentials
(only the IV stage needs `FRED_API_KEY`; ThetaData credentials are only for
repulling raw data), and what a successful run looks like.

`notebooks/05_options_analysis.ipynb` is illustrative/analysis only: it reads
prepared data and renders results, requires no credentials, and never fetches
or builds anything. Every artifact has exactly one canonical producer script.

Key design points (details in `docs/hedge_capacity/methodology.md`):

- **ThetaData is strictly serial** — one session per account; concurrent requests are
  rejected with `RESOURCE_EXHAUSTED`. All API calls go through a retry wrapper; do not
  parallelize fetches.
- **Hedge capacity** = chain-level rate DV01 (option OI × per-contract DV01) / fund DV01.
  By the D_i cancellation identity this reduces to `100·S·Σ(|Δ|·OI)/AUM`, so it survives
  noisy empirical-duration estimates.
- **Quality thresholds** live in `src/config.py` (`MAX_REL_SPREAD`, `DTE_MIN/MAX`,
  delta band, dollar-Greek floors) and are held constant across the sample.
- Chain and IV caches live under `data/raw/options_screen/{ticker}/` — delete a
  ticker's files to force a repull.

---

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

129 passing tests cover BSM pricing/IV inversion, screen filters, cache behavior, rate-space
identities, hedge-capacity known values, panel construction, and the CGM regression
utilities. `tests/test_theta_chain.py` is a live ThetaData diagnostic that exits
unless credentials are set.

---

## Key Variables (core panel)

| Variable | Description |
|----------|-------------|
| `vol_12w` | 12-week rolling std of weekly excess returns — primary fragility measure |
| `downside_vol_12w` | Semi-deviation (negative returns only) over 12 weeks |
| `maxdd_12w` | Worst peak-to-trough drawdown over trailing 12 weeks |
| `stress_index` | Equal-weighted z-score composite of Δ ANFCI, Δ credit spreads, Δ MOVE, Δ VIX, Δ SPX realized volatility, Δ DXY, and Δ policy-rate uncertainty |
| `high_stress` | Binary: 1 if `stress_index > 1.0` (19 of 518 weeks; 3.7%) |
| `fwd_maxdd_12w` | Forward 12-week maximum drawdown (outcome variable) |
| `fwd_vol_12w` | Forward 12-week return volatility |
| `fwd_ret_4w` | Forward 4-week compound return |
| `RET_XS` | Weekly excess return over 3-month T-bill (DTB3) |
| `log_assets` | Log AUM in USD millions |
| `ER_clean` | Expense ratio as decimal |
| `age_years` | Fund age since inception in years |

## Key Variables (options panel)

| Variable | Description |
|----------|-------------|
| `hedge_capacity_ratio` | Chain rate-DV01 (OI-weighted) / fund DV01 — primary measure |
| `convexity_capacity_ratio` | Chain rate convexity / fund dollar convexity (scales with D_i²) |
| `median_rate_carry` | Median daily theta cost per unit of rate DV01 (hedge running cost) |
| `realized_rate_duration` | −100 × 52-week rolling beta of returns on `d_DGS10` |
| `iv_30d` | Near-30-day ATM IV — median of quality-filtered call/put sides |
| `call_put_iv_gap` | Put IV − call IV at the common near-ATM strike |
| `H`, `H_dur` | Hedgeability score (z-sum of pass rate, $vega, $gamma) and duration-normalized variant |

---

## Macro Variables

All series aggregated to weekly Friday-close frequency.

| Variable | Source | Series ID |
|----------|--------|-----------|
| `d_BAMLC0A0CM` | FRED | BofA IG Corporate OAS |
| `d_DGS10` | FRED | 10-Year Treasury Yield |
| `d_ANFCI` | FRED | Chicago Fed Adjusted NFCI |
| `d_T10Y2Y` | FRED | 10Y–2Y Term Spread |
| `d_T5YIE` | FRED | 5-Year Breakeven Inflation |
| `d_VIX` | Yahoo Finance | `^VIX` |
| `d_MOVE` | Yahoo Finance | `^MOVE` |
| `GPR_z` | Iacoviello (2022) | GPR Daily Index (z-scored) |
