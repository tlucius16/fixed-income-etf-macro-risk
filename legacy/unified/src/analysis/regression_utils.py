"""CGM two-way cluster SE and summary table helpers."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.iolib.summary2 import summary_col


def twoway_cluster_se(
    formula: str,
    data: pd.DataFrame,
    col1: str,
    col2: str,
) -> tuple:
    """CGM (2011) two-way cluster SE: V = V(col1) + V(col2) - V(HC1).

    Returns (result, se_2way, V_psd).
      result   — statsmodels RegressionResultsWrapper fitted on col1 clusters
      se_2way  — np.ndarray of CGM standard errors (same order as result.params)
      V_psd    — PSD-projected covariance matrix
    """
    work = data.dropna(subset=[col1, col2]).reset_index(drop=True)
    model = smf.ols(formula, data=work, missing="drop")
    # Patsy/statsmodels may drop additional rows for missing formula variables.
    # Cluster arrays must match that exact estimation sample.
    used_rows = np.asarray(model.data.row_labels, dtype=int)
    groups1 = work.loc[used_rows, col1].to_numpy()
    groups2 = work.loc[used_rows, col2].to_numpy()
    r_c1  = model.fit(cov_type="cluster", cov_kwds={"groups": groups1})
    r_c2  = model.fit(cov_type="cluster", cov_kwds={"groups": groups2})
    r_hc1 = model.fit(cov_type="HC1")
    V = (
        r_c1.cov_params().values
        + r_c2.cov_params().values
        - r_hc1.cov_params().values
    )
    eigvals, eigvecs = np.linalg.eigh(V)
    V_psd = eigvecs @ np.diag(np.maximum(eigvals, 0)) @ eigvecs.T
    se_2way = np.sqrt(np.diag(V_psd))
    return r_c1, se_2way, V_psd


def cgm_summary(
    formula: str,
    data: pd.DataFrame,
    regressors: list[str],
) -> pd.DataFrame:
    """Run a regression with CGM two-way SE (ticker × date) and return a tidy table.

    Columns: coef, se_cgm, t_cgm, p_cgm (two-tailed normal approximation).
    """
    from scipy import stats as scipy_stats

    result, se_2way, _ = twoway_cluster_se(formula, data, "ticker", "date")
    idx = pd.Index(result.params.index)
    se_series = pd.Series(se_2way, index=idx)

    params = result.params[regressors]
    se     = se_series[regressors]
    t_stat = params / se
    p_val  = 2 * (1 - scipy_stats.norm.cdf(np.abs(t_stat)))

    return pd.DataFrame(
        {"coef": params, "se_cgm": se, "t_cgm": t_stat, "p_cgm": p_val}
    )
