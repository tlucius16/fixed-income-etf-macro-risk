"""Keep the current reading path and grouped test/environment layout coherent."""
from pathlib import Path
import re
import json


ROOT = Path(__file__).resolve().parents[2]


def test_study_settings_are_consolidated():
    assert not (ROOT / "configs").exists()
    assert isinstance(json.loads((ROOT / "study_config.json").read_text())["robust_enabled"], bool)


def test_main_reading_path_has_no_missing_local_document_links():
    documents = ["README.md", "REPRODUCING.md", "docs/methodology.md", "docs/results.md",
                 "legacy/unified/docs/archive/README.md", "legacy/unified/README.md",
                 "notebooks/README.md", "tests/README.md"]
    for name in documents:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", (ROOT / name).read_text()):
            if ":" in target or target.startswith("#"):
                continue
            destination = ((ROOT / name).parent / target.split("#")[0]).resolve()
            assert destination.is_relative_to(ROOT) and destination.is_file(), (name, target)


def test_requirements_are_consolidated_in_one_file():
    assert sorted(path.name for path in ROOT.glob("requirements*.txt")) == ["requirements.txt"]
    assert not (ROOT / "requirements").exists()
    lines = (ROOT / "requirements.txt").read_text().splitlines()
    assert len(lines) == len(set(lines))
    assert not any(line.startswith("-r ") for line in lines)


def test_tests_are_grouped_without_losing_known_coverage():
    assert not list((ROOT / "tests").glob("test_*.py"))
    for folder in ("hedge_design", "workflow"):
        assert (ROOT / "tests" / folder / "__init__.py").is_file()
    assert len(list((ROOT / "tests/hedge_design").glob("test_*.py"))) == 7
    assert not (ROOT / "tests/supporting").exists()
    assert (ROOT / "legacy/unified/tests/test_theta_chain.py").is_file()
    assert (ROOT / "legacy/unified/tests/test_iv_realized_spread.py").is_file()


def test_retired_workflow_is_contained_in_legacy():
    for name in ("julia", "arxiv_submission", "src/config.py", "src/analysis",
                 "src/features", "src/pipelines", "docs/draft.md", "docs/legacy",
                 "docs/archive", "docs/hedge_capacity", "notebooks/05_options_analysis.ipynb"):
        assert not (ROOT / name).exists(), name
    assert not list((ROOT / "scripts").glob("0*.py"))
    assert {path.name for path in (ROOT / "notebooks").glob("*.ipynb")} == {"06_hedge_frontiers.ipynb"}
    for name in ("src/config.py", "docs/draft.md", "notebooks/05_options_analysis.ipynb",
                 "julia/Project.toml", "scripts/08_paper_artifacts.py"):
        assert (ROOT / "legacy/unified" / name).is_file()
