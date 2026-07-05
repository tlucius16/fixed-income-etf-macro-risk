"""Feature construction for the options paper.

compute_vrp        — re-exported from vrp (moved there for the appendix)
compute_hedgeability_score — H score and tercile assignments per ticker
estimate_rolling_rate_duration — empirical rate-duration proxy from returns
add_rate_duration_to_panel — attaches duration estimates to weekly panel rows
add_duration_exposure_features — option Greek transforms scaled by duration
summarize_duration_exposure — bucket/ticker/date summaries of scaled Greeks
summarize_roll_cost_by_regime — ticker-snap roll-cost regime summaries
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Regime bins/labels and the annualise factor live in vrp.py / config;
# re-exported here so existing imports keep working.
from src.features.vrp import (  # noqa: F401
    _ANNUALISE_FACTOR,
    _REGIME_LABELS,
    _add_rate_regime,
    compute_vrp,
)

_DURATION_EXPOSURE_VALUE_COLS = [
    "realized_rate_duration",
    "dollar_duration",
    "duration_per_vega",
    "gamma_per_duration",
    "theta_per_duration",
]

_DURATION_EXPOSURE_METRIC_COLS = [
    "realized_rate_duration_mean",
    "duration_r2_mean",
    "dollar_duration_median",
    "abs_duration_per_vega_median",
    "abs_duration_per_vega_quality_median",
    "vega_per_100_duration_quality_median",
    "gamma_per_100_duration_quality_median",
    "theta_bp_per_duration_quality_median",
    "contracts",
    "quality_contracts",
    "quality_share",
]


def _zscore(s: pd.Series) -> pd.Series:
    std = s.std(ddof=1)
    return (s - s.mean()) / std if std > 0 else pd.Series(0.0, index=s.index)


def compute_hedgeability_score(
    ticker_summary_df: pd.DataFrame,
    core_panel_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute H score, hedgeability tercile, and fragility tercile per ticker.

    H = z(mean_pass_rate) + z(median_dollar_vega) + z(median_dollar_gamma)

    Fragility tercile is based on mean forward 12-week max drawdown per ticker
    (more negative = more fragile = higher tercile number).
    """
    ts = ticker_summary_df[ticker_summary_df["liquid"] == True].copy()

    ts["H"] = (
        _zscore(ts["mean_pass_rate"])
        + _zscore(ts["median_dollar_vega"])
        + _zscore(ts["median_dollar_gamma"])
    )

    ts["hedgeability_tercile"] = (
        pd.qcut(ts["H"], q=3, labels=[1, 2, 3]).astype(int)
    )

    frag = (
        core_panel_df[core_panel_df["Symbol"].isin(ts["ticker"])]
        .groupby("Symbol")["fwd_maxdd_12w"]
        .mean()
        .rename("mean_fwd_maxdd_12w")
    )
    ts = ts.join(frag, on="ticker")

    ts["fragility_tercile"] = (
        pd.qcut(-ts["mean_fwd_maxdd_12w"], q=3, labels=[1, 2, 3]).astype(int)
    )

    ts["fragility_hedgeability_group"] = (
        "F" + ts["fragility_tercile"].astype(str)
        + "_H" + ts["hedgeability_tercile"].astype(str)
    )

    keep = [
        "ticker", "H", "hedgeability_tercile", "fragility_tercile",
        "fragility_hedgeability_group", "mean_pass_rate",
        "median_dollar_vega", "median_dollar_gamma", "mean_fwd_maxdd_12w",
    ]
    return ts[keep].reset_index(drop=True)


def _resolve_column(df: pd.DataFrame, preferred: str, fallback: str) -> str:
    if preferred in df.columns:
        return preferred
    if fallback in df.columns:
        return fallback
    raise KeyError(f"Missing required column: {preferred!r} or {fallback!r}")


