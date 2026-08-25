"""Notebook reporting helpers for the options analysis."""

import pandas as pd
from IPython.display import display

from src.data.options_universe import BUCKET_ORDER, ticker_bucket


def display_ticker_summary(ticker_summary):
    display(ticker_summary.sort_values("median_liq_score", ascending=False).round(3))


def display_hedge_capacity_table(options_panel):
    op = options_panel.copy()
    op["duration_bucket"] = op["ticker"].map(ticker_bucket)
    hcap_by_ticker = (
        op.dropna(subset=["hedge_capacity_ratio"])
        .groupby("ticker")
        .agg(
            hcap_median=("hedge_capacity_ratio", "median"),
            hcap_mean=("hedge_capacity_ratio", "mean"),
            weight_basis_mode=(
                "weight_basis", lambda s: s.mode().iloc[0] if len(s) else "unknown"
            ),
            snap_dates=("date", "nunique"),
        )
        .reset_index()
    )
    hcap_by_ticker["duration_bucket"] = hcap_by_ticker["ticker"].map(ticker_bucket)
    bucket_order_map = {bucket: i for i, bucket in enumerate(BUCKET_ORDER)}
    hcap_by_ticker = hcap_by_ticker.sort_values(
        ["duration_bucket", "hcap_median"],
        key=lambda s: s.map(bucket_order_map) if s.name == "duration_bucket" else s,
        ascending=[True, False],
    )
    columns = [
        "ticker",
        "duration_bucket",
        "hcap_median",
        "hcap_mean",
        "weight_basis_mode",
        "snap_dates",
    ]
    display(hcap_by_ticker[columns].round(6))
    return hcap_by_ticker


def display_empirical_duration_table(duration_latest):
    latest_print = duration_latest[
        [
            "ticker",
            "duration_bucket",
            "date",
            "realized_rate_duration",
            "realized_rate_duration_raw",
            "duration_r2",
            "duration_nobs",
        ]
    ].copy()
    numeric_cols = latest_print.select_dtypes(include="number").columns
    latest_print[numeric_cols] = latest_print[numeric_cols].round(4)
    display(latest_print)


def display_hedgeability_scores(hedge):
    print(f"Hedgeability scores: {len(hedge)} liquid tickers")
    print(f"  H_dur coverage: {hedge['H_dur'].notna().sum()} / {len(hedge)}")
    display(
        hedge[
            [
                "ticker",
                "H",
                "hedgeability_tercile",
                "fragility_tercile",
                "fragility_hedgeability_group",
                "H_dur",
            ]
        ]
        .sort_values("H", ascending=False)
        .round(4)
    )


def compile_and_display_regressions(
    tbl1, tbl2, tbl2b, tbl3, tbl3b, tbl4, tbl5, tbl6, tbl7
):
    all_specs = {
        "(1) IVRVG -> ret": tbl1,
        "(2) IVRVG x long -> ret": tbl2,
        "(2b) IVRVG + duration -> ret": tbl2b,
        "(3a) H -> ret": tbl3,
        "(3b) H_dur -> ret": tbl3b,
        "(4) IVRVG -> fwd_vol": tbl4,
        "(5) IVRVG/duration -> ret": tbl5,
        "(6) vega/duration -> drawdown": tbl6,
        "(7) H_dur + long -> drawdown": tbl7,
    }
    rows = []
    for name, table in all_specs.items():
        for var in table.index:
            rows.append({"spec": name, "variable": var, **table.loc[var].to_dict()})
    results_df = pd.DataFrame(rows)
    display(results_df.round(4))
    return results_df


def display_robustness_ladder(ladder_df, boot_df=None):
    if boot_df is not None:
        columns = ["spec", "var", "p_wildboot", "n_reps", "seed"]
        ladder = ladder_df.merge(
            boot_df[columns], on=["spec", "var"], how="left"
        )
        print("Wild-cluster bootstrap p-values joined.")
    else:
        ladder = ladder_df
        print("robustness_boot.csv absent - CGM-only ladder.")
    display(ladder.round(4))
