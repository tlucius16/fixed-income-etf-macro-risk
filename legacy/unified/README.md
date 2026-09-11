# Legacy Unified-Paper Workflow

The retired workflow lives here: `src/`, `scripts/`, notebooks 01–05, `tests/`,
`julia/`, `docs/`, `arxiv_submission/`, and data used only by that workflow.
Python imports use `legacy.unified.src`, separate from the active `src` package.
Run commands from the repository root:

```bash
python scripts/reproduce.py --profile legacy --list
python scripts/reproduce.py --profile legacy --from ladder --until ladder
RUN_THETA_LIVE_TEST=0 RUN_JULIA_AMERICAN=0 RUN_JULIA_BOOTSTRAP=0 \
  python -m pytest tests/ legacy/unified/tests/ -q
```

## Shared Inputs Are Not Retired

These root paths remain dependencies of the current study or its pinned audit:

- `data/raw/prices.csv`, `data/raw/options_screen/` and `data/raw/hedge_design/`.
- `data/processed/options_screen/`, `data/processed/offline/` and `data/processed/hedge_design/`.
- `data/exports/legacy_csv_exports/{raw_prices,daily_returns}.csv`.
- `data/manifests/`: immutable input identities and provenance.

`src/config.py` here routes legacy code to those shared inputs and to this
folder's retired-only data and outputs. Moving shared files without migrating
and revalidating their manifests would break provenance, not merely tidy paths.
Legacy acquisition stages can overwrite shared inputs and require deliberate
use; cleanup has not fetched data or run those stages.

## Preservation and Limitations

The original dirty source tree, including the exact draft, outline and notebook
05, is preserved in `results/preservation/pre-legacy-consolidation-20260909/`.
The draft and outline move unchanged. Notebook import/bootstrap/path references
are updated without executing cells or changing saved outputs. The snapshot's
`relocations.json` records data/document moves with hashes for local files;
two cloud-only placeholders were renamed in place, not downloaded or content-verified.
No data or research files were deleted, staged or committed by this consolidation.

The snapshot is local, gitignored and not a remote backup. It excludes market
data; keep a separate durable backup. See [historical recovery](docs/archive/README.md)
and the [earlier recovery record](docs/recovery/phase4_recovery.md). Historical
records retain their original paths and hashes; restore their source layout
when verifying old runs.

**Legacy notebook execution is not offline.** Some notebooks use live panels
and contain acquisition cells. Missing inputs, dependencies and older empirical
reproduction gaps remain; passing unit tests does not establish full legacy
reproducibility. Use root `requirements.txt`; no separate requirements folder.
