from __future__ import annotations

import numpy as np
import pandas as pd

# All metrics use a 12-week backward-looking rolling window with a minimum of
# 8 non-NaN observations so that early history still produces estimates once
# the ETF has 8 weeks of data, and stabilises at the full 12-week window.
_DEFAULT_WINDOW = 12
_DEFAULT_MIN_PERIODS = 8


# ---------------------------------------------------------------------------
# Scalar helpers applied via rolling().apply(raw=True)
# ---------------------------------------------------------------------------

def _downside_std(arr: np.ndarray) -> float:
    """Std of returns strictly below zero (semi-deviation, threshold = 0).

    Returns NaN when fewer than three negative observations are present in the
    window — an std on one or two points is not meaningful.
    """
    neg = arr[arr < 0.0]
    if len(neg) < 3:
        return np.nan
    return float(np.std(neg, ddof=1))


def _max_drawdown(arr: np.ndarray) -> float:
    """Maximum drawdown over the window expressed as a negative fraction.

    A window of [+2%, -5%, +1%] has a drawdown of roughly -5% from the peak
    reached after the first week.  The return value is <= 0.
    """
    cum = np.cumprod(1.0 + arr)
    running_max = np.maximum.accumulate(cum)
    drawdowns = (cum - running_max) / running_max
    return float(drawdowns.min())


def _es_90(arr: np.ndarray) -> float:
    """Expected Shortfall at the 90 % confidence level.

    Average of all returns at or below the 10th percentile of the window.
    Returned as a negative number (it is a loss).
    """
    threshold = np.nanpercentile(arr, 10)
    tail = arr[arr <= threshold]
    if len(tail) == 0:
        return np.nan
    return float(np.mean(tail))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_rolling_risk_metrics(
    panel: pd.DataFrame,
    window: int = _DEFAULT_WINDOW,
    min_periods: int = _DEFAULT_MIN_PERIODS,
) -> pd.DataFrame:
    """Append five 12-week backward-looking fragility metrics to *panel*.

    Columns added
    -------------
    vol_12w          : annualised-comparable rolling std of Return
    downside_vol_12w : std of negative returns in the window (semi-deviation)
    maxdd_12w        : worst cumulative drawdown in the window (<= 0)
    var_12w_90       : 10th-percentile return in the window (90 % hist. VaR)
    es_12w_90        : mean return below the 10th percentile (90 % hist. ES)

    The panel must contain columns *Symbol*, *Date*, and *Return* and should
    be sorted by (Symbol, Date) before calling this function.
    """
    out = panel.copy()

    grp = out.groupby("Symbol", sort=False)["Return"]

    out["vol_12w"] = grp.transform(
        lambda x: x.rolling(window, min_periods=min_periods).std()
    )

    out["var_12w_90"] = grp.transform(
        lambda x: x.rolling(window, min_periods=min_periods).quantile(0.10)
    )

    out["downside_vol_12w"] = grp.transform(
        lambda x: x.rolling(window, min_periods=min_periods).apply(
            _downside_std, raw=True
        )
    )

    out["maxdd_12w"] = grp.transform(
        lambda x: x.rolling(window, min_periods=min_periods).apply(
            _max_drawdown, raw=True
        )
    )

    out["es_12w_90"] = grp.transform(
        lambda x: x.rolling(window, min_periods=min_periods).apply(
            _es_90, raw=True
        )
    )

    return out
