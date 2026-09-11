"""Profile boundaries prevent default runs from regenerating legacy research."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("reproduce", ROOT / "scripts/reproduce.py")
reproduce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reproduce)


def test_default_profile_does_not_load_credentials_or_run_legacy(monkeypatch):
    calls = []
    monkeypatch.setattr(reproduce, "_load_dotenv", lambda: pytest.fail("Default loaded credentials"))
    monkeypatch.setattr(reproduce, "_checkpoints", lambda: pytest.fail("Default ran old checkpoints"))
    monkeypatch.setattr(reproduce, "_run", lambda cmd, name, **kwargs: calls.append((name, cmd)) or 0)
    assert reproduce.main([]) == 0
    assert [name for name, _ in calls] == ["audit", "tests"]
    assert "--verify" in calls[0][1]
    assert not any("ipynb" in arg or "--inplace" == arg for _, cmd in calls for arg in cmd)


def test_incomplete_audit_runs_tests_but_preserves_nonzero_result(monkeypatch):
    names = []

    def run(cmd, name, **kwargs):
        names.append(name)
        return 2 if name == "audit" else 0

    monkeypatch.setattr(reproduce, "_run", run)
    assert reproduce.main([]) == 2
    assert names == ["audit", "tests"]


@pytest.mark.parametrize("args", [["--from", "iv"], ["--until", "h4-ref"],
                                  ["--skip-notebook"], ["--iv-end", "2025-01-01"],
                                  ["--from", "tests", "--until", "audit"],
                                  ["--profile", "legacy", "--dataset-id", "sample"]])
def test_invalid_profile_options_fail_before_running(args, monkeypatch):
    monkeypatch.setattr(reproduce, "_run", lambda *a, **k: pytest.fail("Unexpected stage execution"))
    with pytest.raises(SystemExit) as exc:
        reproduce.main(args)
    assert exc.value.code == 2


def test_profile_listing_is_read_only(monkeypatch, capsys):
    monkeypatch.setattr(reproduce, "_load_dotenv", lambda: pytest.fail("Listing loaded credentials"))
    monkeypatch.setattr(reproduce, "_run", lambda *a, **k: pytest.fail("Listing executed stage"))
    assert reproduce.main(["--list"]) == 0
    assert capsys.readouterr().out.splitlines() == ["audit", "tests"]
    assert reproduce.main(["--profile", "legacy", "--list"]) == 0
    assert "h4-ref" in capsys.readouterr().out.splitlines()


def test_legacy_stage_order_and_paths_remain_available():
    stages = reproduce.build_stages("legacy", "unused", "2025-01-01")
    assert [name for name, _ in stages] == [
        "screen", "iv", "cp-diag", "panel", "ladder", "artifacts", "h4-ref",
        "jl-boot", "jl-amer", "core-nb", "hedge-nb", "tests",
    ]
    assert stages[1][1][-1] == "2025-01-01"
    for _, cmd in stages:
        for arg in cmd:
            if arg.endswith((".py", ".jl", ".ipynb")):
                assert (ROOT / arg).is_file()


def test_legacy_subset_does_not_run_unselected_stages_or_checkpoints(monkeypatch):
    calls = []
    monkeypatch.setattr(reproduce, "_load_dotenv", lambda: None)
    monkeypatch.setattr(reproduce, "_checkpoints", lambda: pytest.fail("Partial legacy run checked all artifacts"))
    monkeypatch.setattr(reproduce, "_run", lambda cmd, name, **k: calls.append(name) or 0)
    assert reproduce.main(["--profile", "legacy", "--from", "h4-ref", "--until", "h4-ref"]) == 0
    assert calls == ["h4-ref"]


def test_legacy_complete_run_keeps_reference_checks(monkeypatch):
    checks = []
    monkeypatch.setattr(reproduce, "_load_dotenv", lambda: None)
    monkeypatch.setattr(reproduce, "_checkpoints", lambda: checks.append(True))
    monkeypatch.setattr(reproduce, "_run", lambda *a, **k: 0)
    assert reproduce.main(["--profile", "legacy", "--from", "tests"]) == 0
    assert checks == [True]


def test_dataset_selection_passed_to_audit():
    stages = reproduce.build_stages("hedge-design", "sample-2", "unused")
    assert stages[0][1][-2:] == ["sample-2", "--verify"]


def test_only_audit_can_treat_exit_two_as_incomplete(monkeypatch):
    monkeypatch.setattr(reproduce.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(returncode=2, stdout="incomplete", stderr=""))
    assert reproduce._run(["unused"], "audit", allow_incomplete=True) == 2
    with pytest.raises(SystemExit):
        reproduce._run(["unused"], "tests")


def test_active_input_module_does_not_import_legacy_analysis():
    tree = ast.parse((ROOT / "src/data/hedge_inputs.py").read_text())
    project_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("src"):
            project_imports.append(node.module)
        if isinstance(node, ast.Import):
            project_imports.extend(n.name for n in node.names if n.name.startswith("src"))
    retired = {"src.features.forward_outcomes", "src.features.vrp",
               "src.reporting.options_notebook", "src.pipelines.build_core_panel"}
    assert retired.isdisjoint(project_imports)
