# Historical Recovery

Start with the current [methodology](../../../../docs/methodology.md), [results](../../../../docs/results.md)
and [reproduction guide](../../../../REPRODUCING.md), not development-stage reports.

On 2026-09-08, 13 historical Markdown files, the old PDF and its four build assets,
nine superseded scientific runs and three redundant paper builds were removed
from the working tree. All 396 removed files were archived, hash-verified and
restored to a separate directory before deletion. Their exact paths and SHA-256
hashes are recorded in `results/preservation/pre-prune-20260908/manifest.json`.

Post-deletion validation passes 290 tests (three opt-in skips). A temporary paper
build regenerated all 21 canonical artifacts byte-for-byte and executed all eight
notebook code cells without errors, then was removed. The compact proof is
`results/preservation/pre-prune-20260908/prune_verification.json`. The active audit
still returns `2` for the existing incomplete legacy-source inventory; 161 active
tests pass. Caches and Finder metadata were also cleared without touching inputs.

```bash
python scripts/preserve_research.py --snapshot-id pre-prune-20260908 --verify
python scripts/preserve_research.py --snapshot-id pre-prune-20260908 --restore-to /tmp/NEW_RECOVERY_DIRECTORY
```

This recovery bundle contains the pre-deletion source tree **and pruned generated
results**, unlike the older source-only snapshots. It excludes raw/processed
market inputs, credentials and environments. Restore only to a new directory;
older manifests need their original source paths and dependency versions.

The archive and manifest are local and gitignored, not a remote backup. Copy
`results/preservation/` to your own durable backup before discarding the checkout.
Existing source-recovery snapshots remain intact. No commit or history rewrite
was made. The cloud-only `arxiv_submission/` bundle was retained rather than
downloaded or deleted without a content backup.

The original draft, outline and notebook 05 were byte-identical at that checkpoint.
Their exact pre-relocation copies are also in `pre-legacy-consolidation-20260909`. Requirements
were subsequently consolidated into the root `requirements.txt`; the original
dependency files remain recoverable from the snapshots. Active tests, pinned
market inputs, and legacy code still used by
the preserved notebook were not removed. Legacy operating instructions remain in
[the legacy guide](../../README.md); supporting evidence remains in
`../hedge_capacity/` and the earlier recovery record in `../recovery/`.

The remaining legacy files were consolidated under `legacy/unified/` on
2026-09-09, including the cloud-only submission bundle. See the legacy guide for
current locations and the shared-input exceptions. Earlier paths above are historical.
