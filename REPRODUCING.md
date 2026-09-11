# Reproduce the Study

Run commands from the repository root. Market inputs must already be local and
match the selected configuration; no command below silently refreshes data.

## 1. Choose an Environment

Use Python 3.12 and a separate virtual environment as appropriate:

```bash
python3.12 -m venv .venv-research
source .venv-research/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` contains all Python dependencies for calculations, reporting,
acquisition, legacy analysis and tests. Installing packages does not fetch market data.
Existing run verification requires the dependency versions in that run's manifest.
Paper builds made before dependency consolidation retain their old source hashes;
verify those against their preserved source layout or create a new build ID.

The locally verified reporting builds use a temporary, isolated dependency directory
because some original environment components are cloud-only. If it still exists,
prefix local reporting commands with `PYTHONPATH=/private/tmp/hedge-report-deps`.
This is a validation workaround, not a durable environment. Package installation
is explicit and separate from market-data reproduction.

## 2. Identify the Inputs

`study_config.json` pins the chain file
`data/processed/options_screen/chains.csv`, unadjusted `data/raw/prices.csv`,
the audit `data/manifests/local-20260904-v2.json`, and the price/action snapshot
identified by `data/manifests/yahoo-actions-through20250131-20260905.json`.

The scientific chain panel contains 80,521 rows, 36 ETFs and 22 quarterly
snapshots. Licensed caches are not committed. Missing local inputs require a
separate, authorized acquisition or transfer; rebuilding does not manufacture
missing coverage. See [methodology](docs/methodology.md) for data conventions.

## 3. Check or Build

**Read-only audit plus active tests:**

```bash
python scripts/reproduce.py
```

Default stages are `audit` and `tests`. No credentials, experiments, legacy
notebooks or figure generation are invoked. `--list` lists stages;
`--dataset-id NAME` selects an existing audit. Exit `2` means unresolved audit
contents; tests still run. Inventory agreement alone is not a complete input audit.

**One-command science, paper and executed notebook:**

```bash
python scripts/reproduce_hedge_paper.py --run-id my-science --build-id my-paper
python scripts/reproduce_hedge_paper.py --build-id my-paper --verify
```

The runner uses pinned `study_config.json`, independently verified scientific results,
and a write-once paper bundle under `results/hedge_paper/<build-id>/`. Open
`missing_hedge_draft.md` or `review/06_hedge_frontiers.html` there. The bundle
also contains 13 CSV views, six figures, metrics and linked manifests.
Jupyter needs local kernel communication; it uses the runner's Python interpreter.

**Reporting only, without re-solving:**

```bash
python scripts/reproduce_hedge_paper.py --run-id study-20260909 \
  --reuse-run --build-id another-paper
```

Both IDs are immutable. If notebook execution fails, partial output is preserved;
use a new build ID with `--reuse-run`. The template only supports the pinned
configuration rather than silently mislabeling another experiment.

**Science only:**

```bash
python scripts/run_hedge_design.py --config study_config.json --run-id my-robust
python scripts/run_hedge_design.py --run-id my-robust --verify
```

Set `"robust_enabled": false` in `study_config.json` for the non-robust experiment;
`true` (the default) includes robust analysis. The paper build requires `true`.
Scientific outputs live in `results/hedge_design/<run-id>/`. Verification checks
inputs, code, dependencies and outputs; fresh IDs reproduce computations.

## 4. Inspect and Test

`notebooks/06_hedge_frontiers.ipynb` reads a saved paper bundle, defaulting to
`legacy-layout-20260909`. Set `HEDGE_PAPER_BUILD` or its build selector to inspect
another. The tracked template and notebook 05 are never executed in place by
the active pipeline. Notebook checks cover saved-output hashes; CLI verification
also checks sources and dependencies.

```bash
python -m pytest tests/hedge_design tests/workflow -q
RUN_THETA_LIVE_TEST=0 RUN_JULIA_AMERICAN=0 RUN_JULIA_BOOTSTRAP=0 \
  python -m pytest tests/ legacy/unified/tests/ -q
```

The full suite needs the legacy dependencies. [Test groups](tests/README.md)
separate active coverage from supporting and archived checks without deleting tests.

## Legacy, Acquisition and Recovery

Legacy analysis remains explicit: `python scripts/reproduce.py --profile legacy --list`.
See [the legacy guide](legacy/unified/README.md) and
[historical recovery instructions](legacy/unified/docs/archive/README.md).
Legacy notebooks can fetch data and execute in place; they are not part of the
new offline paper build. Reference checkpoints are not certified against the
currently incomplete legacy cache.

Price/action acquisition is a separate network operation:
`python scripts/fetch_hedge_market.py --dataset-id NEW_ID --start 2010-01-01 --end 2025-02-01`.
It never replaces an existing snapshot; adopting it requires a reviewed config.

Before the directory cleanup, the 146-file dirty source tree was restored and
hash-verified from `results/preservation/pre-streamline-20260907/`:

```bash
python scripts/preserve_research.py --snapshot-id pre-streamline-20260907 --verify
python scripts/preserve_research.py --snapshot-id pre-streamline-20260907 --restore-to /tmp/NEW_DIRECTORY
```

Old paper builds retain their original source fingerprints, so they are verified
against that restored source layout—not rewritten manifests. Supply the same
pinned inputs/results separately at their recorded paths; the archive contains
source and compact input manifests, not market data. Config consolidation changes
source fingerprints: older scientific runs also require their original source
and config paths, available in the pre-prune preservation snapshot.
Use regular local files for this verification; the paper verifier rejects
symlinked input paths.

## Pruned Historical Artifacts

The current scientific run is `study-20260909`; the relocated-reference paper
build is `legacy-layout-20260909`. Earlier runs
`lqd-paper-20260907` and its comparison reference
`lqd-robust-20260907-v3` and the first accounting baseline
`lqd-accounting-20260905-v2` remain available. Paper bundles retained in place are
`streamlined-20260907` and the original `phase5-20260907` reference.

Superseded runs, failed/redundant paper builds, development-stage notes and the
old PDF/build assets were backed up and removed on 2026-09-08. The complete
deletion inventory and exact contents are in the verified
`results/preservation/pre-prune-20260908/` recovery bundle. Its generated results
are included; raw/processed inputs are not. See [recovery](legacy/unified/docs/archive/README.md).
Copy the local preservation directory to durable storage before discarding this
checkout. The old cloud-only submission folder was intentionally retained.
