"""Synthetic pull-partition fixtures; no credentials, vendor data, or network required."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.data import build_chain_panel as build


def write_manifest(root, tickers, dates):
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({"plan": {"tickers": tickers, "dates": dates}}))


def write_partition(root, ticker, snap_date, *, strikes=(100.0, 101.0), spot=105.0,
                    include_oi=True, include_greeks=True, liquid=True):
    directory = root / ticker / snap_date
    directory.mkdir(parents=True)
    n = len(strikes)
    eod = pd.DataFrame({"symbol": [ticker] * n, "expiration": ["2025-02-01"] * n,
                        "strike": list(strikes), "right": (["PUT", "CALL"] * n)[:n],
                        "bid": [1.0] * n, "ask": [1.1] * n})
    eod.to_csv(directory / "eod.csv.gz", index=False, compression="gzip")
    if include_oi:
        oi_value = 5000 if liquid else 1
        oi = eod[["expiration", "strike", "right"]].copy()
        oi["open_interest"] = oi_value
        oi.to_csv(directory / "open_interest.csv.gz", index=False, compression="gzip")
    if include_greeks:
        greeks = eod[["expiration", "strike", "right"]].copy()
        # abs(delta) in [0.10, 0.90]; dollar delta/gamma/vega comfortably above the
        # ported thresholds so `quality` is driven by spread/dte/OI in the tests.
        greeks["delta"] = [-0.5 if r == "PUT" else 0.5 for r in eod["right"]]
        greeks["gamma"] = 0.05
        greeks["vega"] = 20.0
        greeks["theta"] = -0.02
        greeks["implied_vol"] = 0.15
        greeks["iv_error"] = 0.0
        greeks["underlying_price"] = spot
        greeks.to_csv(directory / "greeks_eod.csv.gz", index=False, compression="gzip")
    return directory


def test_maps_right_and_pulls_underlying_from_greeks(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    write_partition(root, "LQD", "2025-01-02")
    panel = build.assemble_partitions([root])
    chains = build.lean_chains(panel)
    assert set(chains["right"]) == {"P", "C"}
    assert (chains["underlying"] == 105.0).all()
    assert list(chains.columns) == build.CHAIN_COLUMNS


def test_missing_oi_is_nan_not_zero(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    write_partition(root, "LQD", "2025-01-02", include_oi=False)
    chains = build.lean_chains(build.assemble_partitions([root]))
    assert chains["open_interest"].isna().all()


def test_duplicate_oi_key_collapses_when_values_agree(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02", strikes=(100.0, 101.0))
    oi = pd.read_csv(directory / "open_interest.csv.gz")
    oi["open_interest"] = [10, 20]
    repeated = pd.concat([oi, oi.iloc[[0]]], ignore_index=True)  # a republished duplicate, same value
    repeated.to_csv(directory / "open_interest.csv.gz", index=False, compression="gzip")
    chains = build.lean_chains(build.assemble_partitions([root]))
    assert chains.set_index("strike")["open_interest"].to_dict() == {100.0: 10, 101.0: 20}


def test_duplicate_oi_key_with_conflicting_values_is_refused(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02", strikes=(100.0, 101.0))
    oi = pd.read_csv(directory / "open_interest.csv.gz")
    oi["open_interest"] = [10, 20]
    conflicting_row = oi.iloc[[0]].copy()
    conflicting_row["open_interest"] = 99  # same key, different value -- must not be silently resolved
    repeated = pd.concat([oi, conflicting_row], ignore_index=True)
    repeated.to_csv(directory / "open_interest.csv.gz", index=False, compression="gzip")
    with pytest.raises(ValueError, match="Conflicting open_interest"):
        build.assemble_partitions([root])


def test_missing_greeks_partition_is_skipped_not_fatal(tmp_path):
    # A ticker/date with EOD (and OI) but no Greeks at all is excluded, the
    # same as an unpulled date -- it must not abort a build spanning other,
    # complete dates (observed for real: a full trading year on 5 of 8
    # tickers in the first full 2016-2026 pull).
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02", "2025-01-03"])
    write_partition(root, "LQD", "2025-01-02", include_greeks=False)
    write_partition(root, "LQD", "2025-01-03")
    chains = build.lean_chains(build.assemble_partitions([root]))
    assert set(chains["snap_date"]) == {"2025-01-03"}


def test_all_dates_missing_greeks_is_refused_as_no_partitions(tmp_path):
    # If every date lacks Greeks (e.g. --greeks was never used for the whole
    # pull), assemble_partitions's "no completed partitions" check still
    # catches that degenerate case, just at the end rather than the first date.
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    write_partition(root, "LQD", "2025-01-02", include_greeks=False)
    with pytest.raises(ValueError, match="No completed partitions found"):
        build.assemble_partitions([root])


def test_nonconstant_underlying_within_a_partition_is_refused(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02")
    greeks = pd.read_csv(directory / "greeks_eod.csv.gz")
    greeks.loc[0, "underlying_price"] = 999.0
    greeks.to_csv(directory / "greeks_eod.csv.gz", index=False, compression="gzip")
    with pytest.raises(ValueError, match="Non-constant"):
        build.assemble_partitions([root])


def test_unexpected_right_value_is_refused(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02")
    eod = pd.read_csv(directory / "eod.csv.gz")
    eod.loc[0, "right"] = "STRADDLE"
    eod.to_csv(directory / "eod.csv.gz", index=False, compression="gzip")
    with pytest.raises(ValueError, match="Unexpected option right"):
        build.assemble_partitions([root])


def test_duplicate_key_across_pull_roots_is_refused(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    write_manifest(first, ["LQD"], ["2025-01-02"])
    write_partition(first, "LQD", "2025-01-02")
    write_manifest(second, ["LQD"], ["2025-01-02"])
    write_partition(second, "LQD", "2025-01-02")
    with pytest.raises(ValueError, match="Duplicate contract key"):
        build.assemble_partitions([first, second])


def test_no_data_partition_is_skipped_not_fabricated(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02", "2025-01-03"])
    write_partition(root, "LQD", "2025-01-02")
    # 2025-01-03 has no directory at all -- an unpulled/no_data date.
    chains = build.lean_chains(build.assemble_partitions([root]))
    assert set(chains["snap_date"]) == {"2025-01-02"}


def test_liquid_gate_separates_deep_book_from_thin_book(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD", "ILLQ"], ["2025-01-02"])
    write_partition(root, "LQD", "2025-01-02", strikes=tuple(range(90, 110)), liquid=True)
    write_partition(root, "ILLQ", "2025-01-02", strikes=tuple(range(90, 110)), liquid=False)
    panel = build.assemble_partitions([root])
    summary, ticker_level = build.ticker_summary(panel)
    levels = ticker_level.set_index("ticker")
    assert bool(levels.loc["LQD", "liquid"]) is True
    assert bool(levels.loc["ILLQ", "liquid"]) is False
    assert levels.loc["LQD", "median_liq_score"] > levels.loc["ILLQ", "median_liq_score"]


def test_wide_spread_and_offband_delta_fail_quality(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02", strikes=(100.0, 101.0, 102.0))
    eod = pd.read_csv(directory / "eod.csv.gz")
    eod.loc[0, ["bid", "ask"]] = [1.0, 5.0]  # wide relative spread
    eod.to_csv(directory / "eod.csv.gz", index=False, compression="gzip")
    greeks = pd.read_csv(directory / "greeks_eod.csv.gz")
    greeks.loc[1, "delta"] = 0.02  # outside [0.10, 0.90]
    greeks.to_csv(directory / "greeks_eod.csv.gz", index=False, compression="gzip")
    panel = build.assemble_partitions([root])
    quality = build.contract_quality(panel).set_index("strike")["quality"]
    assert not quality.loc[100.0] and not quality.loc[101.0] and quality.loc[102.0]


def test_write_once_and_manifest_records_source_pulls(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    write_partition(root, "LQD", "2025-01-02")
    output_root = tmp_path / "out"
    destination = build.build_and_write([root], output_root, "ds1")
    manifest = json.loads((destination / "manifest.json").read_text())
    assert manifest["chain_rows"] == 2 and manifest["tickers"] == ["LQD"]
    assert str(root) in manifest["source_pulls"]
    with pytest.raises(FileExistsError):
        build.build_and_write([root], output_root, "ds1")


def test_invalid_dataset_id_is_refused(tmp_path):
    with pytest.raises(ValueError, match="dataset-id"):
        build.build_and_write([tmp_path], tmp_path / "out", "../escape")


# --- v2: quote eligibility / strategy scope / OI-based sizing, kept separate ---

def build_one_sided_pull(tmp_path):
    """A put-only book: real, positive OI on puts, zero calls anywhere in scope."""
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02", strikes=(100.0, 101.0, 102.0))
    # "right" must agree across all three files -- they're joined on it.
    for name, edits in [("eod", {}), ("greeks_eod", {"delta": -0.5}), ("open_interest", {"open_interest": 5000})]:
        frame = pd.read_csv(directory / f"{name}.csv.gz")
        frame["right"] = "PUT"
        for column, value in edits.items():
            frame[column] = value
        frame.to_csv(directory / f"{name}.csv.gz", index=False, compression="gzip")
    return root


def test_quote_eligibility_ignores_scope_and_oi(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02")
    greeks = pd.read_csv(directory / "greeks_eod.csv.gz")
    greeks["delta"] = 0.02  # well outside the strategy-scope delta band
    greeks.to_csv(directory / "greeks_eod.csv.gz", index=False, compression="gzip")
    panel = build.assemble_partitions([root])
    # Quote-eligible (valid two-sided quote, tight spread) regardless of the
    # off-band delta -- scope is a separate question.
    assert build.quote_eligibility(panel).all()
    assert not build.strategy_scope(panel).any()


def test_oi_status_distinguishes_missing_zero_positive_invalid(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02", strikes=(100.0, 101.0, 102.0, 103.0))
    oi = pd.read_csv(directory / "open_interest.csv.gz")
    oi["open_interest"] = [0, 10, -5, 2.5]
    oi.to_csv(directory / "open_interest.csv.gz", index=False, compression="gzip")
    panel = build.assemble_partitions([root])
    by_strike = build.oi_status(panel).groupby(panel["strike"]).first()
    assert by_strike[100.0] == "zero"
    assert by_strike[101.0] == "positive"
    assert by_strike[102.0] == "invalid"  # negative
    assert by_strike[103.0] == "invalid"  # fractional


def test_oi_status_missing_when_no_oi_partition(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    write_partition(root, "LQD", "2025-01-02", include_oi=False)
    panel = build.assemble_partitions([root])
    assert (build.oi_status(panel) == "missing").all()


def test_oi_capped_size_zero_unless_positive(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    write_partition(root, "LQD", "2025-01-02", include_oi=False)
    panel = build.assemble_partitions([root])
    assert (build.oi_capped_size(panel, 0.05) == 0.0).all()
    with pytest.raises(ValueError, match="oi_fraction"):
        build.oi_capped_size(panel, 1.5)


def test_liquidity_profile_reports_one_sided_notional_unlike_v1(tmp_path):
    root = build_one_sided_pull(tmp_path)
    panel = build.assemble_partitions([root])
    _, v1_ticker = build.ticker_summary(panel)
    v2_summary = build.liquidity_profile(panel)
    # v1's book_balance gate zeroes an all-put book (no calls to balance against).
    assert v1_ticker.set_index("ticker").loc["LQD", "median_liq_score"] == 0.0
    # v2 reports the put-side notional directly, with no balance requirement and
    # no composite score or flag to check instead.
    row = v2_summary.iloc[0]
    assert row["put_notional"] > 0 and row["call_notional"] == 0
    assert not {"liq_score", "put_liq_score", "liquid", "put_liquid"} & set(v2_summary.columns)


def test_liquidity_profile_is_a_single_frame_not_a_ticker_rollup(tmp_path):
    root = build_one_sided_pull(tmp_path)
    panel = build.assemble_partitions([root])
    result = build.liquidity_profile(panel)
    assert isinstance(result, pd.DataFrame)  # one per-date frame, not a (summary, ticker_level) pair


def test_liquidity_profile_require_scope_toggle(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02", strikes=(100.0, 101.0))
    greeks = pd.read_csv(directory / "greeks_eod.csv.gz")
    greeks["delta"] = [0.02, -0.5]  # first contract out of scope, second in scope
    greeks.to_csv(directory / "greeks_eod.csv.gz", index=False, compression="gzip")
    panel = build.assemble_partitions([root])
    in_scope_summary = build.liquidity_profile(panel, require_scope=True)
    full_summary = build.liquidity_profile(panel, require_scope=False)
    assert in_scope_summary["eligible_contracts"].iloc[0] < full_summary["eligible_contracts"].iloc[0]


def test_oi_capped_put_menu_reports_menu_not_a_hedge_cost(tmp_path):
    root = build_one_sided_pull(tmp_path)
    panel = build.assemble_partitions([root])
    menu = build.oi_capped_put_menu(panel, oi_fraction=0.05, right="P")
    row = menu.iloc[0]
    assert row["candidate_contracts"] == 3
    assert row["oi_positive"] == 3
    assert row["menu_strikes"] == 3
    assert row["total_menu_contracts_continuous"] == pytest.approx(3 * 5000 * 0.05)
    # priced at the ask (1.1 in build_one_sided_pull), not the mid (1.05)
    expected_cost = (3 * 5000 * 0.05) * build.CONTRACT_MULTIPLIER * 1.1
    assert row["full_menu_premium_cost_usd"] == pytest.approx(expected_cost)


def test_oi_capped_put_menu_keeps_dates_with_zero_candidates(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02", "2025-01-03"])
    write_partition(root, "LQD", "2025-01-02")  # has candidates
    write_partition(root, "LQD", "2025-01-03")  # will have zero puts qualify
    directory = root / "LQD" / "2025-01-03"
    for name in ("eod", "greeks_eod", "open_interest"):
        frame = pd.read_csv(directory / f"{name}.csv.gz")
        frame["right"] = "CALL"  # no puts at all this date
        frame.to_csv(directory / f"{name}.csv.gz", index=False, compression="gzip")
    panel = build.assemble_partitions([root])
    menu = build.oi_capped_put_menu(panel, oi_fraction=0.05, right="P")
    assert set(menu["snap_date"]) == {"2025-01-02", "2025-01-03"}
    empty_row = menu.set_index("snap_date").loc["2025-01-03"]
    assert empty_row["candidate_contracts"] == 0
    assert empty_row["menu_strikes"] == 0
    assert empty_row["total_menu_contracts_continuous"] == 0.0
    assert pd.isna(empty_row["median_spread_of_menu"])
    assert pd.isna(empty_row["min_strike_spot"]) and pd.isna(empty_row["max_strike_spot"])


def test_quote_eligibility_rejects_crossed_quote(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    directory = write_partition(root, "LQD", "2025-01-02", strikes=(100.0, 101.0))
    eod = pd.read_csv(directory / "eod.csv.gz")
    eod.loc[0, ["bid", "ask"]] = [2.0, 1.0]  # crossed: ask < bid
    eod.to_csv(directory / "eod.csv.gz", index=False, compression="gzip")
    panel = build.assemble_partitions([root])
    eligible = pd.Series(build.quote_eligibility(panel).to_numpy(), index=panel["strike"].to_numpy())
    assert not eligible[100.0] and eligible[101.0]


def test_screen_version_v1_default_matches_prior_behavior(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    write_partition(root, "LQD", "2025-01-02")
    default_dest = build.build_and_write([root], tmp_path / "out_default", "ds")
    explicit_dest = build.build_and_write([root], tmp_path / "out_explicit", "ds", screen_version="v1")
    assert (pd.read_csv(default_dest / "ticker_summary.csv")
           .equals(pd.read_csv(explicit_dest / "ticker_summary.csv")))


def test_screen_version_v2_writes_no_ticker_rollup(tmp_path):
    root = build_one_sided_pull(tmp_path)
    destination = build.build_and_write([root], tmp_path / "out", "v2-run", screen_version="v2")
    assert not (destination / "ticker_summary.csv").exists()
    manifest = json.loads((destination / "manifest.json").read_text())
    assert manifest["liquid_tickers"] is None  # null, not a list, and not prose in the same field
    assert "notes" in manifest and "no composite score" in manifest["notes"].lower()


def test_screen_version_v1_manifest_schema_unchanged(tmp_path):
    root = tmp_path / "pull"
    write_manifest(root, ["LQD"], ["2025-01-02"])
    write_partition(root, "LQD", "2025-01-02")
    destination = build.build_and_write([root], tmp_path / "out", "v1-run", screen_version="v1")
    manifest = json.loads((destination / "manifest.json").read_text())
    assert isinstance(manifest["liquid_tickers"], list)
    assert "notes" not in manifest


def test_screen_versions_share_identical_chains_csv(tmp_path):
    root = build_one_sided_pull(tmp_path)
    v1_dest = build.build_and_write([root], tmp_path / "out", "v1-run", screen_version="v1")
    v2_dest = build.build_and_write([root], tmp_path / "out", "v2-run", screen_version="v2")
    assert pd.read_csv(v1_dest / "chains.csv").equals(pd.read_csv(v2_dest / "chains.csv"))
    v2_summary = pd.read_csv(v2_dest / "summary.csv")
    assert "put_notional" in v2_summary.columns and "book_balance" not in v2_summary.columns
    assert json.loads((v2_dest / "manifest.json").read_text())["screen_version"] == "v2"


def test_invalid_screen_version_is_refused(tmp_path):
    with pytest.raises(ValueError, match="screen_version"):
        build.build_and_write([tmp_path], tmp_path / "out", "ds", screen_version="v3")
