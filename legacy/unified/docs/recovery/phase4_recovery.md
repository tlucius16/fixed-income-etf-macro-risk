# Phase 4 Recovery and Preservation Record

The pre-cleanup dirty source tree was saved as `pre-phase4-20260907` and restored
into a fresh temporary directory. All **127 source files** matched their recorded
SHA-256 hashes after restoration. This is a verified local source recovery path,
not certified recovery of the historical empirical results.

[Machine-readable record](phase4_recovery.json) contains the snapshot archive
and manifest hashes, base Git revision, installed distribution directory versions,
protected-file hashes, and old-to-new mappings. The local snapshot includes code,
notebooks, configuration, source documentation, small data manifests, requirements
and Julia project/manifest files. It excludes credentials, raw/processed market
data, generated figures, result directories and the virtual environment.

## Recover the Exact Pre-Cleanup Source

From the current repository root:

```bash
.venv/bin/python scripts/preserve_research.py --snapshot-id pre-phase4-20260907 --verify
.venv/bin/python scripts/preserve_research.py --snapshot-id pre-phase4-20260907 --restore-to /tmp/my-pre-cleanup-source
```

The restore target must not exist. Verification checks archive membership and
every file hash; extraction rejects traversal paths and never overwrites a target.
The archive and manifest live under
`results/preservation/pre-phase4-20260907/`, which is gitignored. Preserve both
files in your own backup before discarding this checkout. Neither the uncommitted
working tree nor the local ZIP is automatically available on GitHub. No branch,
commit, stash, or Git-history rewrite was made by the cleanup.

## Data and Environment Recovery Are Separate

- Audit reference: `data/manifests/local-20260904-v2.json`, restored with the source.
  It identifies available input hashes and cloud-only source gaps. Its 80,521-row,
  22-snapshot local chain panel does not verify the older 339,220-row reference.
- The fixed hedge-design inputs and price/action manifest remain in place. The
  already generated nominal/robust runs and their manifests were not modified.
- Raw caches, offline/live panels, daily prices, exports, and generated legacy
  tables are not in the source ZIP. Restore them separately under the same paths
  after obtaining the required licensed/local inputs; do not synthesize gaps or
  refresh providers merely to make recovery appear to pass.
- Python is 3.12.1 on macOS ARM64 in the observed environment. Package versions
  come from installed `.dist-info` directory names to avoid hydrating unavailable
  metadata. This is an environment inventory, not a tested clean-install lock or
  proof of intact package contents. Julia's exact project/manifest are in the ZIP.
- `requirements.txt` remains byte-identical to the pre-cleanup file.
  `requirements-active.txt` declares only NumPy, pandas, SciPy and pytest;
  `requirements-acquisition.txt` adds yfinance explicitly.
  `requirements-legacy.txt` retains the old requirements and declares notebook
  03's previously missing scikit-learn/patsy imports. No packages were installed
  or removed, and no network-dependent notebook or Julia diagnostics were run.

## User-Edited Material: Reconciliation Decision

`docs/draft.md`, `notebooks/05_options_analysis.ipynb`, and
`docs/paper_restructure_outline.md` retain their original contents and paths.
Their hashes are pinned in the recovery record. The draft's author/contact and
narrative edits and notebook 05's existing edits were not folded into a generated
replacement, reverted, or archived away. The old unified-paper identity and
output references are retained as legacy context, not promoted as Phase 3 claims.
Phase 5 should create the new draft separately and reconcile these edits
deliberately. Notebook 05 retains its supporting descriptive producers and
imports; those dependencies therefore remain installed/available to legacy users.

## Disposition Decisions

- Scripts 07/09 and notebooks 01–03 moved to `legacy/unified/`. Only root/path
  bootstrap and invocation references changed, not statistical logic or outputs.
- IV-versus-realized-volatility tests moved with the legacy scope. The forward
  label test was extracted from mixed feature tests; structural/category tests stay.
- `src/features/forward_outcomes.py` remains because the legacy core-panel builder
  imports it. `options_features.py`, `vrp.py`, regression utilities and notebook
  reporting remain because notebook 05 and retained panels still consume them.
  They are not dependencies of `src/hedge_design/`; a transitive boundary test
  guards the active scientific package and its input-loader/package initializers.
- No useful shared duration/scenario routine needed extraction: active accounting,
  scenarios and benchmarks already reside in `src/hedge_design/`; descriptive
  exposure helpers remain with their supporting consumers.
- No generated artifact was certified obsolete. Prior runs remain valid evidence,
  and legacy tables/figures still have draft/notebook consumers. They were retained,
  along with caches, rather than purged merely because they are gitignored.

The code/layout cleanup can proceed without claiming that missing historical
data, a fresh legacy environment, or publication-grade execution validation are
resolved. Those limitations remain explicit gates, not reasons to delete evidence.

## Validation

- Full supported suite: **267 passed, 3 opt-in live/Julia diagnostics skipped**.
- Restored pre-cleanup source: **129 focused tests passed** from its own temporary
  root using the existing interpreter; no real datasets were copied into that root.
- Current default profile: **138 tests passed**; exit `2` remains the existing
  incomplete-source audit result, with matching input inventory.
- Active and legacy stage listings and all archived entry-point paths were checked.
- Existing `lqd-robust-20260907-v3` run still verifies without changing its source,
  config, input, dependency or output hashes. Verification also succeeds when
  acquisition/legacy imports are deliberately blocked.
- Protected draft, notebook 05, outline and original requirements hashes match.
  All archived notebook outputs and metadata match the pre-cleanup snapshot;
  only root/path-bootstrap source cells changed.
- `git diff --check` passes. No actual historical regression/notebook execution
  is claimed; missing sources, optional network cells and the legacy environment
  gaps remain documented rather than bypassed.
