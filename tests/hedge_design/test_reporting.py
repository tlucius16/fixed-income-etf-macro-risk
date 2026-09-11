"""Synthetic reporting integrity checks; no local market data or plotting needed."""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.reporting import hedge_design as reporting


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("identifier", ["../escape", "/absolute", "", "a/b", "a.b", "-bad"])
def test_identifiers_cannot_escape_output_root(tmp_path, identifier):
    with pytest.raises(ValueError):
        reporting.identified_directory(tmp_path, identifier)


def test_hash_verification_rejects_changes_and_symlinks(tmp_path):
    source = tmp_path / "saved.csv"
    source.write_text("value\n1\n")
    hashes = {source.name: reporting.digest(source)}
    reporting.verify_hashes(tmp_path, hashes)
    source.write_text("value\n2\n")
    with pytest.raises(ValueError, match="Changed artifact"):
        reporting.verify_hashes(tmp_path, hashes)
    (tmp_path / "link.csv").symlink_to(source)
    with pytest.raises(ValueError, match="Symlink"):
        reporting.verify_hashes(tmp_path, {"link.csv": reporting.digest(source)})
    with pytest.raises(ValueError, match="Unsafe"):
        reporting.verify_hashes(tmp_path, {"../saved.csv": "unused"})


def test_anatomy_keeps_dates_sides_and_unknown_oi_separate():
    chains = pd.DataFrame([
        ["LQD", "2025-01-02", "C", "2025-01-31", 100, 10],
        ["LQD", "2025-01-02", "P", "2025-01-31", 100, 0],
        ["LQD", "2025-01-02", "P", "2025-01-31", 101, np.nan],
        ["LQD", "2025-04-01", "C", "2025-04-30", 100, 10],
        ["LQD", "2025-04-01", "P", "2025-04-30", 100, -2],
        ["LQD", "2025-04-01", "P", "2025-04-30", 101, np.inf],
    ], columns=["ticker", "snap_date", "right", "expiry", "strike", "open_interest"])
    result = reporting.market_anatomy(chains)
    assert len(result) == 4
    assert result.query("right == 'C'").recorded_oi.tolist() == [10, 10]
    puts = result.query("right == 'P'")
    assert puts.iloc[0].zero_oi == 1
    assert puts.iloc[0].unknown_or_invalid_oi == 1
    assert puts.iloc[1].unknown_or_invalid_oi == 2
    assert np.isnan(puts.iloc[1].recorded_oi)
    with pytest.raises(ValueError, match="duplicate"):
        reporting.market_anatomy(pd.concat([chains, chains.iloc[:1]]))


def test_basis_point_conversion_does_not_mutate_cash_flows():
    original = pd.DataFrame({"oi_fraction": [np.nan, .05], "nominal_cvar_usd": [1e6, 2e6]})
    converted = reporting.loss_units(original, 1e8)
    assert converted.nominal_cvar_bps.tolist() == [100, 200]
    assert converted.access.tolist() == ["Uncapped", "5% OI assumption"]
    assert original.columns.tolist() == ["oi_fraction", "nominal_cvar_usd"]


def common_fixture():
    policies = ["duration", "unhedged"] + [f"{method}__{menu}"
                for method in ("nominal", "robust") for menu in reporting.MENUS]
    outcomes = pd.DataFrame([
        {"policy": policy, "oi_fraction": cap, "decision_date": date,
         "realized_net_loss_usd": loss, "spent_usd": 100.0}
        for policy in policies for cap in (np.nan, .05)
        for date, loss in [("2024-01-02", -1000.), ("2025-01-02", 3000.)]
    ])
    summary = pd.DataFrame([
        {"policy": policy, "oi_fraction": cap, "matched_dates": 2, "mean_loss_bps": 10.,
         "worst_loss_bps": 30., "mean_spent_bps": 1.}
        for policy in policies for cap in (np.nan, .05)
    ])
    return outcomes, summary


def test_common_outcome_summary_is_reconstructed():
    outcomes, summary = common_fixture()
    reporting.validate_common_outcomes(outcomes, summary, 1e6)
    summary.loc[0, "mean_loss_bps"] += 1
    with pytest.raises(ValueError, match="disagrees"):
        reporting.validate_common_outcomes(outcomes, summary, 1e6)


@pytest.mark.parametrize("change", ["date", "duplicate", "policy", "nonfinite"])
def test_outcome_comparisons_fail_closed(change):
    outcomes, summary = common_fixture()
    if change == "date":
        outcomes.loc[0, "decision_date"] = "2023-01-02"
    elif change == "duplicate":
        outcomes = pd.concat([outcomes, outcomes.iloc[:1]])
    elif change == "policy":
        outcomes = outcomes.query("policy != 'unhedged'")
    else:
        outcomes.loc[0, "realized_net_loss_usd"] = np.nan
    with pytest.raises(ValueError):
        reporting.validate_common_outcomes(outcomes, summary, 1e6)


