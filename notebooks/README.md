# Hedge-Design Notebook

`06_hedge_frontiers.ipynb` is the only active notebook. It inspects hash-checked
saved results; it never fetches inputs, solves hedges or generates paper artifacts.
The default bundle is `legacy-layout-20260909`; select another with `HEDGE_PAPER_BUILD`.

`scripts/reproduce_hedge_paper.py` executes a copy into
`results/hedge_paper/<build-id>/review/`, alongside HTML. The template stays clean.

Notebooks 01–05 now live in [the legacy workflow](../legacy/unified/README.md).
See [reproduction](../REPRODUCING.md) for current commands.
