from __future__ import annotations

import numpy as np
import pandas as pd

# The short horizon covers roughly one month; the long horizon covers one
# quarter.  These mirror the fragility metrics window so that regressions of
# rolling fragility on forward outcomes use comparable time scales.
_FWD_SHORT = 4    # weeks
_FWD_LONG = 12   # weeks
_MIN_PERIODS_LONG = 8


def _compound_return(arr: np.ndarray) -> float:
    """Compound a sequence of simple returns: prod(1+r) - 1."""
    return float(np.prod(1.0 + arr) - 1.0)


def _max_drawdown(arr: np.ndarray) -> float:
    """Maximum drawdown over arr expressed as a negative fraction."""
    cum = np.cumprod(1.0 + arr)
    running_max = np.maximum.accumulate(cum)
    drawdowns = (cum - running_max) / running_max
    return float(drawdowns.min())


def add_forward_outcomes(
    panel: pd.DataFrame,
    fwd_short: int = _FWD_SHORT,
    fwd_long: int = _FWD_LONG,
    min_periods_long: int = _MIN_PERIODS_LONG,
) -> pd.DataFrame:
    """Append three forward outcome columns to *panel*.

    The logic uses backward rolling windows shifted forward so that the value
    recorded at time t reflects what happens from t+1 onward:

        rolling(k).func() at position t+k  →  shift(-k)  →  available at t

    Columns added
    -------------
    fwd_ret_4w    : compound return over the next 4 weeks (t+1 … t+4)
    fwd_maxdd_12w : max drawdown experienced over the next 12 weeks (<= 0)
    fwd_vol_12w   : return volatility (std) over the next 12 weeks

    The final *fwd_short* / *fwd_long* rows per ETF will be NaN by
    construction — no future data exists for those dates.

    The panel must contain columns *Symbol*, *Date*, and *Return* and should
    be sorted by (Symbol, Date) before calling this function.
    """
    out = panel.copy()

    grp = out.groupby("Symbol", sort=False)["Return"]

    # Compound return over next fwd_short weeks
    out["fwd_ret_4w"] = grp.transform(
        lambda x: (
            x.rolling(fwd_short, min_periods=fwd_short)
            .apply(_compound_return, raw=True)
            .shift(-fwd_short)
        )
    )

    # Max drawdown over next fwd_long weeks
    out["fwd_maxdd_12w"] = grp.transform(
        lambda x: (
            x.rolling(fwd_long, min_periods=min_periods_long)
            .apply(_max_drawdown, raw=True)
            .shift(-fwd_long)
        )
    )

    # Volatility over next fwd_long weeks
    out["fwd_vol_12w"] = grp.transform(
        lambda x: (
            x.rolling(fwd_long, min_periods=min_periods_long)
            .std()
            .shift(-fwd_long)
        )
    )

    return out
