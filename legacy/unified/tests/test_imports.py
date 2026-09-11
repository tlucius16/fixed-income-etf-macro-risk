from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def test_core_modules_import():
    from legacy.unified.src.data import macro, prices, risk_free, universe
    from legacy.unified.src.features import structural

    assert macro is not None
    assert prices is not None
    assert risk_free is not None
    assert universe is not None
    assert structural is not None


def test_legacy_paths_separate_retired_outputs_from_shared_audit_inputs():
    from legacy.unified.src import config
    from legacy.unified.src.data import options
    import inspect

    assert config.PROJECT_ROOT == ROOT
    assert config.DATA_DIR == ROOT / "legacy/unified/data"
    assert config.PAPER_DIR == ROOT / "legacy/unified/docs/hedge_capacity"
    assert config.PROCESSED_LIVE_DIR == ROOT / "legacy/unified/data/processed/live"
    assert config.CORE_PANEL_CSV == ROOT / "data/processed/offline/core_panel.csv"
    assert config.RAW_PRICES_CSV == ROOT / "data/raw/prices.csv"
    assert config.CHAINS_CSV == ROOT / "data/processed/options_screen/chains.csv"
    assert options._IV_CACHE_DIR == options._SCREEN_CACHE_DIR == config.OPTIONS_SCREEN_RAW_DIR
    assert inspect.signature(options.concat_results).parameters["out_dir"].default == config.OPTIONS_SCREEN_DIR


def test_archived_iv_script_uses_shared_panel_paths():
    from legacy.unified.src import config
    import importlib.util

    path = ROOT / "legacy/unified/scripts/04_build_iv_panel.py"
    spec = importlib.util.spec_from_file_location("legacy_iv_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module._TICKER_SUMMARY == config.TICKER_SUMMARY_CSV
    assert module._OUT_PATH == config.IV_PANEL_CSV
