"""Preservation, archive routing and active dependency boundaries."""
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("preserve_research", ROOT / "scripts/preserve_research.py")
preserve = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preserve)


def test_snapshot_restore_is_exact_and_never_overwrites(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/example.py").write_text("answer = 42\n")
    (tmp_path / ".env").write_text("PRIVATE_TOKEN=not-a-real-token")
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/raw/input.csv").write_text("private vendor input")
    monkeypatch.setattr(preserve.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="abc123\n"))
    monkeypatch.setattr(preserve.platform, "platform", lambda: "synthetic-platform")
    snapshot = preserve.snapshot(tmp_path, "test")
    manifest = preserve.verify(snapshot)
    assert manifest["files"] == {"src/example.py": preserve.digest(b"answer = 42\n")}
    target = tmp_path / "restored"
    preserve.restore(snapshot, target)
    assert (target / "src/example.py").read_bytes() == b"answer = 42\n"
    assert not (target / ".env").exists()
    with pytest.raises(FileExistsError):
        preserve.restore(snapshot, target)
    with pytest.raises(FileExistsError):
        preserve.snapshot(tmp_path, "test")
    (snapshot / "sources.zip").write_bytes(b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        preserve.verify(snapshot)


def test_restore_rejects_path_traversal(tmp_path):
    payload = b"malicious"
    with zipfile.ZipFile(tmp_path / "sources.zip", "w") as archive:
        archive.writestr("../escape.txt", payload)
    (tmp_path / "manifest.json").write_text(json.dumps({
        "files": {"../escape.txt": preserve.digest(payload)},
        "archive_sha256": preserve.digest((tmp_path / "sources.zip").read_bytes()),
    }))
    with pytest.raises(ValueError, match="Unsafe archive path"):
        preserve.restore(tmp_path, tmp_path / "restore")
    assert not (tmp_path / "escape.txt").exists()


def test_snapshot_rejects_symlinks_and_bad_ids(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "outside.py").write_text("secret")
    (tmp_path / "src/link.py").symlink_to(tmp_path / "outside.py")
    with pytest.raises(ValueError, match="regular file"):
        preserve.snapshot(tmp_path, "symlink")
    for snapshot_id in ("../escape", "", "/absolute"):
        with pytest.raises(ValueError, match="simple snapshot"):
            preserve.snapshot(tmp_path, snapshot_id)


def test_active_scientific_dependency_closure_has_no_legacy_imports():
    paths = list((ROOT / "src/hedge_design").glob("*.py")) + [
        ROOT / "src/data/hedge_inputs.py", ROOT / "src/__init__.py", ROOT / "src/data/__init__.py"]
    allowed_external = set(sys.stdlib_module_names) | {"numpy", "pandas", "scipy", "src"}
    allowed_project = {"src", "src.data", "src.data.hedge_inputs", "src.hedge_design"}
    allowed_project.update("src.hedge_design." + path.stem for path in (ROOT / "src/hedge_design").glob("*.py"))
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, f"Audit relative import explicitly: {path}"
                names = [node.module]
                if node.module in {"src", "src.data", "src.hedge_design"}:
                    names += [node.module + "." + alias.name for alias in node.names]
            for name in names:
                assert name.split(".")[0] in allowed_external, (path, name)
                if name.startswith("src"):
                    assert name in allowed_project, (path, name)


@pytest.mark.parametrize("name", ["01_exploration.ipynb", "02_rolling_risk_metrics.ipynb", "03_analysis.ipynb",
                                  "04_iv_subsumption.ipynb", "05_options_analysis.ipynb"])
def test_archived_notebook_bootstrap_resolves_root_without_execution(name, monkeypatch):
    assert not (ROOT / "notebooks" / name).exists()
    path = ROOT / "legacy/unified/notebooks" / name
    notebook = json.loads(path.read_text())
    code = next("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
    prefix = code.split("sys.path.insert")[0]
    for cwd in (ROOT, path.parent):
        monkeypatch.chdir(cwd)
        namespace = {}
        exec(compile(prefix, str(path), "exec"), namespace)
        assert namespace["ROOT"] == ROOT


def test_legacy_scripts_resolve_original_repository():
    for name in ("07_robustness_ladder.py", "09_fragility_h4.py"):
        assert not (ROOT / "scripts" / name).exists()
        path = ROOT / "legacy/unified/scripts" / name
        assert path.parents[3] == ROOT
        compile(path.read_text(), str(path), "exec")


def test_requirements_cover_all_workflows():
    expected = {"pandas", "numpy", "yfinance", "matplotlib", "requests", "urllib3",
                "jupyter", "xlrd", "statsmodels", "scipy", "thetadata>=1.0.7",
                "seaborn", "pytest", "scikit-learn", "patsy", "nbformat", "nbclient",
                "nbconvert", "ipykernel"}
    assert set((ROOT / "requirements.txt").read_text().splitlines()) == expected


@pytest.mark.parametrize("name", ["requirements.txt", "study_config.json"])
def test_source_snapshot_includes_root_settings(tmp_path, name):
    source = tmp_path / name
    source.write_text("numpy\n")
    assert source in preserve.source_paths(tmp_path)


def test_snapshot_keeps_source_data_modules_but_excludes_legacy_market_data(tmp_path):
    source = tmp_path / "src/data/hedge_inputs.py"
    archived = tmp_path / "legacy/unified/src/data/options.py"
    market = tmp_path / "legacy/unified/data/raw/private.json"
    for path in (source, archived, market):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
    assert set(preserve.source_paths(tmp_path)) == {source, archived}
