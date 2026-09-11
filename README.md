# The Missing Hedge

How much downside protection can listed bond-ETF options provide for a fixed
portfolio, at a stated cost and under explicit access assumptions?

This repository implements cash-flow accounting, nominal and finite-model CVaR
hedge design, and reproducible comparisons of direct LQD puts with TLT/IEF
substitutes. **Results are conditional research—not executable capacity or
demonstrated hedge performance.**

## Start Here

1. [Results and remaining work](docs/results.md) — what the evidence supports.
2. [Methodology](docs/methodology.md) — inputs, accounting and validation rules.
3. [Reproduce the study](REPRODUCING.md) — setup and commands.

For a guided inspection, open [the hedge-design notebook](notebooks/06_hedge_frontiers.ipynb).
It reads saved results; it never fetches data or solves hedges. The
[paper source](docs/missing_hedge_draft.md) is a separate migration draft.

## Run

After installing the appropriate environment and obtaining the pinned local inputs:

```bash
python scripts/reproduce.py
python scripts/reproduce_hedge_paper.py --run-id my-science --build-id my-paper
```

The first command verifies the input audit and runs active tests. An incomplete
legacy-source audit returns `2`, even when tests pass. The second explicitly
generates science, tables, six figures, the paper and an executed notebook/HTML.
Neither refreshes data or overwrites existing runs.

All study settings live in `study_config.json`. Set `robust_enabled` to `false`
for nominal-only analysis with `scripts/run_hedge_design.py`; the full paper
build requires `true` (the default).

## Repository Map

| Location | Purpose |
|---|---|
| `study_config.json` | Versioned assumptions and pinned input identities |
| `src/hedge_design/` | Accounting, scenarios, optimizers and evaluation |
| `src/reporting/hedge_design.py` | Saved-result tables and figures |
| `scripts/` | Active audit, experiment, preservation and paper commands |
| `notebooks/` | Active hedge-design result inspection |
| `tests/hedge_design/`, `tests/workflow/` | Active scientific and workflow tests |
| `requirements.txt` | All Python dependencies |
| `data/`, `results/` | Local inputs and generated, provenance-checked outputs |
| `legacy/` | Retired code, notebooks, tests, documents, Julia and legacy-only data |

Only the active hedge-design implementation remains in `src/`. The old draft,
outline and notebooks 01–05 are under `legacy/unified/`. Historical inputs still
used by the current study or audit stay in `data/`; old does not mean unused.
See [legacy boundaries and recovery](legacy/unified/README.md).

Contract deliverables, quote/OI timing and independent distribution validation
remain unresolved. OI is not executable depth, and sparse snapshots do not
establish performance.
