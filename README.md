# Fixed-Income ETF Macro-Risk Research

**Macro Stress, Liquidity, and the Cross-Section of Bond ETF Fragility**

This repository supports the empirical analysis underlying the working paper. The core question: do fixed-income ETF fragility signals (rolling volatility, downside vol, max drawdown) predict forward tail outcomes, and is that risk compensated in expected returns?

Four hypotheses drive the analysis:
- **H1** — Macro shocks generate heterogeneous cross-sectional ETF return responses
- **H2** — Structural characteristics (size, cost, age) explain return variation beyond category membership
- **H3** — Backward-looking fragility predicts forward drawdowns but not forward returns (mispricing)
- **H4** — The fragility-to-drawdown relationship amplifies during high macro stress regimes

Panel: **347 ETFs · 521 weeks · April 2016 – April 2026 · 156,588 ETF-week observations**

---

## Repository Structure

```text
.
├── data/
│   ├── raw/                              # etfdb_screener.csv (optional fresh pull)
│   │   └── live/                         # live raw intermediates
│   ├── processed/
│   │   ├── offline/                      # paper's fixed snapshot (default)
│   │   └── live/                         # fresh-pull outputs
│   └── exports/
│       ├── legacy_csv_exports/           # cached raw outputs from original prototype
│       └── tables/                       # exported result tables
├── notebooks/
│   ├── 02_rolling_risk_metrics.ipynb     # motivating fragility figures (paper figures)
│   └── 03_analysis.ipynb                 # full H1–H4 analysis
├── docs/
│   ├── draft.md                          # working paper draft
│   ├── data_provenance.md                # data source and construction notes
│   └── methodology_review.md             # outstanding statistical issues
├── scripts/
│   └── rebuild_panel_from_legacy.py      # panel rebuild from cached files (no API needed)
└── src/
    ├── config.py
    ├── data/
    │   ├── macro.py                      # FRED + Yahoo macro series → weekly panel
    │   ├── prices.py                     # Yahoo Finance ETF prices → weekly returns
    │   ├── risk_free.py                  # FRED DTB3 → weekly RF rate
    │   └── universe.py                   # ETFDB screener → ticker list
    ├── features/
    │   ├── category.py                   # ETFDB category → research bucket mapping
    │   ├── forward_outcomes.py           # fwd_ret_4w, fwd_maxdd_12w, fwd_vol_12w
    │   ├── rolling_risk.py               # vol_12w, downside_vol_12w, maxdd_12w, VaR, ES
    │   ├── stress_index.py               # composite macro stress index + high_stress flag
    │   └── structural.py                 # log_assets, ER_clean, age_years
    └── pipelines/
        └── build_core_panel.py           # end-to-end pipeline (requires FRED API key)
```

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Panel Modes

Processed CSVs live in two separate slots:

| Mode | Path | Purpose |
|------|------|---------|
| `offline` | `data/processed/offline/` | Paper's fixed 2016–2026 snapshot — never changes |
| `live` | `data/processed/live/` | Fresh pulls from FRED / Yahoo Finance |

Notebooks default to `offline`. To switch, change one line near the top of the notebook and rerun — no kernel restart needed:

```python
PANEL_MODE = 'offline'  # change to 'live' after running the live pipeline
panel = pd.read_csv(config.core_panel_csv(PANEL_MODE), ...)
```

> **BAML credit spread note:** FRED now exposes only a rolling 3-year window for `BAMLC0A0CM`. The live pipeline automatically merges the legacy cached `baml_w.csv` (covering 1997–2026) with the fresh FRED pull, so the live panel retains full history.

---

## Generating the Core Panel

There are two ways to build the panel.

### Option 1 — Rebuild from cached legacy files (no API key required)

Uses the pre-downloaded CSVs in `data/exports/legacy_csv_exports/` to reconstruct the full 2016–2026 panel. Writes to `data/processed/offline/`.

```bash
python scripts/rebuild_panel_from_legacy.py
```

| File | Coverage | Contents |
|------|----------|----------|
| `legacy_csv_exports/macro_factors.csv` | 2016–2026 | ANFCI, BAML CS, DGS10, T10Y2Y, T5YIE, MOVE, VIX, GPR + weekly changes |
| `legacy_csv_exports/returns_w_long.csv` | 2002–2026 | Weekly returns for 347 ETFs |
| `legacy_csv_exports/rf_w.csv` | 1954–2026 | Weekly risk-free rate (DTB3) |
| `legacy_csv_exports/database.csv` | — | ETF metadata (name, AUM, ER, inception, category) |

Output: `data/processed/offline/core_panel.csv` — 156,588 rows, 347 ETFs, April 2016 – April 2026.

### Option 2 — Full pipeline rebuild (requires FRED API key + internet)

Downloads fresh data from Yahoo Finance and FRED, then rebuilds the panel from scratch. Writes to `data/processed/live/` by default.

```bash
export FRED_API_KEY="your_key_here"  # Windows: $env:FRED_API_KEY = "your_key_here"
python -m src.pipelines.build_core_panel
```

Optional arguments:
```bash
python -m src.pipelines.build_core_panel --panel-mode live        # default
python -m src.pipelines.build_core_panel --panel-mode offline     # overwrite the paper snapshot
python -m src.pipelines.build_core_panel --min-years 5
python -m src.pipelines.build_core_panel --screener-csv data/raw/etfdb_screener.csv
python -m src.pipelines.build_core_panel --output-dir data/processed/custom
```

The pipeline writes three CSVs to the mode directory:
```
data/processed/<mode>/weekly_returns_long.csv
data/processed/<mode>/macro_factors_weekly.csv
data/processed/<mode>/core_panel.csv
```

> **Note:** If `data/raw/etfdb_screener.csv` is absent, the pipeline falls back to `data/exports/legacy_csv_exports/database.csv` for ETF metadata.

---

## Running the Analysis

With `core_panel.csv` built, execute the notebooks in order:

```bash
# Motivating figures (fragility time series, stress episodes, scatter)
.venv/Scripts/python.exe -m nbconvert --to notebook --execute --inplace notebooks/02_rolling_risk_metrics.ipynb

# Full H1–H4 regression analysis
.venv/Scripts/python.exe -m nbconvert --to notebook --execute --inplace notebooks/03_analysis.ipynb
```

Or open them interactively in VS Code / JupyterLab.

---

## Key Variables

| Variable | Description |
|----------|-------------|
| `vol_12w` | 12-week rolling std of weekly excess returns — primary fragility measure |
| `downside_vol_12w` | Semi-deviation (negative returns only) over 12 weeks |
| `maxdd_12w` | Worst peak-to-trough drawdown over trailing 12 weeks |
| `stress_index` | Equal-weighted z-score composite of Δ ANFCI, Δ CS, Δ MOVE, Δ VIX |
| `high_stress` | Binary: 1 if `stress_index > 1.0` (~top 4% of weeks in sample) |
| `fwd_maxdd_12w` | Forward 12-week maximum drawdown (outcome variable, H3/H4) |
| `fwd_vol_12w` | Forward 12-week return volatility |
| `fwd_ret_4w` | Forward 4-week compound return |
| `RET_XS` | Weekly excess return over 3-month T-bill (DTB3) |
| `log_assets` | Log AUM in USD millions |
| `ER_clean` | Expense ratio as decimal |
| `age_years` | Fund age since inception in years |

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
