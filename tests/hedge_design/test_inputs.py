"""Synthetic audit fixtures; no credentials, vendor data, or network required."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.data.hedge_inputs import (
    CHAIN_PATH, CORE_PATH, PRICE_PATH, audit_inputs, inventory_sources,
    inspect_raw_chains, load_chains, load_prices, pilot_coverage, quote_flags,
    reconcile_chains, render_audit, sha256_file, write_audit,
)
from src.data import hedge_inputs


def contracts():
    return pd.DataFrame([
        {"ticker": ticker, "snap_date": "2024-01-02", "expiry": "2024-02-02",
         "right": "P", "strike": 100.0, "underlying": 100.0,
         "bid": 1.0, "ask": 1.1, "open_interest": 10.0}
        for ticker in ("LQD", "TLT", "IEF")
    ])


@pytest.fixture
def input_root(tmp_path):
    chain = contracts()
    for name in (CHAIN_PATH, CORE_PATH, PRICE_PATH):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    chain.to_csv(tmp_path / CHAIN_PATH, index=False)
    for ticker, rows in chain.groupby("ticker"):
        path = tmp_path / "data/raw/options_screen" / ticker / "2024-01-02_chain.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(rows.to_dict("records")))
    pd.DataFrame({"Date": ["2023-12-29"], "Symbol": ["LQD"], "Return": [0.01]}).to_csv(
        tmp_path / CORE_PATH, index=False)
    pd.DataFrame({"Date": ["2023-12-29", "2024-01-02", "2024-02-02"],
                  "LQD": [99, 100, 90], "TLT": [99, 100, 110],
                  "IEF": [99, 100, 105]}).to_csv(tmp_path / PRICE_PATH, index=False)
    return tmp_path


def test_audit_pins_sources_without_mutation_and_does_not_claim_readiness(input_root):
    before = inventory_sources(input_root)
    manifest, tables = audit_inputs(input_root, "synthetic")
    assert inventory_sources(input_root) == before
    assert manifest["raw_derived_reconciliation"]["status"] == "match"
    assert manifest["readiness"]["source_integrity"] == "pass"
    assert manifest["readiness"]["total_return_hedge_design"].startswith("blocked")
    assert "missing_universe_HYG" in {item["code"] for item in manifest["issues"]}
    assert (tables["pilot_coverage"]["status"] == "price_coverage_only").all()
    assert "not a hedge backtest" in render_audit(manifest)
    json.dumps(manifest, allow_nan=False)


def test_fingerprint_stable_and_changes_when_input_changes(input_root):
    first, tables = audit_inputs(input_root, "first")
    report = write_audit(input_root, first, tables)
    second, _ = audit_inputs(input_root, "second")
    assert report.exists()
    assert first["input_fingerprint"] == second["input_fingerprint"]
    path = input_root / PRICE_PATH
    prices = pd.read_csv(path)
    prices.loc[0, "LQD"] += 1
    prices.to_csv(path, index=False)
    third, _ = audit_inputs(input_root, "third")
    assert third["input_fingerprint"] != first["input_fingerprint"]


def test_existing_output_is_never_overwritten(input_root):
    manifest, tables = audit_inputs(input_root, "one")
    report = write_audit(input_root, manifest, tables)
    before = sha256_file(report)
    with pytest.raises(FileExistsError):
        write_audit(input_root, manifest, tables)
    assert sha256_file(report) == before


@pytest.mark.parametrize("dataset_id", ["../escape", "/tmp/x", "", "x/y", ".hidden"])
def test_invalid_dataset_id_rejected_before_read(input_root, dataset_id):
    with pytest.raises(ValueError, match="dataset-id"):
        audit_inputs(input_root, dataset_id)


def test_duplicate_contract_key_is_rejected(input_root):
    frame = contracts()
    pd.concat([frame, frame.iloc[[0]]]).to_csv(input_root / CHAIN_PATH, index=False)
    with pytest.raises(ValueError, match="Duplicate contract key"):
        load_chains(input_root / CHAIN_PATH)
    manifest, _ = audit_inputs(input_root, "duplicates")
    assert manifest["readiness"]["source_integrity"] == "fail"


def test_duplicate_price_date_is_rejected(input_root):
    frame = pd.read_csv(input_root / PRICE_PATH)
    pd.concat([frame, frame.iloc[[0]]]).to_csv(input_root / PRICE_PATH, index=False)
    with pytest.raises(ValueError, match="duplicate price date"):
        load_prices(input_root / PRICE_PATH)


def test_missing_inputs_produce_blocked_report(tmp_path):
    manifest, _ = audit_inputs(tmp_path, "missing")
    assert manifest["readiness"]["source_integrity"] == "fail"
    assert manifest["raw_derived_reconciliation"]["status"] == "unavailable"
    assert "invalid_prices" in {i["code"] for i in manifest["issues"]}


def test_empty_corrupt_and_mismatched_caches_have_distinct_status(input_root):
    directory = input_root / "data/raw/options_screen/LQD"
    (directory / "2024-02-01_chain.json").write_text("[]")
    (directory / "2024-03-01_chain.json").write_text("{broken")
    (directory / "2024-04-01_chain.json").write_text(json.dumps(contracts().to_dict("records")))
    (directory / "2024-05-01_chain.json").write_text("{}")
    _, diagnostics = inspect_raw_chains(input_root)
    assert {"empty_unverified", "unreadable", "path_record_mismatch", "invalid_schema"}.issubset(
        set(diagnostics["status"]))
    manifest, _ = audit_inputs(input_root, "bad-caches")
    assert manifest["readiness"]["source_integrity"] == "fail"


def test_reconciliation_checks_values_but_not_row_order(input_root):
    raw, _ = inspect_raw_chains(input_root)
    derived = load_chains(input_root / CHAIN_PATH)
    assert reconcile_chains(raw, derived.iloc[::-1])["status"] == "match"
    derived.loc[0, "ask"] = 50
    assert reconcile_chains(raw, derived)["status"] == "mismatch"


def test_quote_audit_distinguishes_oi_from_quote_eligibility(input_root):
    frame = load_chains(input_root / CHAIN_PATH)
    frame["open_interest"] = [np.nan, 0, -1]
    flags = quote_flags(frame)
    assert flags["quote_eligible"].all()
    assert flags["oi_missing"].tolist() == [True, False, False]
    assert flags["oi_zero"].tolist() == [False, True, False]
    assert flags["oi_invalid"].tolist() == [False, False, True]
    frame["bid"] = [2, 0, np.inf]
    assert not quote_flags(frame)["quote_eligible"].any()


def test_pilot_uses_one_expiry_and_does_not_fill_missing_prices(input_root):
    frame = load_chains(input_root / CHAIN_PATH)
    # A second LQD expiration must not replace the shared, nearest expiration.
    frame.loc[frame["ticker"] == "LQD", "expiry"] = pd.Timestamp("2024-02-09")
    prices = load_prices(input_root / PRICE_PATH)
    prices.loc[pd.Timestamp("2024-02-02"), "IEF"] = np.nan
    coverage = pilot_coverage(frame, prices).set_index("ticker")
    assert coverage["expiry"].nunique() == 1
    assert coverage.loc["LQD", "status"] == "empty_menu"
    assert coverage.loc["IEF", "status"] == "missing_exact_price"
    assert coverage.loc["TLT", "prior_price_rows"] == 1


def test_secret_files_are_not_inventoried(input_root):
    (input_root / ".env").write_text("SECRET=synthetic-never-export")
    manifest, tables = audit_inputs(input_root, "no-secrets")
    assert not tables["source_files"]["path"].str.contains(".env", regex=False).any()
    assert "synthetic-never-export" not in json.dumps(manifest)


def test_cloud_only_sources_are_not_opened_or_claimed_as_pinned(input_root, monkeypatch):
    target = input_root / "data/raw/options_screen/TLT/2024-01-02_chain.json"
    monkeypatch.setattr(hedge_inputs, "is_cloud_placeholder", lambda path: path == target)
    original = type(target).read_text

    def guarded_read(path, *args, **kwargs):
        assert path != target, "Cloud-only source must not be opened"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(type(target), "read_text", guarded_read)
    manifest, tables = audit_inputs(input_root, "cloud")
    assert not manifest["content_fingerprint_complete"]
    assert manifest["raw_derived_reconciliation"]["status"] == "unavailable"
    assert manifest["readiness"]["source_integrity"] == "fail"
    assert manifest["available_raw_comparison"]["status"] == "match"
    assert manifest["readiness"]["descriptive_analysis"] == "conditional_on_derived_inputs"
    row = tables["source_files"].set_index("path").loc[target.relative_to(input_root).as_posix()]
    assert row["status"] == "cloud_placeholder"
    assert pd.isna(row["sha256"])


def test_incomplete_raw_cache_still_detects_mismatched_available_rows(input_root, monkeypatch):
    target = input_root / "data/raw/options_screen/TLT/2024-01-02_chain.json"
    monkeypatch.setattr(hedge_inputs, "is_cloud_placeholder", lambda path: path == target)
    chain = pd.read_csv(input_root / CHAIN_PATH)
    chain.loc[chain["ticker"] == "LQD", "ask"] = 5
    chain.to_csv(input_root / CHAIN_PATH, index=False)
    manifest, _ = audit_inputs(input_root, "partial-mismatch")
    assert manifest["available_raw_comparison"]["status"] == "mismatch"
    assert manifest["readiness"]["descriptive_analysis"] == "blocked"


def test_wrong_core_schema_is_a_blocker(input_root):
    pd.DataFrame({"unknown": [1]}).to_csv(input_root / CORE_PATH, index=False)
    manifest, _ = audit_inputs(input_root, "bad-core")
    assert manifest["readiness"]["source_integrity"] == "fail"
    assert "invalid_core_schema" in {i["code"] for i in manifest["issues"]}