def test_draft_values_are_inserted_from_tables_and_missing_tokens_fail():
    rendered = reporting.render_draft("{{metric:count}}\n{{table:risk}}",
                                     {"risk": pd.DataFrame({"loss_bps": [123.456]})}, {"count": 2})
    assert "123.46" in rendered and rendered.startswith("2\n")
    with pytest.raises(KeyError):
        reporting.render_draft("{{metric:missing}}", {}, {})
    with pytest.raises(ValueError, match="Unresolved"):
        reporting.render_draft("{{unsupported}}", {}, {})


def test_bundle_reader_is_read_only_and_detects_tampering(tmp_path):
    directory = tmp_path / "results/hedge_paper/example"
    (directory / "tables").mkdir(parents=True)
    table = directory / "tables/risk.csv"
    table.write_text("loss_bps\n1\n")
    manifest = {"schema_version": 1, "build_id": "example", "run_id": "science",
                "outputs": {"tables/risk.csv": reporting.digest(table)}}
    (directory / "manifest.json").write_text(json.dumps(manifest))
    before = {path: reporting.digest(path) for path in directory.rglob("*") if path.is_file()}
    _, frames = reporting.load_bundle(tmp_path, "example")
    assert frames["risk"].loss_bps.tolist() == [1]
    assert before == {path: reporting.digest(path) for path in directory.rglob("*") if path.is_file()}
    table.write_text("loss_bps\n2\n")
    with pytest.raises(ValueError, match="Changed"):
        reporting.load_bundle(tmp_path, "example")


def test_existing_build_rejected_before_reading_science(tmp_path, monkeypatch):
    (tmp_path / "results/hedge_paper/exists").mkdir(parents=True)
    monkeypatch.setattr(reporting, "load_run", lambda *args: pytest.fail("Read science before overwrite check"))
    with pytest.raises(ValueError, match="overwrite"):
        reporting.build_paper(tmp_path, "unused", "exists")


def test_paper_rejects_nominal_only_run(tmp_path):
    directory = tmp_path / "results/hedge_design/nominal"
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(json.dumps({"run_id": "nominal", "phase3": None}))
    with pytest.raises(ValueError, match="completed Phase 3"):
        reporting.load_run(tmp_path, "nominal")


def test_paper_rejects_disabled_robust_before_solving(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("paper_cli", ROOT / "scripts/reproduce_hedge_paper.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    (tmp_path / "study_config.json").write_text(json.dumps({"robust_enabled": False}))
    monkeypatch.setattr(cli.subprocess, "run", lambda *args, **kwargs: pytest.fail("Started solver"))
    with pytest.raises(ValueError, match="robust_enabled: true"):
        cli.science("unused", verify=False)


def test_notebook_and_reporter_have_no_optimizer_acquisition_or_legacy_imports():
    notebook = json.loads((ROOT / "notebooks/06_hedge_frontiers.ipynb").read_text())
    code = "\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
    sources = [code, (ROOT / "src/reporting/hedge_design.py").read_text()]
    forbidden = ("src.hedge_design", "src.data", "src.features", "src.analysis", "legacy", "yfinance", "requests", "scipy.optimize")
    for source in sources:
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(forbidden)
            if isinstance(node, ast.Import):
                assert not any(alias.name.startswith(forbidden) for alias in node.names)
    assert "build_paper" not in code and "write_text" not in code
    assert all(not cell.get("outputs") for cell in notebook["cells"])


def test_cli_reuse_never_runs_optimizer_and_existing_build_is_protected(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("paper_cli", ROOT / "scripts/reproduce_hedge_paper.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(cli, "science", lambda run_id, verify: calls.append((run_id, verify)))
    monkeypatch.setattr(cli, "build_paper", lambda *args: tmp_path / "results/hedge_paper/new")
    monkeypatch.setattr(cli, "execute_review", lambda *args: None)
    monkeypatch.setattr(cli, "verify_paper", lambda *args: None)
    monkeypatch.setattr(cli, "verify_review", lambda *args: None)
    assert cli.main(["--run-id", "existing", "--build-id", "new", "--reuse-run"]) == 0
    assert calls == [("existing", True)]
    (tmp_path / "results/hedge_paper/new").mkdir(parents=True)
    calls.clear()
    assert cli.main(["--run-id", "unused", "--build-id", "new"]) == 1
    assert not calls
