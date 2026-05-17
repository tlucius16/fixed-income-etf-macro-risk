from __future__ import annotations

import pandas as pd

# The four components capture orthogonal dimensions of macro-financial stress:
#   d_ANFCI       — tightening financial conditions (broader than spreads)
#   d_BAMLC0A0CM  — widening IG credit spreads
#   d_MOVE        — rising bond market volatility
#   d_VIX         — rising equity implied volatility / risk aversion
# All four increase during stress episodes, so the composite is a simple
# equal-weighted average of their z-scores.  Full-sample standardisation is
# appropriate for a retrospective research panel.
_COMPONENTS = ["d_ANFCI", "d_BAMLC0A0CM", "d_MOVE", "d_VIX"]

# A stress_index z-score above this threshold flags the week as a high-stress
# regime.  1.0 corresponds roughly to the top ~16 % of weeks historically.
_HIGH_STRESS_THRESHOLD = 1.0


def add_expanding_stress_index(
    panel: pd.DataFrame,
    min_periods: int = 52,
) -> pd.DataFrame:
    """Add *stress_index_exp* and *high_stress_exp* using an expanding-window z-score.

    Unlike :func:`add_stress_index`, standardisation at each week t uses only
    the mean and std of weeks strictly before t (via a one-period shift).  This
    eliminates the lookahead bias present in the full-sample version and makes
    the signal valid for predictive framing.

    The flag is undefined (NaN / 0) for the first *min_periods* weeks while the
    expanding window accumulates enough history.

    Columns added
    -------------
    stress_index_exp : expanding-window z-score composite
    high_stress_exp  : 1 if stress_index_exp > 1.0, else 0
    """
    macro_weekly = (
        panel[["Date"] + _COMPONENTS]
        .drop_duplicates("Date")
        .set_index("Date")
        .sort_index()
    )

    # Expanding mean and std through t-1 (shift(1) removes current-period lookahead)
    exp_mean = macro_weekly[_COMPONENTS].expanding(min_periods=min_periods).mean().shift(1)
    exp_std  = macro_weekly[_COMPONENTS].expanding(min_periods=min_periods).std(ddof=1).shift(1)

    z_exp = (macro_weekly[_COMPONENTS] - exp_mean) / exp_std
    z_exp["stress_index_exp"] = z_exp[_COMPONENTS].mean(axis=1)
    z_exp["high_stress_exp"] = (z_exp["stress_index_exp"] > _HIGH_STRESS_THRESHOLD).astype(int)

    stress_exp = z_exp[["stress_index_exp", "high_stress_exp"]].reset_index()

    return panel.merge(stress_exp, on="Date", how="left")


def add_stress_index(panel: pd.DataFrame) -> pd.DataFrame:
    """Add *stress_index* and *high_stress* columns to *panel*.

    The stress index is computed at the weekly level (one value per date,
    shared across all ETFs in that week) and then merged back by date.

    Columns added
    -------------
    stress_index : equal-weighted z-score composite of the four macro-change
                   components; higher = more stressed
    high_stress  : 1 if stress_index > 1.0 (top ~16 % of weeks), else 0
    """
    # Extract one observation per week — macro columns are identical across
    # all ETFs within a given date
    macro_weekly = (
        panel[["Date"] + _COMPONENTS]
        .drop_duplicates("Date")
        .set_index("Date")
        .sort_index()
    )

    # Z-score each component over the full sample
    z = (macro_weekly - macro_weekly.mean()) / macro_weekly.std(ddof=1)

    z["stress_index"] = z[_COMPONENTS].mean(axis=1)
    z["high_stress"] = (z["stress_index"] > _HIGH_STRESS_THRESHOLD).astype(int)

    stress = z[["stress_index", "high_stress"]].reset_index()

    return panel.merge(stress, on="Date", how="left")
