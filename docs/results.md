# Results and Research Status

The accounting, nominal CVaR, finite-model design and reporting implementations
are complete. **The evidence remains conditional, not submission-ready or an
executable backtest.** Read [methodology](methodology.md) before interpreting the
figures; see [reproduction](../REPRODUCING.md) for exact commands.

## Where to Look

- [Notebook template](../notebooks/06_hedge_frontiers.ipynb): saved-result inspection only.
- [Paper source](missing_hedge_draft.md): a separate migration draft with generated table placeholders.
- `results/hedge_paper/legacy-layout-20260909/`: current-layout tables, six figures,
  resolved paper and `review/06_hedge_frontiers.html`.
- `results/hedge_design/study-20260909/`: underlying immutable scientific run.

Generated results require the pinned local inputs and are not committed. The
original draft and notebook 05 are preserved under `legacy/unified/`, pending reconciliation.

## Main Conditional Findings

The fixed $100 million LQD pilot uses January 2–31, 2025 and 1,239 strictly
predecision joint historical windows. At a 50-bp budget, 90% tail and no OI cap:

| Menu | Method | Historical CVaR, loss bps | Worst-model CVaR, loss bps |
|---|---|---:|---:|
| Direct LQD | Nominal | 511.8 | 811.3 |
| Direct LQD | Robust | 511.8 | 811.3 |
| Treasury substitute | Nominal | 361.4 | 748.6 |
| Treasury substitute | Robust | 386.5 | 739.8 |
| Combined | Nominal | 361.4 | 748.6 |
| Combined | Robust | 408.1 | 735.4 |

The combined robust design sacrifices historical-model protection for a smaller
worst-model loss. This is a model-dependent trade-off, not a free improvement.
The observed direct menu contains ten puts, all with zero recorded OI and
strike/spot ratios 1.132–1.404. It is not moneyness-matched to Treasury options.
Every positive-OI-fraction direct cap therefore prevents a pilot allocation.
The 0.95–1.05 matched-moneyness direct menu is empty, not a synthetic hedge.

On the same 16 subsequent-outcome dates, net-loss summaries are mixed:

| Menu / assumed access | Nominal mean | Robust mean | Nominal worst | Robust worst |
|---|---:|---:|---:|---:|
| Combined, uncapped | -22.5 | -24.1 | 377.7 | 330.8 |
| Treasury, uncapped | -25.5 | -24.1 | 557.1 | 677.2 |
| Combined, 5% OI | -11.2 | -10.6 | 685.2 | 696.8 |
| Treasury, 5% OI | -11.0 | -10.4 | 688.7 | 700.3 |

All entries are bps of initial portfolio value; negative means a gain. Worst
means the maximum in this small sample, not a population bound. These clustered
snapshots do not establish robust superiority or a realized-CVaR estimate. OI
remains an assumed participation constraint, not executable depth.

## Reproducibility and Preservation

The current science-to-paper run reproduces all 47 scientific CSVs byte-for-byte
against `lqd-paper-20260907`; the report only changes its config-switch guidance.
The earlier paper replay reproduced
all 21 tables/figures/draft/metrics artifacts exactly. Config consolidation adds
an explicit robust-analysis switch and changes source fingerprints; older runs
require their original source/config layout. Historical manifests are not
rewritten to conceal source changes. The current run uses root `study_config.json`.

After legacy consolidation, **306 tests pass and three opt-in diagnostics are skipped**.
The audit inventory still matches, with existing incomplete-content/code status
retaining exit `2`. All 13 reporting
tables and six figures are byte-identical to `streamlined-20260907`; metrics and
the generated draft update the run identity and archived-draft location. All eight
notebook code cells execute successfully, and current bundle verification passes.

The pre-cleanup dirty source tree is preserved in
`results/preservation/pre-streamline-20260907/` and was restored/hash-verified.
The earlier `phase5-20260907` paper bundle also verifies against that restored
source layout with the identified local inputs/results supplied separately.
The [recovery guide](../legacy/unified/docs/archive/README.md) explains how to recover historical reports
and superseded result runs removed on 2026-09-08. Their exact contents were
archived and restored/hash-verified first; the local backup is not a remote copy.
The current scientific run, its verified comparison reference, the accounting
baseline, current paper and original paper reference remain in place.

Retired code, notebooks 01–05, tests, documents, Julia and legacy-only data now
live under `legacy/unified/`. Shared audited inputs remain at their pinned root
paths. The pre-move source snapshot and verified relocation inventory are in
`results/preservation/pre-legacy-consolidation-20260909/`; original notebook
outputs and draft/outline contents are preserved. The relocated-reference paper
rebuild matches all 21 previous artifacts except the draft's archived-source path.

## Remaining Work

1. Validate deliverables, quote/OI timestamps, execution assumptions and issuer
   distributions independently.
2. Expand dates and ETF coverage; assess moneyness, data vintage and whole-contract
   sizing without treating OI as market depth.
3. Reconcile the separate paper draft with the preserved original, then finalize
   claims, references and presentation.
4. Establish a durable reporting environment and resolve or explicitly bound the
   incomplete legacy-source audit. Its exit `2` is not a successful full audit.

General distributionally robust optimization, daily trading systems, ML/RL and
market-wide completeness claims are not required next implementation steps.
