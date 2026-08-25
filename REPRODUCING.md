# Reproducing this repository

Everything derived in this repo is produced by **one command**:

```bash
python scripts/reproduce.py
```

That runs the full pipeline in dependency order, prints per-stage status, and
ends with a checkpoint table that must match the reference values below.
`python scripts/reproduce.py --list` shows the stages; `--from` / `--until` /
`--skip-julia` / `--skip-notebook` subset them.

## The three data layers

| Layer | Location | In git? | How you get it |
|---|---|---|---|
| **Raw caches** (ThetaData chains + IV quotes, one JSON per ticker/date) | `data/raw/options_screen/` | no (license-encumbered) | from the authors, or repull with a ThetaData subscription (see below) |
| **Derived data** (chains.csv, IV panel, options panel, side capacity) | `data/processed/options_screen/` | no | `scripts/reproduce.py` stages `screen`…`panel` |
| **Paper artifacts** (tables, figures, sample funnel, robustness ladders) | `docs/hedge_capacity/{tables,figures}/` | no | stages `ladder`…`hedge-nb` |

**The raw caches are the source of truth.** Given them, every downstream file
regenerates deterministically. Never delete them to "start fresh" — that
converts a 15-minute reproduction into a multi-hour ThetaData repull whose IVs
drift by ~±0.1 vol pt (the trailing dividend yield depends on the price window
fetched, so refetched inputs are not bit-identical).

## Requirements

- Python venv: `pip install -r requirements.txt`
- Julia ≥ 1.12 (optional — the `jl-*` stages are skipped with a warning if
  absent; the repo reproduces fully without the robustness-bootstrap and
  American-bias tables). First run: deps auto-resolve from the pinned
  `julia/Manifest.toml`.
- Credentials, via environment or a `.env` in the repo root (gitignored):
  - `FRED_API_KEY` — required by the `iv` stage only.
  - `THETADATA_USERNAME` / `THETADATA_PASSWORD` — **not** required for reproduction
    from caches; only for repulling raw data or extending the IV panel past
    the cached end date.

## Pipeline stages

| Stage | Command (run individually if preferred) | Produces |
|---|---|---|
| fetch | `scripts/02_fetch_chains.py` | (Optional) raw ThetaData JSON caches (requires ThetaData credentials) |
| screen | `scripts/03_concat_screen.py` | chains.csv, summary.csv, ticker_summary.csv (√-notional liquidity gate) |
| iv | `scripts/04_build_iv_panel.py --end 2026-07-17` | iv_panel_full.csv (cache-backed; pinned end date ⇒ no ThetaData calls) |
| cp-diag | `scripts/05_build_call_put_iv_diagnostic.py` | call_put_iv_diagnostic.csv |
| panel | `scripts/06_build_options_panel.py` | options_panel.csv |
| ladder | `scripts/07_robustness_ladder.py` | robustness_spec0.csv, side_capacity.csv |
| artifacts | `scripts/08_paper_artifacts.py` | sample funnel, capacity accounting, call/put ratio, duration validation, universe tables; core fragility figure and hedge-capacity figures 24–26 |
| h4-ref | `scripts/09_fragility_h4.py` | fragility H4 reference (Symbol/Date/CGM SEs) |
| jl-boot | `julia .../robustness_boot.jl` | robustness_boot.csv (wild-cluster bootstrap, seeded) |
| jl-amer | `julia -t auto .../american_bias.jl` | american_bias.csv (CRR American repricing) |
| core-nb | `jupyter nbconvert --execute notebooks/02_rolling_risk_metrics.ipynb notebooks/03_analysis.ipynb` | core fragility, stress, and robustness outputs; **credential-free** |
| hedge-nb | `jupyter nbconvert --execute notebooks/05_options_analysis.ipynb` | hedge-capacity figures/tables; **credential-free** — the notebook only reads prepared data |
| tests | `pytest tests/ -q` | 129 passed, 3 skipped (opt-in Julia/live-API diagnostics) |

The notebooks are illustrative/analysis only: they never fetch or build data.
Every artifact has exactly one canonical producer, listed above.

## Build the unified paper

Run the `artifacts` stage first so the generated fragility figure is present,
then build the tracked PDF from `docs/draft.md`:

```powershell
powershell -ExecutionPolicy Bypass -File docs/build_draft_pdf.ps1
```

On a TeX-equipped Unix system, use `bash docs/build_draft_pdf.sh`. The Windows
builder uses Pandoc and headless Microsoft Edge; the Unix builder uses Pandoc
and XeLaTeX. Both write `docs/draft.pdf`.

## What success looks like

`reproduce.py` verifies these automatically:

| Checkpoint | Value |
|---|---|
| chains.csv rows | 339,220 |
| liquid tickers (√-notional gate) | 6 — EDV, EMB, IEF, LQD, TLT, ZROZ |
| sample-funnel ETF counts | 352 → 36 → 33 → 6 |
| options_panel.csv rows | 18,056 |
| Spec 0 baseline coefficient | −0.3377 (CGM p 0.0004) |
| Spec 0 wild-bootstrap p-value | 0.0953 (9,999 ticker-cluster replications) |

### Reproducibility philosophy: pinned inputs, not pinned pull dates

Reproduction means *the committed/cached inputs plus the code yield identical
outputs* — it does not mean a fresh API pull today returns the same data
(FRED revises series such as ANFCI; Yahoo lookback windows depend on the run
date; FRED's BAMLC0A0CM now exposes only a rolling 3-year window, which is
why the repo carries a full-history hybrid). The fixed inputs are the committed
offline core panel, the cached S&P daily closes, and the ThetaData chain/IV
caches. The canonical offline snapshot contains 159,216 rows from 2016-08-19
through 2026-07-17. The live pipeline (`src/pipelines/build_core_panel.py`)
exists for fresh pulls and will legitimately differ by data vintage and window
boundaries.

## Repulling raw data (authors / subscribers only)

```bash
# chains (monthly business-start snapshots from 2016, C+P with OI); strictly serial
python scripts/02_fetch_chains.py
# weekly IV — extend past the cached end date
python scripts/04_build_iv_panel.py
```

ThetaData allows one session per account and rejects concurrent requests
(`RESOURCE_EXHAUSTED`); do not parallelize. If a repull is interrupted, delete
any *empty* `*_chain.json` files it left behind before rerunning — they are
cache poison (they read as "no data" forever after).
