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
| **Paper artifacts** (tables, figures, robustness ladders) | `docs/options_paper/{tables,figures}/` | no | stages `ladder`…`notebook` |

**The raw caches are the source of truth.** Given them, every downstream file
regenerates deterministically. Never delete them to "start fresh" — that
converts a 15-minute reproduction into a multi-hour ThetaData repull whose IVs
drift by ~±0.1 vol pt (the trailing dividend yield depends on the price window
fetched, so refetched inputs are not bit-identical).

## Requirements

- Python venv: `pip install -r requirements.txt`
- Julia ≥ 1.12 (optional — the `jl-*` stages are skipped with a warning if
  absent; the repo reproduces fully without them minus the bootstrap and
  American-bias tables). First run: deps auto-resolve from the pinned
  `julia/Manifest.toml`.
- Credentials, via environment or a `.env` in the repo root (gitignored):
  - `FRED_API_KEY` — required by the `iv` stage only.
  - `THETA_USERNAME` / `THETA_PASSWORD` — **not** required for reproduction
    from caches; only for repulling raw data or extending the IV panel past
    the cached end date.

## Pipeline stages

| Stage | Command (run individually if preferred) | Produces |
|---|---|---|
| screen | `scripts/02_concat_screen.py` | chains.csv, summary.csv, ticker_summary.csv (√-notional liquidity gate) |
| iv | `scripts/03_build_iv_panel.py --end 2026-07-02` | iv_panel_full.csv (cache-backed; pinned end date ⇒ no API calls) |
| cp-diag | `scripts/05_build_call_put_iv_diagnostic.py` | call_put_iv_diagnostic.csv |
| panel | `scripts/04_build_options_panel.py` | options_panel.csv |
| ladder | `scripts/06_robustness_ladder.py` | robustness_spec0.csv, side_capacity.csv |
| artifacts | `scripts/07_paper_artifacts.py` | capacity accounting, call/put ratio, duration validation, universe tables; figures 24–26 |
| jl-parity | `julia --project=julia julia/scripts/parity_check.jl` | gate: Julia vs Python quant layer on all 80,521 contracts |
| jl-boot | `julia .../robustness_boot.jl` | robustness_boot.csv (wild-cluster bootstrap, seeded) |
| jl-amer | `julia -t auto .../american_bias.jl` | american_bias.csv (CRR American repricing) |
| notebook | `jupyter nbconvert --execute notebooks/05_options_analysis.ipynb` | remaining figures/tables; **credential-free** — the notebook only reads prepared data |
| tests | `pytest tests/ -q` | 152 passed (Julia/live-API tests opt-in via `RUN_JULIA_*`, `RUN_THETA_*`) |

Notebook 05 is illustrative/analysis only: it never fetches or builds data.
Every artifact has exactly one canonical producer, listed above.

## What success looks like

`reproduce.py` verifies these automatically:

| Checkpoint | Value |
|---|---|
| chains.csv rows | 80,521 |
| liquid tickers (√-notional gate) | 8 — TLT, LQD, IEF, EMB, TIP, EDV, ZROZ, VCLT |
| options_panel.csv rows | 18,058 |
| Spec 0 baseline coefficient | −0.2682 (CGM p 0.0036; wild-bootstrap p 0.25) |
| jl-parity | `PARITY OK` (Greeks ≤1e-13, IV ≤6e-7 vs Python) |

## Repulling raw data (authors / subscribers only)

```bash
# chains (quarterly, C+P with OI) — hours; ThetaData is strictly serial
python scripts/04_build_options_panel.py --repull
# weekly IV — extend past the cached end date
python scripts/03_build_iv_panel.py
```

ThetaData allows one session per account and rejects concurrent requests
(`RESOURCE_EXHAUSTED`); do not parallelize. If a repull is interrupted, delete
any *empty* `*_chain.json` files it left behind before rerunning — they are
cache poison (they read as "no data" forever after).