def estimate_rolling_rate_duration(
    core_panel_df: pd.DataFrame,
    *,
    window: int = 52,
    min_obs: int = 40,
    return_col: str = "Return",
    yield_col: str = "d_DGS10",
    spread_col: str | None = None,
    date_col: str = "date",
    ticker_col: str = "ticker",
    yield_unit_scale: float = 100.0,
    duration_clip: tuple[float, float] | None = (-2.0, 35.0),
) -> pd.DataFrame:
    """Estimate trailing empirical rate duration from weekly returns.

    Rolling regression:  Return_it = alpha + beta_rate * d_yield_t + error
    realized_rate_duration = -100 * beta_rate  (positive for long-duration ETFs)

    FRED yield changes are in percentage points, hence the 100x multiplier.
    Each estimate uses only the trailing window ending at date t (no look-ahead).
    """
    if window < 2:
        raise ValueError("window must be at least 2")
    if min_obs < 2:
        raise ValueError("min_obs must be at least 2")
    if min_obs > window:
        raise ValueError("min_obs cannot exceed window")

    date_col   = _resolve_column(core_panel_df, date_col, "Date")
    ticker_col = _resolve_column(core_panel_df, ticker_col, "Symbol")

    factors = [yield_col]
    if spread_col is not None:
        factors.append(spread_col)

    required = [date_col, ticker_col, return_col, *factors]
    missing = [col for col in required if col not in core_panel_df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    work = core_panel_df[required].copy()
    work[date_col] = pd.to_datetime(work[date_col])
    for col in [return_col, *factors]:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.sort_values([ticker_col, date_col])

    rows: list[dict[str, object]] = []
    x_cols = factors
    for ticker, grp in work.groupby(ticker_col, sort=False):
        grp = grp.reset_index(drop=True)
        for end_pos in range(len(grp)):
            start_pos = max(0, end_pos - window + 1)
            sample = grp.iloc[start_pos : end_pos + 1].dropna(
                subset=[return_col, *x_cols]
            )
            if len(sample) < min_obs:
                continue

            y = sample[return_col].to_numpy(dtype=float)
            x = sample[x_cols].to_numpy(dtype=float)
            x = np.column_stack([np.ones(len(sample)), x])
            if np.linalg.matrix_rank(x) < x.shape[1]:
                continue

            beta = np.linalg.lstsq(x, y, rcond=None)[0]
            fitted = x @ beta
            ss_res = float(np.sum((y - fitted) ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            r2 = np.nan if ss_tot <= 0 else 1.0 - ss_res / ss_tot

            rate_beta    = float(beta[1])
            raw_duration = -yield_unit_scale * rate_beta
            row: dict[str, object] = {
                "date": grp.loc[end_pos, date_col],
                "ticker": ticker,
                "rate_beta": rate_beta,
                "realized_rate_duration_raw": raw_duration,
                "duration_nobs": int(len(sample)),
                "duration_r2": r2,
                "duration_yield_col": yield_col,
            }

            if spread_col is not None:
                spread_beta = float(beta[2])
                row["spread_beta"] = spread_beta
                row["realized_spread_duration_raw"] = -yield_unit_scale * spread_beta
                row["duration_spread_col"] = spread_col

            rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    if duration_clip is None:
        out["realized_rate_duration"] = out["realized_rate_duration_raw"]
        if "realized_spread_duration_raw" in out.columns:
            out["realized_spread_duration"] = out["realized_spread_duration_raw"]
    else:
        lower, upper = duration_clip
        out["realized_rate_duration"] = out["realized_rate_duration_raw"].clip(
            lower=lower, upper=upper,
        )
        if "realized_spread_duration_raw" in out.columns:
            out["realized_spread_duration"] = out[
                "realized_spread_duration_raw"
            ].clip(lower=lower, upper=upper)

    return out.sort_values(["ticker", "date"]).reset_index(drop=True)


def _safe_denominator(s: pd.Series) -> pd.Series:
    return s.where(s.abs() > np.finfo(float).eps)


def _latest_prior_by_ticker(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    *,
    left_date_col: str,
    right_date_col: str,
    ticker_col: str,
) -> pd.DataFrame:
    merged_parts: list[pd.DataFrame] = []
    for ticker, left_grp in left_df.groupby(ticker_col, sort=False):
        left = left_grp.sort_values(left_date_col)
        right = (
            right_df[right_df[ticker_col] == ticker]
            .drop(columns=[ticker_col])
            .sort_values(right_date_col)
        )
        if right.empty:
            merged = left.copy()
            for col in right.columns:
                merged[col] = pd.NaT if col == right_date_col else np.nan
        else:
            merged = pd.merge_asof(
                left,
                right,
                left_on=left_date_col,
                right_on=right_date_col,
                direction="backward",
            )
        merged_parts.append(merged)

    return pd.concat(merged_parts, ignore_index=True)


def _duration_quality_mask(
    df: pd.DataFrame,
    *,
    duration_col: str,
    duration_r2_min: float | None,
    min_abs_duration: float | None,
) -> pd.Series:
    mask = df[duration_col].notna()
    if min_abs_duration is not None:
        mask &= df[duration_col].abs() >= min_abs_duration
    if duration_r2_min is not None and "duration_r2" in df.columns:
        mask &= df["duration_r2"] >= duration_r2_min
    return mask


def add_rate_duration_to_panel(
    panel_df: pd.DataFrame,
    duration_df: pd.DataFrame,
    *,
    panel_date_col: str = "date",
    duration_date_col: str = "date",
    ticker_col: str = "ticker",
    duration_col: str = "realized_rate_duration",
    duration_r2_min: float | None = 0.20,
    min_abs_duration: float | None = 1.0,
) -> pd.DataFrame:
    """Attach latest prior empirical duration estimates to a weekly panel.

    If the panel already has ``vrp`` this also adds duration-scaled IVRVG
    variants:

      vrp_per_duration         = vrp / |realized_rate_duration|
      vrp_x_duration           = vrp * realized_rate_duration
      *_quality                = same value only where the duration estimate
                                  passes the R² and absolute-duration guards
    """
    required_panel = [ticker_col, panel_date_col]
    missing_panel = [col for col in required_panel if col not in panel_df.columns]
    if missing_panel:
        raise KeyError(f"Missing required panel columns: {missing_panel}")

    required_duration = [ticker_col, duration_date_col, duration_col]
    missing_duration = [col for col in required_duration if col not in duration_df.columns]
    if missing_duration:
        raise KeyError(f"Missing required duration columns: {missing_duration}")

    panel_work = panel_df.copy()
    panel_work["__panel_order"] = np.arange(len(panel_work))
    panel_work[panel_date_col] = pd.to_datetime(panel_work[panel_date_col])

    duration_meta_cols = [
        col for col in [
            duration_date_col, duration_col,
            "realized_rate_duration_raw", "rate_beta", "duration_nobs",
            "duration_r2", "duration_yield_col", "spread_beta",
            "realized_spread_duration", "realized_spread_duration_raw",
            "duration_spread_col",
        ]
        if col in duration_df.columns
    ]
    duration_work = duration_df[[ticker_col, *duration_meta_cols]].copy()
    duration_work[duration_date_col] = pd.to_datetime(duration_work[duration_date_col])
    duration_work["__duration_estimate_date"] = duration_work[duration_date_col]

    out = _latest_prior_by_ticker(
        panel_work, duration_work,
        left_date_col=panel_date_col,
        right_date_col=duration_date_col,
        ticker_col=ticker_col,
    )
    out = out.sort_values("__panel_order").drop(columns=["__panel_order"])
    if "__duration_estimate_date" in out.columns:
        out = out.rename(columns={"__duration_estimate_date": "duration_estimate_date"})
    elif duration_date_col != panel_date_col and duration_date_col in out.columns:
        out = out.rename(columns={duration_date_col: "duration_estimate_date"})

    out["duration_abs"] = out[duration_col].abs()
    out["duration_quality"] = _duration_quality_mask(
        out, duration_col=duration_col,
        duration_r2_min=duration_r2_min, min_abs_duration=min_abs_duration,
    )

    if "vrp" in out.columns:
        duration_abs = _safe_denominator(out["duration_abs"])
        out["vrp_per_duration"] = out["vrp"] / duration_abs
        out["vrp_x_duration"] = out["vrp"] * out[duration_col]
        out["vrp_per_duration_quality"] = out["vrp_per_duration"].where(out["duration_quality"])
        out["vrp_x_duration_quality"] = out["vrp_x_duration"].where(out["duration_quality"])

    return out.reset_index(drop=True)


def add_duration_exposure_features(
    chains_df: pd.DataFrame,
    duration_df: pd.DataFrame,
    *,
    chain_date_col: str = "snap_date",
    duration_date_col: str = "date",
    ticker_col: str = "ticker",
    duration_col: str = "realized_rate_duration",
    contract_multiplier: float = 100.0,
    duration_r2_min: float | None = 0.20,
    min_abs_duration: float | None = 1.0,
) -> pd.DataFrame:
    """Attach latest prior duration estimates and add duration-scaled Greeks.

    Each contract row receives the latest duration estimate available on or
    before its snapshot date for the same ticker.

        dollar_duration = dollar_delta * realized_rate_duration
    """
    required_chain = [ticker_col, chain_date_col, "dollar_vega", "dollar_gamma", "theta_daily"]
    missing_chain = [col for col in required_chain if col not in chains_df.columns]
    if missing_chain:
        raise KeyError(f"Missing required chain columns: {missing_chain}")

    missing_delta_inputs = [
        col for col in ("delta", "underlying") if col not in chains_df.columns
    ]
    if "dollar_delta" not in chains_df.columns:
        if missing_delta_inputs:
            raise KeyError(
                "chains_df requires dollar_delta or delta plus underlying; "
                f"missing {missing_delta_inputs}"
            )

    required_duration = [ticker_col, duration_date_col, duration_col]
    missing_duration = [col for col in required_duration if col not in duration_df.columns]
    if missing_duration:
        raise KeyError(f"Missing required duration columns: {missing_duration}")

    chain_work = chains_df.copy()
    chain_work["__chain_order"] = np.arange(len(chain_work))
    chain_work[chain_date_col] = pd.to_datetime(chain_work[chain_date_col])
    if "dollar_delta" not in chain_work.columns:
        chain_work["dollar_delta"] = chain_work["delta"] * chain_work["underlying"]
    elif not missing_delta_inputs:
        computed_delta = chain_work["delta"] * chain_work["underlying"]
        chain_work["dollar_delta"] = chain_work["dollar_delta"].fillna(computed_delta)

    duration_meta_cols = [
        col for col in [
            duration_date_col, duration_col,
            "realized_rate_duration_raw", "rate_beta", "duration_nobs",
            "duration_r2", "duration_yield_col", "spread_beta",
            "realized_spread_duration", "realized_spread_duration_raw",
            "duration_spread_col",
        ]
        if col in duration_df.columns
    ]
    duration_work = duration_df[[ticker_col, *duration_meta_cols]].copy()
    duration_work[duration_date_col] = pd.to_datetime(duration_work[duration_date_col])

    out = _latest_prior_by_ticker(
        chain_work, duration_work,
        left_date_col=chain_date_col,
        right_date_col=duration_date_col,
        ticker_col=ticker_col,
    )
    out = out.sort_values("__chain_order").drop(columns=["__chain_order"])
    out = out.rename(columns={duration_date_col: "duration_estimate_date"})

    out["dollar_duration"] = out["dollar_delta"] * out[duration_col]
    out["contract_dollar_delta"] = out["dollar_delta"] * contract_multiplier
    out["contract_dollar_duration"] = out["dollar_duration"] * contract_multiplier

    out["duration_quality"] = _duration_quality_mask(
        out, duration_col=duration_col,
        duration_r2_min=duration_r2_min, min_abs_duration=min_abs_duration,
    )

    duration_abs = _safe_denominator(out["dollar_duration"].abs())
    dollar_vega  = _safe_denominator(out["dollar_vega"])

    out["duration_per_vega"]       = out["dollar_duration"] / dollar_vega
    out["abs_duration_per_vega"]   = out["dollar_duration"].abs() / dollar_vega
    out["vega_per_100_duration"]   = 100.0 * out["dollar_vega"] / duration_abs
    out["gamma_per_duration"]      = out["dollar_gamma"] / duration_abs
    out["gamma_per_100_duration"]  = 100.0 * out["gamma_per_duration"]
    out["theta_per_duration"]      = out["theta_daily"].abs() / duration_abs
    out["theta_bp_per_duration"]   = 10000.0 * out["theta_per_duration"]

    quality_cols = [
        "duration_per_vega", "abs_duration_per_vega", "vega_per_100_duration",
        "gamma_per_duration", "gamma_per_100_duration",
        "theta_per_duration", "theta_bp_per_duration",
    ]
    for col in quality_cols:
        out[f"{col}_quality"] = out[col].where(out["duration_quality"])

    out["duration_obs_age_days"] = (
        out[chain_date_col] - out["duration_estimate_date"]
    ).dt.days

    return out.reset_index(drop=True)


def _duration_exposure_sample(chains_duration_df: pd.DataFrame) -> pd.DataFrame:
    missing = [
        col for col in [
            "ticker", "snap_date", "duration_bucket", "duration_quality",
            *_DURATION_EXPOSURE_VALUE_COLS,
        ]
        if col not in chains_duration_df.columns
    ]
    if missing:
        raise KeyError(f"Missing required duration-exposure columns: {missing}")
    return chains_duration_df.dropna(subset=_DURATION_EXPOSURE_VALUE_COLS).copy()


def _add_quality_share(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["quality_share"] = out["quality_contracts"] / _safe_denominator(out["contracts"])
    return out


def summarize_duration_exposure(
    chains_duration_df: pd.DataFrame,
    *,
    bucket_order: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Summarize duration-scaled option Greeks.

    Returns
    -------
    summary_by_bucket, summary_by_ticker, summary_by_date_bucket,
    summary_by_ticker_date
    """
    sample = _duration_exposure_sample(chains_duration_df)

    bucket_agg = dict(
        realized_rate_duration_mean=("realized_rate_duration", "mean"),
        realized_rate_duration_median=("realized_rate_duration", "median"),
        duration_r2_mean=("duration_r2", "mean"),
        dollar_duration_median=("dollar_duration", "median"),
        abs_duration_per_vega_median=("abs_duration_per_vega", "median"),
        abs_duration_per_vega_quality_median=("abs_duration_per_vega_quality", "median"),
        vega_per_100_duration_quality_median=("vega_per_100_duration_quality", "median"),
        gamma_per_100_duration_quality_median=("gamma_per_100_duration_quality", "median"),
        theta_bp_per_duration_quality_median=("theta_bp_per_duration_quality", "median"),
        duration_obs_age_days_median=("duration_obs_age_days", "median"),
        contracts=("ticker", "size"),
        quality_contracts=("duration_quality", "sum"),
    )
    by_bucket = _add_quality_share(sample.groupby("duration_bucket").agg(**bucket_agg))
    if bucket_order is not None:
        by_bucket = by_bucket.reindex([b for b in bucket_order if b in by_bucket.index])

    ticker_agg = dict(
        duration_bucket=("duration_bucket", "first"),
        realized_rate_duration_mean=("realized_rate_duration", "mean"),
        duration_r2_mean=("duration_r2", "mean"),
        dollar_duration_median=("dollar_duration", "median"),
        abs_duration_per_vega_median=("abs_duration_per_vega", "median"),
        abs_duration_per_vega_quality_median=("abs_duration_per_vega_quality", "median"),
        vega_per_100_duration_quality_median=("vega_per_100_duration_quality", "median"),
        gamma_per_100_duration_quality_median=("gamma_per_100_duration_quality", "median"),
        theta_bp_per_duration_quality_median=("theta_bp_per_duration_quality", "median"),
        contracts=("ticker", "size"),
        quality_contracts=("duration_quality", "sum"),
    )
    by_ticker = _add_quality_share(
        sample.groupby("ticker").agg(**ticker_agg).reset_index()
    )

    date_bucket_agg = dict(
        dollar_duration_median=("dollar_duration", "median"),
        vega_per_100_dur_median=("vega_per_100_duration_quality", "median"),
        contracts=("ticker", "size"),
        quality_contracts=("duration_quality", "sum"),
    )
    by_date_bucket = _add_quality_share(
        sample.groupby(["snap_date", "duration_bucket"]).agg(**date_bucket_agg).reset_index()
    )

    ticker_date_agg = dict(
        duration_bucket=("duration_bucket", "first"),
        realized_rate_duration_mean=("realized_rate_duration", "mean"),
        dollar_duration_median=("dollar_duration", "median"),
        abs_duration_per_vega_quality_median=("abs_duration_per_vega_quality", "median"),
        vega_per_100_duration_quality_median=("vega_per_100_duration_quality", "median"),
        gamma_per_100_duration_quality_median=("gamma_per_100_duration_quality", "median"),
        theta_bp_per_duration_quality_median=("theta_bp_per_duration_quality", "median"),
        contracts=("ticker", "size"),
        quality_contracts=("duration_quality", "sum"),
    )
    by_ticker_date = _add_quality_share(
        sample.groupby(["ticker", "snap_date"]).agg(**ticker_date_agg).reset_index()
    )

    return (
        by_bucket.reset_index(),
        by_ticker.reset_index(drop=True),
        by_date_bucket.reset_index(drop=True),
        by_ticker_date.reset_index(drop=True),
    )


def summarize_roll_cost_by_regime(
    exposure_by_ticker_date_df: pd.DataFrame,
    *,
    bucket_order: list[str] | None = None,
    min_quality_contracts: int = 50,
    min_quality_share: float = 0.25,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Summarize duration-normalized theta cost by rate regime.

    Returns
    -------
    summary_by_regime_bucket, time_series, tradeoff
    """
    theta_col = "theta_bp_per_duration_quality_median"
    vega_col  = "vega_per_100_duration_quality_median"
    required  = [
        "ticker", "snap_date", "duration_bucket",
        theta_col, vega_col, "quality_contracts", "quality_share",
    ]
    missing = [col for col in required if col not in exposure_by_ticker_date_df]
    if missing:
        raise KeyError(f"Missing required roll-cost columns: {missing}")

    panel = _add_rate_regime(
        exposure_by_ticker_date_df[required].copy(), date_col="snap_date",
    )
    quality = (
        panel[theta_col].notna()
        & (panel["quality_contracts"] >= min_quality_contracts)
        & (panel["quality_share"] >= min_quality_share)
    )
    sample = panel.loc[quality].copy()

    group_cols = ["rate_regime", "duration_bucket"]
    summary = (
        sample.groupby(group_cols, observed=True)
        .agg(
            theta_p25=(theta_col, lambda s: s.quantile(0.25)),
            theta_median=(theta_col, "median"),
            theta_p75=(theta_col, lambda s: s.quantile(0.75)),
            vega_per_100_duration_median=(vega_col, "median"),
            ticker_snap_obs=("ticker", "size"),
            tickers=("ticker", "nunique"),
        )
        .reset_index()
    )

    baseline = (
        summary.loc[summary["rate_regime"].astype(str) == "pre_tightening",
                    ["duration_bucket", "theta_median"]]
        .rename(columns={"theta_median": "pre_tightening_theta_median"})
    )
    summary = summary.merge(baseline, on="duration_bucket", how="left")
    summary["theta_change_vs_pre"] = summary["theta_median"] - summary["pre_tightening_theta_median"]
    summary["theta_ratio_vs_pre"] = (
        summary["theta_median"] / _safe_denominator(summary["pre_tightening_theta_median"])
    )

    time_series = (
        sample.groupby(["snap_date", "rate_regime", "duration_bucket"], observed=True)
        .agg(
            theta_median=(theta_col, "median"),
            vega_per_100_duration_median=(vega_col, "median"),
            ticker_snap_obs=("ticker", "size"),
        )
        .reset_index()
    )

    tradeoff = summary[[
        "rate_regime", "duration_bucket", "theta_median",
        "vega_per_100_duration_median", "ticker_snap_obs", "tickers",
    ]].copy()
    tradeoff["theta_cost_per_vega_capacity"] = (
        tradeoff["theta_median"] / _safe_denominator(tradeoff["vega_per_100_duration_median"])
    )

    if bucket_order is not None:
        regime_order   = {label: i for i, label in enumerate(_REGIME_LABELS)}
        bucket_order_map = {bucket: i for i, bucket in enumerate(bucket_order)}
        for frame in (summary, tradeoff):
            frame["__bucket_order"] = frame["duration_bucket"].map(bucket_order_map)
            frame["__regime_order"] = frame["rate_regime"].astype(str).map(regime_order)
            frame.sort_values(["__regime_order", "__bucket_order"], inplace=True)
            frame.drop(columns=["__bucket_order", "__regime_order"], inplace=True)
        time_series["__bucket_order"] = time_series["duration_bucket"].map(bucket_order_map)
        time_series.sort_values(["snap_date", "__bucket_order"], inplace=True)
        time_series.drop(columns=["__bucket_order"], inplace=True)

    return (
        summary.reset_index(drop=True),
        time_series.reset_index(drop=True),
        tradeoff.reset_index(drop=True),
    )


def add_latest_duration_exposure_to_panel(
    panel_df: pd.DataFrame,
    exposure_by_ticker_date_df: pd.DataFrame,
    *,
    panel_date_col: str = "date",
    exposure_date_col: str = "snap_date",
    ticker_col: str = "ticker",
    exposure_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Attach latest prior quarterly duration-exposure metrics to a panel."""
    required_panel = [ticker_col, panel_date_col]
    missing_panel = [col for col in required_panel if col not in panel_df.columns]
    if missing_panel:
        raise KeyError(f"Missing required panel columns: {missing_panel}")

    if exposure_cols is None:
        exposure_cols = [
            col for col in _DURATION_EXPOSURE_METRIC_COLS
            if col in exposure_by_ticker_date_df.columns
        ]

    required_exposure = [ticker_col, exposure_date_col, *exposure_cols]
    missing_exposure = [
        col for col in required_exposure if col not in exposure_by_ticker_date_df.columns
    ]
    if missing_exposure:
        raise KeyError(f"Missing required exposure columns: {missing_exposure}")

    panel_work = panel_df.copy()
    panel_work["__panel_order"] = np.arange(len(panel_work))
    panel_work[panel_date_col] = pd.to_datetime(panel_work[panel_date_col])

    exposure_work = exposure_by_ticker_date_df[required_exposure].copy()
    exposure_work[exposure_date_col] = pd.to_datetime(exposure_work[exposure_date_col])
    exposure_work["__exposure_snap_date"] = exposure_work[exposure_date_col]

    out = _latest_prior_by_ticker(
        panel_work, exposure_work,
        left_date_col=panel_date_col,
        right_date_col=exposure_date_col,
        ticker_col=ticker_col,
    )
    out = out.sort_values("__panel_order").drop(columns=["__panel_order"])
    out = out.rename(columns={"__exposure_snap_date": "exposure_snap_date"})
    return out.reset_index(drop=True)


def add_duration_normalized_hedgeability(
    hedge_df: pd.DataFrame,
    duration_exposure_by_ticker_df: pd.DataFrame,
    *,
    min_quality_contracts: int = 50,
    min_quality_share: float = 0.25,
) -> pd.DataFrame:
    """Add duration-normalized hedgeability score ``H_dur`` per ticker."""
    metric_cols = [
        "vega_per_100_duration_quality_median",
        "gamma_per_100_duration_quality_median",
        "theta_bp_per_duration_quality_median",
        "quality_contracts",
        "quality_share",
    ]
    missing = [
        col for col in ["ticker", *metric_cols]
        if col not in duration_exposure_by_ticker_df.columns
    ]
    if missing:
        raise KeyError(f"Missing required duration summary columns: {missing}")

    keep = ["ticker", *metric_cols]
    out  = hedge_df.merge(
        duration_exposure_by_ticker_df[keep], on="ticker", how="left",
    )

    score_cols = [
        "vega_per_100_duration_quality_median",
        "gamma_per_100_duration_quality_median",
        "theta_bp_per_duration_quality_median",
    ]
    valid = (
        out[["mean_pass_rate", *score_cols]].notna().all(axis=1)
        & (out["quality_contracts"] >= min_quality_contracts)
        & (out["quality_share"] >= min_quality_share)
    )

    out["H_dur"] = np.nan
    base = out.loc[valid, ["mean_pass_rate", *score_cols]].copy()
    if not base.empty:
        out.loc[valid, "H_dur"] = (
            _zscore(base["mean_pass_rate"])
            + _zscore(base["vega_per_100_duration_quality_median"])
            + _zscore(base["gamma_per_100_duration_quality_median"])
            - _zscore(base["theta_bp_per_duration_quality_median"])
        )

    return out
