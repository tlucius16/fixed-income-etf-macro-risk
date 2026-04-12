from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_core_modules_import():
    from src.data import macro, prices, risk_free, universe
    from src.features import structural

    assert macro is not None
    assert prices is not None
    assert risk_free is not None
    assert universe is not None
    assert structural is not None
