"""Restructure 03_analysis.ipynb: reorder cells and update section headers."""
import json
from pathlib import Path

NB_PATH = Path(__file__).parent.parent / "notebooks" / "03_analysis.ipynb"

with open(NB_PATH, encoding="utf-8") as f:
    nb = json.load(f)

# Some cells (created before nbformat 4.5) may lack an 'id' field.
# Assign a stable synthetic id based on position for those.
for i, c in enumerate(nb["cells"]):
    if "id" not in c:
        c["id"] = f"cell-{i}"

cells = {c["id"]: c for c in nb["cells"]}

# ── Updated markdown sources ───────────────────────────────────────────────
UPDATED_MARKDOWN = {
    "cell-0": """\
# Fixed-Income ETF Fragility: Macro Stress, Liquidity, and the Cross-Section of Bond ETF Returns

Four testable hypotheses:
- **H1** — Macro shocks drive heterogeneous cross-sectional returns; sensitivity varies systematically across ETF characteristics
- **H2** — Structural characteristics (size, cost, age) explain return variation beyond broad category membership
- **H3** — Backward-looking fragility metrics predict forward downside outcomes (drawdown, volatility) — fragility has predictive validity
- **H4** — The fragility-to-drawdown relationship amplifies during high macro stress regimes; fragile ETFs are disproportionately punished\
""",
    "a2133527": "## Setup",
    "30a837f3": "## 1. Universe Overview",
    "8db44f0b": "## 2. Summary Statistics",
    "13a91dbb": "## 3. Structural Variable Distributions",
    "56752a4c": "## 4. Macro Shock Correlations",
    "3da0436d": "## 5. Stress Index",
    "75d2d5d2": """\
## H1 + H2: Macro Sensitivity & Structural Heterogeneity

**H1**: Macro shocks (credit spreads, rate changes) significantly explain weekly bond ETF returns, with heterogeneous sensitivity across ETF types.
**H2**: Structural characteristics (AUM, expense ratio, age) explain cross-sectional variation beyond broad category membership.

Three progressive specifications isolate the contribution of macro factors (H1), category fixed effects, and structural characteristics (H2). F-tests confirm joint significance of each block.\
""",
    "56edbfbb": """\
### Within-Category Beta Dispersion (H1)

H1 claims heterogeneous macro sensitivity **within** categories, not just between them.
Per-ETF OLS betas on `d_BAMLC0A0CM` test whether dispersion around the category mean is statistically non-zero. Bartlett test checks whether dispersion differs across categories.\
""",
    "cd7d659c": """\
## H3: Fragility Predicts Forward Downside

**H3**: Backward-looking fragility metrics (`vol_12w`, `downside_vol_12w`, `maxdd_12w`) predict forward drawdowns and volatility — fragile ETFs have worse subsequent tail outcomes.

**Panel A** — progressive specs for `vol_12w → fwd_maxdd_12w`. R² increments show structural characteristics explain ~7× more variance than category labels (further H2 evidence).
**Panel B** — full spec across three outcomes; positive `vol_12w` on `fwd_ret_4w` shows no return penalty for fragility — the core risk-mispricing finding.
**Panel C** — robustness across all three fragility metrics.\
""",
    "0eca96fc": "### Decile Sort: Forward Outcomes by Fragility",
    "df659f43": "### Return per Unit of Max Drawdown — Full Sample vs. Stress (H4)",
    "8788c3f4": """\
### Robustness: Two-Way Clustered Standard Errors (CGM 2011)

Forward outcome windows at *t* and *t+1* overlap by 11 of 12 weeks, inducing serial correlation that Symbol-only clustering may understate. Cameron-Gelbach-Miller (2011): **V₂ = V(Symbol) + V(Date) − V(HC1)**.\
""",
    "3d8141e2": """\
### Robustness: Fama-MacBeth Spearman Rank Correlation

Pooled Spearman ignores panel structure and inflates sample size. Instead: compute cross-sectional Spearman ρ between `vol_12w` and `fwd_maxdd_12w` within each week, then t-test whether the mean weekly ρ differs from zero. Degrees of freedom = number of weeks, not ETF-weeks.\
""",
    "c41145cb": """\
## H4: Stress Regime Amplification

**H4**: The fragility-to-drawdown relationship amplifies during high macro stress. Fragile ETFs are disproportionately punished when the composite stress index exceeds one standard deviation.

Four columns: **(1)** additive baseline, **(2)** binary interaction `vol_12w × high_stress`, **(3)** continuous interaction `vol_12w × stress_index`, **(4a/4b)** split-sample coefficient comparison.\
""",
    "ac9716e8": """\
### Stress-Conditional Decile Sort (H4, Non-Parametric)

Same cross-sectional sort on `vol_12w`, restricted to `high_stress == 1` weeks.
Tests whether the D1–D10 drawdown spread widens during stress (H4, non-parametric).\
""",
    "20621abb": """\
### Portfolio Tilt: Exclude Top-Fragility Quartile (H4, Practical)

Does screening out the most fragile 25% of ETFs reduce drawdowns specifically during stressed periods?

- **Naive EW**: equal-weight all non-Other ETFs with valid `vol_12w` each week
- **Tilt EW**: equal-weight only the bottom 75% by `vol_12w` (drop top fragility quartile)

The paired t-test isolates whether the tilt advantage is stress-specific — the direct practical statement of H4.\
""",
}

# Apply updated markdown sources
for cell_id, new_source in UPDATED_MARKDOWN.items():
    if cell_id in cells:
        cells[cell_id]["source"] = new_source

# ── New cell order ─────────────────────────────────────────────────────────
NEW_ORDER = [
    # Setup
    "cell-0", "bc1e9c55", "a2133527", "299ef8f0",
    # Descriptive statistics
    "30a837f3", "ecdf6432",           # universe overview
    "8db44f0b", "b03ca896", "1ea39928",  # summary stats
    "13a91dbb", "b77fa0a3",           # structural distributions (moved up)
    "56752a4c", "3d72dd48",           # macro correlations
    "3da0436d", "82be79b3",           # stress index
    # H1 + H2
    "75d2d5d2", "8231474f", "88c4acd6", "53427df9",  # M1 regressions + heatmap
    "56edbfbb", "4f69bb24",           # within-category dispersion (moved here)
    # H3
    "cd7d659c", "09065d83", "bea880a2",  # M2 panels A/B/C
    "0eca96fc", "9cec7a5c",           # decile sort (full sample)
    "8788c3f4", "91b3e1fc",           # two-way SE (moved here)
    "3d8141e2", "93716f1f",           # spearman (moved here)
    # H4
    "c41145cb", "f167c81e",           # M3 regressions
    "ac9716e8", "ac1edbc9",           # stress-conditional decile (defines decile_stress)
    "df659f43", "38de7cf6",           # calmar: uses decile_summary + decile_stress
    "20621abb", "e3a4df14",           # portfolio tilt
]

missing = [cid for cid in NEW_ORDER if cid not in cells]
if missing:
    print(f"WARNING: missing cell IDs: {missing}")

nb["cells"] = [cells[cid] for cid in NEW_ORDER if cid in cells]

with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"Done. Wrote {len(nb['cells'])} cells to {NB_PATH.name}")
for i, cid in enumerate(NEW_ORDER):
    cell = cells.get(cid, {})
    ctype = cell.get("cell_type", "code")
    preview = "".join(cell.get("source", ""))[:60].replace("\n", " ")
    print(f"  [{i:02d}] {cid:12s} ({ctype:8s}) {preview}")
