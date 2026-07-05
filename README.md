# Fixed-Income ETF Macro-Risk Research

Two related working papers built on a shared weekly fixed-income ETF panel:

1. **Macro Stress, Liquidity, and the Cross-Section of Bond ETF Fragility** — do backward-looking fragility signals (rolling volatility, downside vol, max drawdown) predict forward tail outcomes, and is that risk compensated in expected returns?
2. **Hedge Capacity and Rate-Duration Risk in Fixed-Income ETF Options Markets** — how much listed-option depth exists relative to each ETF's rate exposure (DV01-scaled hedge capacity), where does it concentrate, and does it relate to forward drawdowns?

Fragility panel: **347 ETFs · 521 weeks · April 2016 – April 2026 · 156,588 ETF-week observations**
Options panel: **36-ticker options universe · quarterly chain snapshots 2020 Q1 – 2025 Q2 · weekly ATM IV 2020 → present**

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
│   │   ├── offline/                      # fragility paper's fixed snapshot (default)
│   │   ├── live/                         # fresh-pull outputs
│   │   └── options_screen/               # chains.csv, options_panel.csv, iv_panel_full.csv (gitignored)
│   └── exports/
│       ├── legacy_csv_exports/           # cached raw outputs from original prototype
│       └── tables/                       # exported result tables
├── notebooks/
│   ├── 02_rolling_risk_metrics.ipynb     # fragility paper: motivating figures
│   ├── 03_analysis.ipynb                 # fragility paper: full H1–H4 analysis
│   ├── 05_options_analysis.ipynb         # options paper: 10-section analysis
│   └── archive/                          # retired notebooks
├── docs/
│   ├── draft.md                          # fragility paper draft
│   ├── options_paper/                    # options paper: methodology, provenance
│   │   ├── figures/                      # generated (gitignored)
│   │   └── tables/                       # generated (gitignored)
│   ├── data_provenance.md
│   └── methodology_review.md
├── scripts/
│   ├── 01_download_prices.py             # batch EOD close download (yfinance)
│   ├── 03_build_iv_panel.py              # weekly ATM call/put IV panel (ThetaData)
│   ├── 04_build_options_panel.py         # chain repull + hedge-capacity panel build
│   ├── 05_build_call_put_iv_diagnostic.py# quarterly call/put IV gap table
│   └── rebuild_panel_from_legacy.py      # fragility panel rebuild (no API needed)
├── src/
│   ├── config.py                         # paths + options quality thresholds (single source of truth)
│   ├── analysis/
│   │   └── regression_utils.py           # CGM (2011) two-way cluster SEs
│   ├── data/
│   │   ├── macro.py, prices.py, risk_free.py, universe.py   # fragility panel inputs
│   │   ├── options.py                    # ThetaData chains, IV series, liquidity screen
│   │   ├── options_panel.py              # build_options_panel() steps 2–7
│   │   └── options_universe.py           # 36-ticker universe, buckets, ETF metadata
│   ├── features/
│   │   ├── category.py, forward_outcomes.py, rolling_risk.py,
│   │   ├── stress_index.py, structural.py                    # fragility features
│   │   ├── rate_space.py                 # dollar-Greeks → rate-space (D_i bridge, DV01)
│   │   ├── hedge_capacity.py             # OI-weighted chain capacity by side (C/P/total)
│   │   ├── call_put_iv.py                # quarterly call/put IV diagnostic
│   │   ├── options_features.py           # empirical duration, hedgeability scores
│   │   └── vrp.py                        # IVRVG appendix diagnostics
│   └── pipelines/
│       └── build_core_panel.py           # fragility panel end-to-end (FRED key required)
└── tests/                                # pytest suite (146 tests)
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
FRED_API_KEY=...        # fragility macro series + risk-free rate (free: fred.stlouisfed.org)
THETA_USERNAME=...      # options data only (ThetaData subscription)
THETA_PASSWORD=...
```

The fragility paper needs only `FRED_API_KEY` (or no key at all with the legacy rebuild).
The options pipeline needs all three.

---

## Paper 1 — Fragility (notebooks 02–03)

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

### Option 1 — Rebuild from cached legacy files (no API key required)

```bash
python scripts/rebuild_panel_from_legacy.py
```

Output: `data/processed/offline/core_panel.csv` — 156,588 rows, 347 ETFs.

### Option 2 — Full pipeline rebuild (FRED key + internet)

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

## Paper 2 — Options / Hedge Capacity (notebook 05)

Build order (each step is cache-backed and resumable):

```bash
# 1. Unadjusted EOD closes for the universe (underlying prices for IV/screens)
python scripts/01_download_prices.py

# 2. Quarterly option chains (calls+puts with OI) + hedge-capacity panel.
#    --repull hits ThetaData; without it, rebuilds from the cached chains.csv.
python scripts/04_build_options_panel.py --repull

# 3. Weekly ATM 30-day IV panel (combined call/put method; --call-only for legacy series)
python scripts/03_build_iv_panel.py

# 4. Quarterly call/put IV gap diagnostic
python scripts/05_build_call_put_iv_diagnostic.py
```

Then run `notebooks/05_options_analysis.ipynb` top to bottom. The screen cell is
cache-backed (fast when chains are already pulled) and the panel-build cell is
behind a `REBUILD_PANEL = False` flag — flip it after a chain repull.

Key design points (details in `docs/options_paper/methodology.md`):

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

146 tests cover BSM pricing/IV inversion, screen filters, cache behavior, rate-space
identities, hedge-capacity known values, panel construction, and the CGM regression
utilities. `tests/test_theta_chain.py` is a live ThetaData diagnostic that exits
unless credentials are set.

---

## Key Variables (fragility panel)

| Variable | Description |
|----------|-------------|
| `vol_12w` | 12-week rolling std of weekly excess returns — primary fragility measure |
| `downside_vol_12w` | Semi-deviation (negative returns only) over 12 weeks |
| `maxdd_12w` | Worst peak-to-trough drawdown over trailing 12 weeks |
| `stress_index` | Equal-weighted z-score composite of Δ ANFCI, Δ CS, Δ MOVE, Δ VIX |
| `high_stress` | Binary: 1 if `stress_index > 1.0` (~top 4% of weeks in sample) |
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
